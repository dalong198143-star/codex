"""Bing 搜索采集器 — HTML 解析

从 Bing 搜索结果中提取标题、摘要、URL。
使用 ProxyHandler({}) 绕过系统代理。
"""

import re
import urllib.request
import urllib.parse
import html as html_module
import ssl
import time

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SOURCE_BLACKLIST = [
    "dictionary.com", "vocabulary.com", "merriam-webster.com",
    "wikipedia.org", "youtube.com", "facebook.com", "reddit.com",
]


def _fetch(url: str, timeout: int = 8) -> str | None:
    """获取 URL 内容 — 绕过系统代理，带重试"""
    handler = urllib.request.ProxyHandler({})
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(handler)
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            return opener.open(req, timeout=timeout, context=ctx).read().decode("utf-8", errors="replace")
        except Exception:
            if attempt == 0:
                time.sleep(1)
                continue
            return None
    return None


def bing_search(query: str) -> list[dict]:
    """Bing 搜索

    Args:
        query: 搜索关键词

    Returns:
        list[dict]: 每条包含 t(标题), u(URL), s(摘要), src("bing")
    """
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query) + "&count=6"
    data = _fetch(url)
    if not data:
        return []

    results = []
    for block in re.split(r'<li class="b_algo"', data)[1:9]:
        try:
            tm = re.search(r'<h2><a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block)
            sm = re.search(r'<p[^>]*>(.*?)</p>', block)
            if not tm or not sm:
                continue
            url = tm.group(1)
            if any(d in url for d in SOURCE_BLACKLIST):
                continue
            title = html_module.unescape(tm.group(2))[:150]
            snippet = html_module.unescape(sm.group(1))[:500]
            results.append({"t": title, "u": url, "s": snippet, "src": "bing"})
        except Exception:
            continue

    return results
