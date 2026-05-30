"""知识库同步 — 向 ChromaDB 写入情报条目

同步策略:
  - 时机: 每次扫描完成后
  - 级别: 仅 CRITICAL + IMPORTANT（WATCH 不写）
  - 内容: 含 LLM 分析结果（如果有）
  - 去重: KB 服务端 ChromaDB 余弦距离阈值 0.25 负责去重

调用方式:
  from storage.kb_sync import sync_to_kb
  sync_to_kb(items)  # items 为 scan() 输出列表
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# KB 服务地址
KB_SERVER_URL = "http://127.0.0.1:8765"  # shared with ????? ? same machine, intentional
# topic ??????? tags ??? 4 ??? topic
# enterprise_competition / policy_regulation / tech_breakthrough / market_trend
_TOPIC_MAP = {
    frozenset({"ai", "infra"}): "enterprise_competition",
    frozenset({"ai"}): "enterprise_competition",
    frozenset({"dc", "investment"}): "market_trend",
    frozenset({"dc", "north-america"}): "market_trend",
    frozenset({"middle-east", "infra"}): "market_trend",
    frozenset({"africa", "emerging"}): "market_trend",
    frozenset({"ixp", "europe"}): "policy_regulation",
    frozenset({"ixp", "asia"}): "policy_regulation",
    frozenset({"policy", "geo"}): "policy_regulation",
    frozenset({"cable", "infra"}): "tech_breakthrough",
    frozenset({"satellite", "infra"}): "tech_breakthrough",
}

_DEFAULT_TOPIC = "market_trend"  # fallback

def _get_topic(tags: list) -> str:
    """???? tags ???? topic"""
    if not tags:
        return _DEFAULT_TOPIC
    key = frozenset(tags)
    return _TOPIC_MAP.get(key, _DEFAULT_TOPIC)

# ChromaDB 脚本目录（用于自动启动 kb_server）
HERMES_SCRIPTS = Path("D:/hermes-tools/scripts")


def _server_ready() -> bool:
    """检查 KB 服务是否运行"""
    try:
        r = requests.get(f"{KB_SERVER_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _ensure_server():
    """确保 KB 服务在运行（自动启动）"""
    if _server_ready():
        return
    logger.info("KB server not running, starting...")
    import subprocess
    try:
        subprocess.Popen(
            [sys.executable, str(HERMES_SCRIPTS / "kb_server.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        for _ in range(30):
            time.sleep(0.2)
            if _server_ready():
                logger.info("KB server ready")
                return
        logger.warning("KB server failed to start within 6s")
    except Exception as e:
        logger.warning(f"KB auto-start failed: {e}")


def _kb_add(content: str, topic: str, section: str) -> Optional[dict]:
    """向 KB 添加一条记录"""
    try:
        r = requests.post(
            f"{KB_SERVER_URL}/add",
            json={"content": content, "topic": topic, "section": section},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"KB add failed: {e}")
        return None


def sync_to_kb(items: list[dict]):
    """向知识库同步情报条目

    Args:
        items: scan() 输出的条目列表
    """
    _ensure_server()

    # 只同步 CRITICAL + IMPORTANT
    to_sync = [it for it in items if it.get("level") in ("CRITICAL", "IMPORTANT")]
    if not to_sync:
        logger.info("KB sync: no CRITICAL/IMPORTANT items to sync")
        return

    success = 0
    failed = 0

    for it in to_sync:
        try:
            node = it.get("n", "?")
            title = it.get("t", "")[:120]
            snippet = it.get("s", "")[:400]
            url = it.get("u", "")
            level = it.get("level", "WATCH")
            kw = ", ".join(it.get("kw", []) or [])

            # LLM 分析结果（如果有）
            llm_summary = it.get("llm_summary", "")
            llm_importance = it.get("llm_importance", 0)

            # 构建同步内容
            parts = [f"[{level}] [{node}] {title}"]
            if llm_summary:
                parts.append(f"💡 {llm_summary}")
            parts.append(snippet)
            parts.append(f"来源: {url}")
            parts.append(f"关键词: {kw}")
            if llm_importance:
                parts.append(f"LLM重要性: {llm_importance}/5")
            content = "\n".join(parts)

            tags = it.get("tags", [])
            topic = _get_topic(tags)
            section = f"{node} - {title[:60]}"

            result = _kb_add(content, topic, section)
            if result:
                success += 1
            else:
                failed += 1

        except Exception as e:
            failed += 1
            logger.warning(f"KB sync item failed: {e}")

    logger.info(f"KB sync: {success} synced, {failed} failed")
    if success > 0:
        print(f"  [KB] 同步完成: {success} 条 (失败 {failed})")


def sync_is_available() -> bool:
    """检查 KB 服务是否可用"""
    return _server_ready()

