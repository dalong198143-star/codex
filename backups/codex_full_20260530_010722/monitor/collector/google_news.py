"""Google News RSS 采集器

从 Google News RSS feed 获取新闻。
注意: 在国内网络可能无法访问，此时由 RSS feed 兜底。
"""

import re
import urllib.request
import urllib.parse
import html as html_module
import ssl
import time

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _fetch(url: str, timeout: int = 8) -> str | None:
    """获取 URL 内容"""
    handler = urllib.request.ProxyHandler({})
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(handler)
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
            )
            return opener.open(req, timeout=timeout, context=ctx).read().decode("utf-8", errors="replace")
        except Exception:
            if attempt == 0:
                time.sleep(1)
                continue
            return None
    return None


def google_news_search(query: str) -> list[dict]:
    """Google News RSS 搜索

    Args:
        query: 搜索关键词

    Returns:
        list[dict]: 每条包含 t(标题), u(URL), s(摘要), src("google-news")
    """
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    data = _fetch(url)
    if not data:
        return []

    results = []
    for item in re.findall(r"<item>.*?</item>", data, re.DOTALL):
        try:
            title = re.search(r"<title>(.*?)</title>", item)
            link = re.search(r"<link>(.*?)</link>", item)
            desc = re.search(r"<description>(.*?)</description>", item)
            if not title or not link:
                continue
            results.append({
                "t": html_module.unescape(title.group(1))[:150],
                "u": link.group(1),
                "s": html_module.unescape(desc.group(1)[:500] if desc else title.group(1)),
                "src": "google-news",
            })
        except Exception:
            continue

    return results[:6]
