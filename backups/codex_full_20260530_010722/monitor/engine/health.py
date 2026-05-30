"""系统健康监控 — 静默故障检测 + 系统心跳

功能:
  1. 每轮扫描后记录各节点健康状态
  2. 节点连续 N 次 0 结果 → 静默故障告警
  3. 每 4 小时生成系统心跳报告
  4. 数据源可用性追踪
"""

import datetime
import time
from pathlib import Path
from typing import Optional

from monitor.config import get_enabled_nodes
from monitor.storage.db import log_health, get_recent_health


# 节点静默检测阈值
SILENT_THRESHOLD = 3  # 连续 3 次 0 结果视为静默故障


class HealthTracker:
    """健康追踪器 — 记录每轮扫描的系统状态"""

    def __init__(self):
        self._node_silent_count: dict[str, int] = {}
        self._source_health: dict[str, dict] = {}
        self._last_heartbeat: Optional[datetime.datetime] = None
        self._scan_count = 0
        # 初始化节点沉默计数器
        for n in get_enabled_nodes():
            self._node_silent_count[n["name"]] = 0

    def record_node_result(self, node_name: str, total_items: int, error: Optional[str] = None):
        """记录一个节点的本轮扫描结果

        Args:
            node_name: 节点名称
            total_items: 本轮获取到的条目数
            error: 如果有错误，传入错误信息
        """
        if error:
            # 出错了也算一次"无声"扫描
            self._node_silent_count[node_name] = self._node_silent_count.get(node_name, 0) + 1
            log_health("node", "ERROR", f"{node_name}: {error[:200]}")
            return

        if total_items == 0:
            self._node_silent_count[node_name] = self._node_silent_count.get(node_name, 0) + 1
        else:
            self._node_silent_count[node_name] = 0  # 有结果，重置计数器

    def get_silent_nodes(self) -> list[str]:
        """返回当前被判定为静默故障的节点列表"""
        silent = []
        for name, count in self._node_silent_count.items():
            if count >= SILENT_THRESHOLD:
                silent.append(f"{name} (连续 {count} 次 0 结果)")
        return silent

    def record_source_health(self, source: str, ok: bool, detail: str = ""):
        """记录数据源可用性

        Args:
            source: 数据源名称 (bing/google-news/rss-xxx)
            ok: 是否正常
            detail: 详细描述
        """
        now = time.time()
        if source not in self._source_health:
            self._source_health[source] = {
                "last_ok": 0,
                "last_fail": 0,
                "fail_count": 0,
                "consecutive_fails": 0,
            }
        h = self._source_health[source]
        if ok:
            h["last_ok"] = now
            h["consecutive_fails"] = 0
            h["fail_count"] = 0
        else:
            h["last_fail"] = now
            h["consecutive_fails"] += 1
            h["fail_count"] += 1
        log_health(f"source:{source}", "OK" if ok else "DOWN", detail[:200])

    def get_dead_sources(self) -> list[str]:
        """返回连续失败超过 3 次的数据源"""
        dead = []
        for src, h in self._source_health.items():
            if h["consecutive_fails"] >= 3:
                dead.append(f"{src} (连续 {h['consecutive_fails']} 次失败)")
        return dead

    def should_send_heartbeat(self, interval_hours: int = 4) -> bool:
        """检查是否到了发送系统心跳的时间"""
        now = datetime.datetime.now()
        if self._last_heartbeat is None:
            self._last_heartbeat = now
            return True  # 首次运行发送
        if (now - self._last_heartbeat).total_seconds() >= interval_hours * 3600:
            self._last_heartbeat = now
            return True
        return False

    def build_heartbeat_report(self) -> str:
        """构建系统心跳报告（纯文本）"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"📡 系统心跳报告 — {now}",
            f"{'=' * 40}",
        ]

        # 扫描统计
        lines.append(f"\n扫描次数: {self._scan_count}")

        # 静默节点
        silent = self.get_silent_nodes()
        if silent:
            lines.append(f"\n🔴 静默故障节点 ({len(silent)}):")
            for s in silent:
                lines.append(f"  • {s}")
        else:
            lines.append(f"\n✅ 所有节点均有数据返回")

        # 故障数据源
        dead = self.get_dead_sources()
        if dead:
            lines.append(f"\n🔴 不可用数据源 ({len(dead)}):")
            for d in dead:
                lines.append(f"  • {d}")
        else:
            lines.append(f"\n✅ 所有数据源可达")

        # 最近健康记录
        recent = get_recent_health(hours=1)
        errors = [r for r in recent if r["status"] != "OK"]
        if errors:
            lines.append(f"\n⚠️ 最近 1 小时异常 ({len(errors)}):")
            for r in errors[:5]:
                lines.append(f"  [{r['ts'][:16]}] {r['source']}: {r['detail'][:80]}")
        else:
            lines.append(f"\n✅ 最近 1 小时无异常")

        lines.append(f"\n{'=' * 40}")
        return "\n".join(lines)

    def increment_scan(self):
        """增加扫描计数"""
        self._scan_count += 1

    def get_summary(self) -> dict:
        """获取当前健康摘要"""
        return {
            "scan_count": self._scan_count,
            "silent_nodes": self.get_silent_nodes(),
            "dead_sources": self.get_dead_sources(),
        }
