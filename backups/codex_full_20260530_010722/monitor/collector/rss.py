"""RSS Feed 采集器（兜底数据源）

feedparser 解析 RSS/Atom feed，作为 Bing 和 Google News 的兜底。
Bing/Google 都挂时，至少还有这个能拿到数据。
"""

import time
from typing import Optional

import feedparser
import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _fetch_feed(url: str, timeout: int = 10) -> Optional[str]:
    """获取 RSS feed 内容"""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"},
            timeout=timeout,
            proxies={"http": "", "https": ""},  # 绕过系统代理
        )
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def parse_feed(url: str) -> list[dict]:
    """解析单个 RSS feed

    Args:
        url: Feed URL

    Returns:
        list[dict]: 条目列表
    """
    raw = _fetch_feed(url)
    if not raw:
        return []

    parsed = feedparser.parse(raw)
    results = []
    for entry in parsed.entries[:10]:  # 每个 feed 最多取 10 条
        title = (entry.get("title") or "")[:150]
        link = entry.get("link") or ""
        summary = (entry.get("summary") or entry.get("description") or "")[:500]
        if title and link:
            results.append({
                "t": title,
                "u": link,
                "s": summary,
                "src": f"rss:{parsed.feed.get('title', url)[:20]}",
            })
    return results


def search_feeds(feeds: list[dict]) -> list[dict]:
    """批量搜索多个 RSS feed

    Args:
        feeds: feed 配置列表，每项含 name/url/tags

    Returns:
        list[dict]: 合并去重后的条目
    """
    all_items = []
    seen_urls = set()

    for feed_cfg in feeds:
        if not feed_cfg.get("enabled", True):
            continue
        url = feed_cfg.get("url", "")
        if not url:
            continue
        try:
            items = parse_feed(url)
            for it in items:
                if it["u"] not in seen_urls:
                    seen_urls.add(it["u"])
                    all_items.append(it)
        except Exception:
            continue
        time.sleep(0.3)  # 避免频繁请求被 ban

    return all_items
