"""配置加载 — 从 YAML 文件热加载节点和 Feed 配置

每轮扫描前调用 load_nodes() / load_feeds() 重读 YAML，
确保配置修改后立即生效，无需重启进程。
"""

import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).parent

# 缓存，避免每轮反复解析 YAML（但每轮扫描前会清缓存重新加载）
_node_cache: list[dict] | None = None
_feed_cache: list[dict] | None = None


def _load_yaml(filename: str) -> dict:
    """加载 YAML 文件，返回解析后的字典"""
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_nodes(force_reload: bool = False) -> list[dict]:
    """加载节点配置，每轮扫描前调用

    Args:
        force_reload: 强制重新读取文件（默认使用缓存）

    Returns:
        list[dict]: 节点配置列表，每个节点包含 name/keywords/tags/mail_level/enabled
    """
    global _node_cache
    if _node_cache is None or force_reload:
        data = _load_yaml("nodes.yaml")
        _node_cache = data.get("nodes", [])
    return _node_cache


def load_feeds(force_reload: bool = False) -> list[dict]:
    """加载 RSS Feed 配置

    Args:
        force_reload: 强制重新读取文件

    Returns:
        list[dict]: Feed 配置列表
    """
    global _feed_cache
    if _feed_cache is None or force_reload:
        data = _load_yaml("feeds.yaml")
        _feed_cache = data.get("feeds", [])
    return _feed_cache


def get_enabled_nodes(force_reload: bool = False) -> list[dict]:
    """获取所有启用的节点"""
    return [n for n in load_nodes(force_reload=force_reload) if n.get("enabled", True)]


def get_enabled_feeds(force_reload: bool = False) -> list[dict]:
    """获取所有启用的 Feed"""
    return [f for f in load_feeds(force_reload=force_reload) if f.get("enabled", True)]


def get_data_dir() -> Path:
    """获取持久化数据目录
    优先级: MONITOR_DATA_DIR 环境变量 > %%TEMP%%/codex_monitor_v2
    """
    env_dir = os.environ.get("MONITOR_DATA_DIR")
    if env_dir:
        base = Path(env_dir)
    else:
        d_path = Path("D:\\maozhua\\Codex\\data\\monitor")
        try:
            d_path.mkdir(parents=True, exist_ok=True)
            test_file = d_path / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            base = d_path
        except (PermissionError, OSError):
            base = Path(os.environ.get("TEMP", "C:\\Temp")) / "codex_monitor_v2"
    base.mkdir(parents=True, exist_ok=True)
    return base


# === 配置验证（用于 test-config 命令） ===

def validate_config() -> list[str]:
    """验证配置文件的正确性，返回错误列表"""
    errors = []

    nodes = load_nodes(force_reload=True)
    if not nodes:
        errors.append("nodes.yaml: 未定义任何节点")
    for i, n in enumerate(nodes):
        if not n.get("name"):
            errors.append(f"nodes.yaml 第 {i+1} 项: 缺少 name")
        if not n.get("keywords"):
            errors.append(f"nodes.yaml [{n.get('name','?')}]: 缺少 keywords")
        level = n.get("mail_level", "")
        if level not in ("CRITICAL", "IMPORTANT", "WATCH", "NONE"):
            errors.append(f"nodes.yaml [{n.get('name','?')}]: mail_level 无效 ({level})")

    feeds = load_feeds(force_reload=True)
    for i, f in enumerate(feeds):
        if not f.get("name"):
            errors.append(f"feeds.yaml 第 {i+1} 项: 缺少 name")
        if not f.get("url"):
            errors.append(f"feeds.yaml [{f.get('name','?')}]: 缺少 url")

    return errors
