"""LLM 批量分析 — 情报推演层（v2.1 核心能力）

功能:
  1. 中文摘要（20-50 字）
  2. 重要性评分（1-5）
  3. 关联事件标记（跨条目引用）
  4. 置信度评分（1-5）

设计原则:
  - 单次调用处理全部新条目（批量）
  - temperature=0.1 + json.loads 解析（不依赖国产模型 JSON mode）
  - 超时 30s 后降级到纯规则 classifier
  - 互斥锁防止积压雪崩

调用方式:
  from engine.llm_analyzer import batch_analyze
  enriched = batch_analyze(items)
  # items 中的每条会被添加上 llm_summary, llm_importance, llm_confidence, llm_related
"""

import json
import os
import time
import logging
from typing import Optional
import threading

logger = logging.getLogger(__name__)

# 互斥锁，防止多轮扫描同时调用 LLM
_llm_lock = threading.Lock()
_llm_busy = False

# LLM API 配置
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3-coder")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "60"))  # 单次调用超时
LLM_MAX_ITEMS = int(os.environ.get("LLM_MAX_ITEMS", "30"))  # 每次最多分析条数


def is_busy() -> bool:
    """检查 LLM 是否正在处理中（用于外部跳过判断）"""
    return _llm_busy


def _build_prompt(items: list[dict]) -> str:
    """构建 LLM 分析提示词"""
    entries = []
    for i, item in enumerate(items):
        t = item.get("t", "")[:120]
        s = item.get("s", "")[:150]
        n = item.get("n", "?")
        lv = item.get("level", "WATCH")
        kw = ", ".join(item.get("kw", []) or [])
        entries.append(f"[{i}] 节点={n} 级别={lv} 关键词={kw}\n    标题: {t}\n    摘要: {s}")

    entries_text = "\n\n".join(entries)

    prompt = f"""你是一个全球网络基础设施情报分析师。以下是本次扫描收集到的新条目。

请对每条执行分析，以 JSON 数组格式返回（一一对应）：

{{
  "analyses": [
    {{
      "index": 0,
      "summary_zh": "中文摘要，20-50字",
      "importance": 4,
      "confidence": 4,
      "related_indices": [],
      "reason": "简要说明为什么重要/不重要"
    }}
  ]
}}

评分标准：
- importance: 1(噪音)~5(重大事件)。1=话题无关，2=轻微相关，3=普通，4=重要，5=极其重要
- confidence: 1(不确定)~5(非常可靠)。基于来源可信度和内容质量
- related_indices: 与本条相关的其他条目 index 列表（语义关联，如同一事件的多个报道）

条目列表：
{entries_text}
"""
    return prompt


def _parse_response(text: str) -> list[dict]:
    """解析 LLM 返回的 JSON，含降级兜底

    Args:
        text: LLM 返回的原始文本

    Returns:
        list[dict]: 分析结果列表
    """
    # 尝试提取 JSON 数组
    text = text.strip()

    # 尝试直接解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "analyses" in data:
            return data["analyses"]
    except json.JSONDecodeError:
        pass

    # 尝试用正则提取 JSON 块
    import re
    json_match = re.search(r"\[[\s\S]*\]", text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # 再试 {analyses: [...]} 格式
    json_match = re.search(r'\{\s*"analyses"\s*:\s*\[[\s\S]*\]\s*\}', text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, dict) and "analyses" in data:
                return data["analyses"]
        except json.JSONDecodeError:
            pass

    return []


def _call_llm(prompt: str) -> Optional[str]:
    """调用 LLM API（走本地代理链）"""
    import urllib.request
    import urllib.error

    data = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4096,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-dummy",  # local proxy (127.0.0.1:1234), no real key needed
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=LLM_TIMEOUT)
        body = resp.read().decode("utf-8")
        result = json.loads(body)
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            OSError, TimeoutError) as e:
        logger.warning(f"LLM call failed: {e}")
        return None


def batch_analyze(items: list[dict]) -> list[dict]:
    """批量分析条目（主入口）

    Args:
        items: 条目列表，每条含 t(标题)/s(摘要)/n(节点)/level/URL等

    Returns:
        list[dict]: 增强后的条目列表（含 llm_* 字段）
    """
    global _llm_busy

    # 互斥锁
    if not _llm_lock.acquire(blocking=False):
        logger.warning("LLM 正在处理上一轮，跳过本轮分析")
        return items  # 返回原始条目，不阻塞

    try:
        _llm_busy = True

        if not items:
            return items

        # 截断：最多分析 LLM_MAX_ITEMS 条
        batch = items[:LLM_MAX_ITEMS]
        if len(items) > LLM_MAX_ITEMS:
            logger.info(f"条目过多 ({len(items)}), 只分析前 {LLM_MAX_ITEMS} 条")

        # 构建提示词
        prompt = _build_prompt(batch)
        logger.info(f"LLM 分析: {len(batch)} 条, 模型={LLM_MODEL}")

        # 调用 LLM
        start = time.time()
        response = _call_llm(prompt)
        elapsed = time.time() - start

        if not response:
            logger.warning(f"LLM 无响应 ({elapsed:.1f}s), 返回原始条目")
            return items

        # 解析结果
        analyses = _parse_response(response)
        if not analyses:
            logger.warning(f"LLM 返回格式无法解析, 原始响应前200字: {response[:200]}")
            return items

        logger.info(f"LLM 分析完成: {len(analyses)} 条结果, 耗时 {elapsed:.1f}s")

        # 将分析结果合并到条目
        analysis_map = {a.get("index"): a for a in analyses if "index" in a}
        for i, item in enumerate(batch):
            if i in analysis_map:
                a = analysis_map[i]
                item["llm_summary"] = a.get("summary_zh", "")
                item["llm_importance"] = a.get("importance", 3)
                item["llm_confidence"] = a.get("confidence", 3)
                item["llm_related"] = a.get("related_indices", [])
                item["llm_reason"] = a.get("reason", "")

        return items

    finally:
        _llm_busy = False
        _llm_lock.release()
