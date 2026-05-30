"""持久化存储 — SQLite 数据库管理

所有数据持久化到 D:\\maozhua\\Codex\\data\\monitor\\monitor.db
WAL 模式支持并发读写，自动清理旧数据。

表结构:
  seen       — 已见条目去重 (id=sha256[:16], ts)
  log        — 每轮扫描日志 (ts, node, n, new)
  hotwords   — 热词追踪 (word, count, last_seen, peak)
  mail_queue — 待发送邮件队列（SMTP 失败时缓存）
  health     — 系统健康记录 (ts, source, status, detail)
"""

import sqlite3
import datetime
import hashlib
import os
import time
from pathlib import Path
from typing import Optional

from monitor.config import get_data_dir

DB_FILENAME = "monitor.db"
_RETRY_DELAY = 0.1  # 并发写冲突时重试等待时间
_RETRY_MAX = 5      # 最大重试次数


def _get_db_path() -> Path:
    return get_data_dir() / DB_FILENAME


def _connect() -> sqlite3.Connection:
    """获取数据库连接，启用 WAL 模式"""
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _retry(func):
    """带重试的数据库操作装饰器，处理 SQLITE_BUSY"""
    def wrapper(*args, **kwargs):
        for attempt in range(_RETRY_MAX):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < _RETRY_MAX - 1:
                    time.sleep(_RETRY_DELAY * (attempt + 1))
                    continue
                raise
    return wrapper


# === 初始化 ===

def init_db():
    """创建表结构（幂等）"""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seen (
            id TEXT PRIMARY KEY,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS log (
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            node TEXT,
            n INTEGER DEFAULT 0,
            new INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS hotwords (
            word TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_seen TIMESTAMP,
            peak INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS mail_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            html_body TEXT,
            retries INTEGER DEFAULT 0,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS health (
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            status TEXT,
            detail TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_seen_ts ON seen(ts);
        CREATE INDEX IF NOT EXISTS idx_log_ts ON log(ts);
        CREATE INDEX IF NOT EXISTS idx_health_ts ON health(ts);
    """)
    conn.commit()
    conn.close()


# === 去重 ===

def make_hash(text: str) -> str:
    """从文本生成 16 位去重哈希"""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@_retry
def is_seen(hash_id: str) -> bool:
    """检查是否已见过"""
    conn = _connect()
    row = conn.execute("SELECT 1 FROM seen WHERE id=?", (hash_id,)).fetchone()
    conn.close()
    return row is not None


@_retry
def mark_seen(hash_id: str):
    """标记为已见"""
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO seen(id, ts) VALUES (?, ?)",
        (hash_id, datetime.datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


# === 扫描日志 ===

@_retry
def log_scan(node: str, total: int, new: int):
    """记录一轮扫描结果"""
    conn = _connect()
    conn.execute(
        "INSERT INTO log(ts, node, n, new) VALUES (?, ?, ?, ?)",
        (datetime.datetime.utcnow().isoformat(), node, total, new)
    )
    conn.commit()
    conn.close()


# === 热词追踪 ===

@_retry
def track_hotwords(keywords: list[str]) -> list[str]:
    """记录热词出现，返回本轮新发热词"""
    conn = _connect()
    now = datetime.datetime.utcnow().isoformat()
    heated = []
    for kw in keywords:
        if not isinstance(kw, str):
            continue
        row = conn.execute(
            "SELECT count, peak FROM hotwords WHERE word=?",
            (kw,)
        ).fetchone()
        if row:
            new_count = row[0] + 1
            new_peak = max(row[1], new_count)
            conn.execute(
                "UPDATE hotwords SET count=?, peak=?, last_seen=? WHERE word=?",
                (new_count, new_peak, now, kw)
            )
            # 连续出现 3 次视为升温
            if new_count >= 3 and row[0] < 3:
                heated.append(kw)
        else:
            conn.execute(
                "INSERT INTO hotwords(word, count, last_seen, peak) VALUES (?, 1, ?, 1)",
                (kw, now)
            )
    conn.commit()
    conn.close()
    return heated


# === 邮件队列 ===

@_retry
def enqueue_mail(subject: str, html_body: str):
    """SMTP 失败时缓存到队列"""
    conn = _connect()
    conn.execute(
        "INSERT INTO mail_queue(subject, html_body) VALUES (?, ?)",
        (subject, html_body)
    )
    conn.commit()
    conn.close()


@_retry
def get_pending_mails() -> list[dict]:
    """获取待发送邮件列表"""
    conn = _connect()
    rows = conn.execute(
        "SELECT id, subject, html_body, retries FROM mail_queue WHERE retries < 3 "
        "ORDER BY created ASC"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "subject": r[1], "html_body": r[2], "retries": r[3]}
        for r in rows
    ]


@_retry
def mark_mail_sent(mail_id: int):
    """标记邮件已发送（删除队列）"""
    conn = _connect()
    conn.execute("DELETE FROM mail_queue WHERE id=?", (mail_id,))
    conn.commit()
    conn.close()


@_retry
def mark_mail_failed(mail_id: int, error: str):
    """标记邮件发送失败，增加重试计数"""
    conn = _connect()
    conn.execute(
        "UPDATE mail_queue SET retries=retries+1, last_error=? WHERE id=?",
        (error[:200], mail_id)
    )
    conn.commit()
    conn.close()


# === 健康记录 ===

@_retry
def log_health(source: str, status: str, detail: str = ""):
    """记录系统健康状态"""
    conn = _connect()
    conn.execute(
        "INSERT INTO health(ts, source, status, detail) VALUES (?, ?, ?, ?)",
        (datetime.datetime.utcnow().isoformat(), source, status, detail[:500])
    )
    conn.commit()
    conn.close()


def get_recent_health(hours: int = 24) -> list[dict]:
    """获取最近健康记录"""
    conn = _connect()
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT ts, source, status, detail FROM health WHERE ts > ? ORDER BY ts DESC",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [{"ts": r[0], "source": r[1], "status": r[2], "detail": r[3]} for r in rows]


# === 数据生命周期 ===

@_retry
def clean_old_data():
    """清理过期数据（每周调用一次）"""
    conn = _connect()
    now = datetime.datetime.utcnow()
    # seen 保留 30 天
    cutoff_seen = (now - datetime.timedelta(days=30)).isoformat()
    conn.execute("DELETE FROM seen WHERE ts < ?", (cutoff_seen,))
    # log 保留 90 天
    cutoff_log = (now - datetime.timedelta(days=90)).isoformat()
    conn.execute("DELETE FROM log WHERE ts < ?", (cutoff_log,))
    # health 保留 30 天
    cutoff_health = (now - datetime.timedelta(days=30)).isoformat()
    conn.execute("DELETE FROM health WHERE ts < ?", (cutoff_health,))
    conn.commit()
    conn.close()
    # VACUUM 回收空间（单独连接，不在事务内）
    vconn = _connect()
    vconn.execute("VACUUM")
    vconn.close()


def get_stats_24h() -> dict:
    """获取 24 小时统计"""
    conn = _connect()
    day_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat()
    total_fetched = conn.execute(
        "SELECT COALESCE(SUM(n), 0) FROM log WHERE ts > ?", (day_ago,)
    ).fetchone()[0]
    total_accepted = conn.execute(
        "SELECT COUNT(*) FROM seen WHERE ts > ?", (day_ago,)
    ).fetchone()[0]
    conn.close()
    return {
        "fetched": total_fetched,
        "accepted": total_accepted,
        "filtered": max(0, total_fetched - total_accepted),
    }


# === 备份 ===

def backup_db(output_dir: str | None = None) -> str:
    """备份 SQLite 数据库到指定目录

    生成 .sql 文本格式备份（可读可恢复）。
    每周自动调用一次（由 cmd_clean 触发）。

    Args:
        output_dir: 备份输出目录，默认使用数据目录下的 backups 子目录

    Returns:
        备份文件路径
    """
    import shutil
    from datetime import datetime
    from monitor.config import get_data_dir

    if output_dir is None:
        output_dir = str(get_data_dir() / "backups")
    os.makedirs(output_dir, exist_ok=True)

    db_path = _get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f"monitor_backup_{timestamp}.sql")

    conn = _connect()
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(line + "\n")
        print(f"  [Backup] 已备份到: {backup_file}")
    finally:
        conn.close()

    # 保留最近 7 个备份，删除更早的
    backups = sorted(
        [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("monitor_backup_")],
        key=os.path.getmtime
    )
    while len(backups) > 7:
        old = backups.pop(0)
        os.remove(old)
        print(f"  [Backup] 清理旧备份: {os.path.basename(old)}")

    return backup_file

import os, shutil, sqlite3, datetime as dt
from monitor.config import get_data_dir

def _backup_chromadb():
    """ChromaDB 原子备份: sqlite3.backup + 向量子目录复制
    备份位置: get_data_dir()/backups/chroma_backup_YYYYMMDD_HHMMSS/
    保留最近 7 份。
    """
    src_dir = r'D:/hermes-tools/kb-vector'
    backup_root = str(get_data_dir() / "backups")
    os.makedirs(backup_root, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(backup_root, f"chroma_backup_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)
    src_db = os.path.join(src_dir, "chroma.sqlite3")
    dst_db = os.path.join(backup_dir, "chroma.sqlite3")
    conn = sqlite3.connect(src_db)
    try:
        bkp = sqlite3.connect(dst_db)
        try:
            conn.backup(bkp)
            print(f"  [ChromaBackup] SQLite 原子备份完成")
        finally:
            bkp.close()
    finally:
        conn.close()
    for item in os.listdir(src_dir):
        src_item = os.path.join(src_dir, item)
        dst_item = os.path.join(backup_dir, item)
        if os.path.isdir(src_item) and item != "reports":
            if not os.path.exists(dst_item):
                shutil.copytree(src_item, dst_item)
    print(f"  [ChromaBackup] 已备份到: {backup_dir}")
    backups = sorted(
        [os.path.join(backup_root, d) for d in os.listdir(backup_root)
         if d.startswith("chroma_backup_") and os.path.isdir(os.path.join(backup_root, d))],
        key=os.path.getmtime
    )
    while len(backups) > 7:
        old = backups.pop(0)
        shutil.rmtree(old, ignore_errors=True)
        print(f"  [ChromaBackup] 清理旧备份: {os.path.basename(old)}")
    return backup_dir
