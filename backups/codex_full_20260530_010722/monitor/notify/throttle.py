"""通知频率控制 — 冷却期 + 合并 + 免打扰

规则:
  CRITICAL: 强制发送，跳过免打扰
  IMPORTANT: 遵守免打扰，每个节点每 2 小时最多 1 封
  WATCH: 8 小时汇总 1 次
  免打扰时段: 23:00-07:00（仅 IMPORTANT/WATCH 遵守）

安全设计:
  - 冷却状态写入 SQLite（可靠、跨轮持久化、不丢失）
  - 无硬编码路径、无 sys.path 污染
  - 所有输入经类型检查
"""

import datetime
import sqlite3
import os
from pathlib import Path
from monitor.utils import now
from typing import Optional

import monitor.storage.db as db


class Throttle:
    """通知节流器 — 用数据库持久化冷却状态"""

    def __init__(self):
        self._db_path = self._get_db_path()

    @staticmethod
    def _get_db_path() -> Path:
        """获取数据库路径（与 db.py 保持一致）"""
        from monitor.config import get_data_dir
        return get_data_dir() / "monitor.db"

    @staticmethod
    def _get_now() -> datetime.datetime:
        return now()

    def _ensure_table(self):
        """确保冷却表存在（幂等）"""
        conn = sqlite3.connect(str(self._db_path), timeout=3)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS throttle_cooldown (
                    node_name TEXT PRIMARY KEY,
                    last_sent_ts TIMESTAMP,
                    level TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_last_sent(self, node_name: str) -> Optional[datetime.datetime]:
        """获取节点的最后发送时间"""
        self._ensure_table()
        conn = sqlite3.connect(str(self._db_path), timeout=3)
        try:
            row = conn.execute(
                "SELECT last_sent_ts FROM throttle_cooldown WHERE node_name=?",
                (node_name,)
            ).fetchone()
            if row and row[0]:
                return datetime.datetime.fromisoformat(row[0])
            return None
        finally:
            conn.close()

    def _set_last_sent(self, node_name: str, level: str, now: datetime.datetime):
        """设置节点的最后发送时间"""
        self._ensure_table()
        conn = sqlite3.connect(str(self._db_path), timeout=3)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO throttle_cooldown(node_name, last_sent_ts, level)
                VALUES (?, ?, ?)
            """, (node_name, now.isoformat(), level))
            conn.commit()
        finally:
            conn.close()

    def _check_quiet_hours(self, now: datetime.datetime) -> bool:
        """检查是否在免打扰时段 (23:00-07:00)"""
        hour = now.hour
        return hour >= 23 or hour < 7

    def should_send(self, node_name: str, level: str) -> tuple[bool, str]:
        """判断是否应该发送通知

        Args:
            node_name: 节点名称
            level: CRITICAL / IMPORTANT / WATCH

        Returns:
            (should_send: bool, reason: str)
        """
        if not isinstance(node_name, str) or not isinstance(level, str):
            return (False, "参数类型错误")

        now = self._get_now()

        # WATCH: 不单独发送，8 小时汇总
        if level == "WATCH":
            return (False, "WATCH 级仅 08/16 点汇总发送")

        # CRITICAL: 强制发送
        if level == "CRITICAL":
            self._set_last_sent(node_name, level, now)
            return (True, "CRITICAL 强制通知")

        # 免打扰检查（仅对 IMPORTANT）
        if self._check_quiet_hours(now):
            return (False, f"免打扰时段 ({now.hour}:00-07:00)")

        # IMPORTANT: 每节点每 2 小时最多 1 封
        if level == "IMPORTANT":
            last_sent = self._get_last_sent(node_name)
            if last_sent is not None:
                elapsed = (now - last_sent).total_seconds()
                if elapsed < 7200:  # 2 小时
                    remaining = int(120 - elapsed / 60)
                    return (False, f"冷却中 (还需 {remaining} 分钟)")
            self._set_last_sent(node_name, level, now)
            return (True, "IMPORTANT 许可")

        return (False, f"未知级别: {level}")

    def should_send_watch_digest(self) -> bool:
        """检查是否到了发送 WATCH 汇总的时间（每 8 小时）"""
        now = self._get_now()
        return now.hour in (8, 16) and now.minute < 5
