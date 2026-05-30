"""情报系统 v2 — 全局信息流动节点监控

版本: 2.0.0 (2026-05-29)
取代: v1 global_monitor.py (已存档)
架构: 采集→过滤→推演(LLM)→存储→通知

使用: python -m monitor scan
配置: config/nodes.yaml, config/feeds.yaml
"""

__version__ = "2.0.0"
__description__ = "Global Information Flow Node Monitor"
