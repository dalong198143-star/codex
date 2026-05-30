"""KB 定时维护脚本 — 供 Windows 任务计划程序调用

功能:
  1. 全量备份知识库（JSONL，直连 ChromaDB）
  2. 清理超过30天的旧备份
  3. 输出健康报告

用法:
  python kb_maintain.py                       # 执行维护
  python kb_maintain.py --dry-run             # 预览

建议: 每天凌晨 3:00 通过 Task Scheduler 执行
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
# 使用 D 盘 Python 包（与 kb_server.py 一致）
_D_PACKAGES = "D:/hermes-tools/python/Python311/site-packages"
if _D_PACKAGES not in sys.path:
    sys.path.insert(0, _D_PACKAGES)

KB_SERVER = "http://127.0.0.1:8765"
BACKUP_DIR = Path("D:/maozhua/Codex/kb-backups")
BACKUP_RETENTION_DAYS = 30
REPORT_FILE = Path("D:/hermes-tools/kb-vector/health_snapshot.json")
KB_PATH = "D:/hermes-tools/kb-vector"
COLLECTION = "general"

DRY_RUN = "--dry-run" in sys.argv


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def ensure_server():
    """确保 KB 服务在运行"""
    try:
        r = requests.get(f"{KB_SERVER}/health", timeout=5)
        if r.status_code == 200:
            return r.json()
    except requests.ConnectionError:
        pass
    log("KB server not running, attempting to start...")
    import subprocess
    subprocess.Popen(
        [sys.executable, str(Path(__file__).parent.parent.parent / "hermes-tools" / "scripts" / "kb_server.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        time.sleep(0.5)
        try:
            r = requests.get(f"{KB_SERVER}/health", timeout=5)
            if r.status_code == 200:
                log("KB server started successfully")
                return r.json()
        except requests.ConnectionError:
            continue
    raise RuntimeError("Failed to start KB server")


def backup():
    """全量导出知识库（直连 ChromaDB）"""
    log("Step 1: Full backup...")
    if DRY_RUN:
        log("  [DRY-RUN] Would export backup")
        return None

    try:
        import chromadb
    except ImportError:
        log("  [ERROR] chromadb not installed")
        return 1

    client = chromadb.PersistentClient(path=KB_PATH)
    col = client.get_collection(COLLECTION)
    data = col.get(include=["documents", "metadatas"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kb_backup_{timestamp}.jsonl"
    filepath = BACKUP_DIR / filename
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    with open(filepath, "w", encoding="utf-8") as f:
        ids = data["ids"]
        docs = data["documents"]
        metas = data["metadatas"]
        for i in range(len(ids)):
            record = {
                "id": ids[i],
                "document": docs[i] if docs else "",
                "metadata": metas[i] if metas else {},
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            total += 1

    size = filepath.stat().st_size
    log(f"  Exported {total} items to {filename} ({size/1024:.1f}KB)")
    return str(filepath)


def clean_old_backups():
    log(f"Step 2: Clean backups older than {BACKUP_RETENTION_DAYS} days...")
    if DRY_RUN:
        log("  [DRY-RUN] Would check and delete old backups")
        return 0

    cutoff = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
    deleted = 0
    for f in sorted(BACKUP_DIR.glob("kb_backup_*.jsonl")):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            f.unlink()
            log(f"  Deleted old backup: {f.name}")
            deleted += 1
    if deleted == 0:
        log("  No old backups to clean")
    return deleted


def snapshot():
    log("Step 3: Take health snapshot...")
    if DRY_RUN:
        log("  [DRY-RUN] Would save health snapshot")
        return

    try:
        r = requests.get(f"{KB_SERVER}/health", timeout=10)
        health = r.json() if r.status_code == 200 else {"status": "error"}
    except Exception as e:
        health = {"status": "error", "error": str(e)}

    try:
        r = requests.get(f"{KB_SERVER}/topics", timeout=10)
        topics_data = r.json() if r.status_code == 200 else {}
    except Exception as e:
        topics_data = {"error": str(e)}

    snapshot_data = {
        "timestamp": datetime.now().isoformat(),
        "health": health,
        "topics": topics_data.get("topics", {}),
        "total_docs": topics_data.get("total", 0),
    }

    if not DRY_RUN:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        log(f"  Snapshot saved")

    print()
    print("=" * 45)
    print("  KB Health Report")
    print("=" * 45)
    print(f"  Status:    {snapshot_data['health'].get('status', 'unknown')}")
    print(f"  Total:     {snapshot_data['total_docs']} docs")
    for topic, count in sorted(snapshot_data.get("topics", {}).items(), key=lambda x: -x[1]):
        print(f"    {topic:<25} {count}")
    print("=" * 45)


def main():
    log("=== KB Maintenance Start ===")
    t0 = time.time()

    try:
        ensure_server()
        backup()
        clean_old_backups()
        snapshot()
    except Exception as e:
        log(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.time() - t0
    log(f"=== KB Maintenance Complete ({elapsed:.1f}s) ===")


if __name__ == "__main__":
    main()

