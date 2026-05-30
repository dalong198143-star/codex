"""分类引擎 — 多标签分类 + 质量评分

核心改进 (vs v1):
  - 多标签: 一条新闻可同时标记 CRITICAL + IMPORTANT + WATCH
  - CRITICAL 过载防护: 'billion' 类投资新闻自动降级到 IMPORTANT
  - 质量评分: 综合 AI 生成检测 / SEO 污染 / 陈旧 / 流量内容
"""

import re

# === 关键模式（命中即标记为该级别） ===
# 不再"第一个命中的级别即止"，而是全部标记

CRITICAL_PATTERNS = re.compile(
    r"(cable cut|submarine cable\s*(?:cut|break|damage|sever)|"
    r"outage|disrupt(?:ion)?|downtime|"
    r"breach|cyber attack|cyberattack|"
    r"export control|ban|sanction|blocked|"
    r"new\s*(?:submarine|cable|landing\s*station)|"
    r"Starlink\s*(?:launch|constellation|expansion)|"
    r"record\s*(?:traffic|bandwidth|capacity))", re.IGNORECASE)

IMPORTANT_PATTERNS = re.compile(
    r"(launch|invest|fund|partner|expand|breakthrough|"
    r"data center\s*(?:campus|investment|announce|project)|"
    r"internet exchange|IXP|"
    r"AI\s*(?:infrastructure|data center|chip|model|startup|unicorn|funding|investment)|"
    r"semiconductor|chip\s*(?:manufacturing|factory|plant|fabrication)|"
    r"GPU|NVIDIA|TSMC|AMD|Intel|"
    r"hyperscale|cloud region|edge\s*node|"
    r"satellite|LEO|constellation|"
    r"regulation|regulatory|"
    r"venture capital|startup\s*(?:funding|investment|series)|"
    r"IPO|stock market|tech stock|fintech|"
    r"open source|LLM|foundation model|"
    r"(?:million|billion)\s*(?:users|deploy|project|investment|funding|deal|valuation))", re.IGNORECASE)

WATCH_PATTERNS = re.compile(
    r"(AI|artificial intelligence|"
    r"funding|acquir|investment|"
    r"digit(al|ization)|transformation|"
    r"emerging market|undersea|submarine|"
    r"UAE|Dubai|Saudi|Africa|Southeast Asia|"
    r"chip|semiconductor|"
    r"fintech|startup|VC|IPO|"
    r"open source|LLM|GPU|cloud computing)", re.IGNORECASE)

# === 过载防护：这些模式如果单独命中 CRITICAL，降级到 IMPORTANT ===
CRITICAL_OVERLOAD_PATTERNS = re.compile(
    # ???????/????????????
    # billion/million ???? investment/funding/deal/raised/series ??
    # "billion-dollar question"?"billion users" ?????
    r"(?:(?:million|billion)\s+(?:investment|funding|deal|raised|series|round|venture|capex)|"
    r"(?:investment|funding|deal|raised)\s+(?:of\s+)?(?:us[ds]?\s*)?(?:million|billion))",
    re.IGNORECASE)

# === 质量检测模式（v1 保留） ===

TRUSTED_SOURCES = [
    "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com",
    "nytimes.com", "bbc.com", "bbc.co.uk", "cnbc.com", "economist.com",
    "techcrunch.com", "theverge.com", "arstechnica.com",
    "wired.com", "venturebeat.com", "crunchbase.com", "spectrum.ieee.org", "thenextweb.com", "nature.com", "science.org",
    "datacenterdynamics.com", "lightreading.com", "fierce-network.com",
    "submarinenetworks.com", "telecompaper.com",
]

AI_GEN_PATTERNS = re.compile(
    r"(here is|here are|below are|as an ai|as a language model|"
    r"I cannot|I don\'t have|I\'m not able to|"
    r"in conclusion|in summary|to summarize|"
    r"it is important to note that|"
    r"this is a great question|"
    r"based on my research|according to my sources|"
    r"certainly!|absolutely!|of course!)", re.IGNORECASE)

SEO_CLUE_PATTERNS = re.compile(
    r"(click here|read more|learn more|sponsored|advertisement|"
    r"best\s*(?:price|deal|offer|discount|coupon)|"
    r"top\s*\d+\s*(?:way|tip|trick|reason|thing)|"
    r"you need to know|you should know|"
    r"this is why|the reason why|"
    r"affiliate|promo code|exclusive deal)", re.IGNORECASE)

STALE_CLUE = re.compile(
    r"(2024|2023|2022|last year|two years ago|"
    r"was announced|was launched|earlier this year|"
    r"according to reports|reportedly|"
    r"is said to be|is believed to be)", re.IGNORECASE)

CLICHE_PATTERNS = re.compile(
    r"(revolutionary|game-changing|groundbreaking|"
    r"unprecedented|next-generation|cutting-edge|"
    r"industry-leading|world-class|best-in-class|"
    r"disruptive|innovative|transformative)", re.IGNORECASE)

FLOOD_PATTERNS = re.compile(
    r"(stock\s*(?:market|price|trading)|"
    r"cryptocurrency|bitcoin|nft|"
    r"metaverse|web3|blockchain|"
    r"sports|entertainment|celebrity|"
    r"weather|forecast|earthquake|"
    r"recipe|diet|fitness|workout)", re.IGNORECASE)

SOURCE_BLACKLIST = [
    "dictionary.com", "vocabulary.com", "merriam-webster.com", "cambridge.org",
    "wikipedia.org", "youtube.com", "instagram.com", "facebook.com",
    "reddit.com", "ebay.com", "amazon.com", "imdb.com",
]

POLLUTION_TOLERANCE = {
    "CRITICAL": 4,
    "IMPORTANT": 3,
    "WATCH": 2,
}


def classify_multi(text: str) -> dict:
    """多标签分类 — 返回命中级别列表及关键词

    Args:
        text: 标题+摘要拼接的文本

    Returns:
        dict: {
            "levels": ["CRITICAL", "IMPORTANT"],  # 所有命中级别（排序，最高级在前）
            "primary": "CRITICAL",                 # 最高级别
            "keywords": ["cable cut", "IXP"],      # 命中的关键词
        }
    """
    t = text.lower()
    levels = []
    keywords = []

    crit_kw = CRITICAL_PATTERNS.findall(t)
    if crit_kw:
        # 检查是否需要过载降级
        overload = CRITICAL_OVERLOAD_PATTERNS.findall(t)
        if overload:
            # 如果命中的全是过载模式，降级到 IMPORTANT
            # 如果同时命中了真正的关键内容（如 cable cut），保持 CRITICAL
            crit_set = set(k.lower() for k in crit_kw)
            overload_set = set(k.lower() for k in overload)
            non_overload = crit_set - overload_set
            if non_overload:
                levels.append("CRITICAL")
                keywords.extend(crit_kw)
            else:
                # 全是被过载模式匹配的，降级到 IMPORTANT
                levels.append("IMPORTANT")
        else:
            levels.append("CRITICAL")
            keywords.extend(crit_kw)

    imp_kw = IMPORTANT_PATTERNS.findall(t)
    if imp_kw:
        levels.append("IMPORTANT")
        keywords.extend(imp_kw)

    wat_kw = WATCH_PATTERNS.findall(t)
    if wat_kw:
        levels.append("WATCH")
        keywords.extend(wat_kw)

    # 去重
    # findall 可能返回 tuple（多捕获组时），统一转字符串
    keywords = list(set(
        kw[0] if isinstance(kw, tuple) else kw
        for kw in keywords
    ))

    # 排序: CRITICAL > IMPORTANT > WATCH
    level_order = {"CRITICAL": 0, "IMPORTANT": 1, "WATCH": 2}
    levels = sorted(set(levels), key=lambda l: level_order.get(l, 99))

    return {
        "levels": levels,
        "primary": levels[0] if levels else None,
        "keywords": keywords[:6],  # 最多 6 个
    }


def quality_score(title: str, snippet: str, url: str) -> tuple[int, list[str]]:
    """质量评分 (0=纯净, 越高污染越严重)

    Returns:
        (score, flags): 分数和标记列表
    """
    t = (title + " " + snippet).lower()
    u = url.lower()
    flags = []
    score = 0

    # 信任源直接通过
    if any(trusted in u for trusted in TRUSTED_SOURCES):
        return (0, ["trusted_source"])

    # AI 生成内容 +3
    ai_hits = AI_GEN_PATTERNS.findall(t)
    if ai_hits:
        score += 3
        flags.append(f"ai_gen({len(ai_hits)})")

    # SEO 污染 +2
    seo_hits = SEO_CLUE_PATTERNS.findall(t)
    if seo_hits:
        score += 2
        flags.append(f"seo({len(seo_hits)})")

    # 陈旧内容 +1
    if STALE_CLUE.search(t):
        score += 1
        flags.append("stale")

    # 陈词滥调 +1
    if CLICHE_PATTERNS.search(t):
        score += 1
        flags.append("cliche")

    # 流量内容（股票/加密/体育等）+2
    if FLOOD_PATTERNS.search(t):
        score += 2
        flags.append("flood")

    # SEO 风格 URL +1
    if u.count("-") > 8:
        score += 1
        flags.append("seo_url")

    # 黑名单域名 +2
    if any(bl in u for bl in SOURCE_BLACKLIST):
        score += 2
        flags.append("blacklisted_domain")

    return (score, flags)


def is_worth_sending(pollution_score: int, primary_level: str) -> bool:
    """判断条目是否值得发送

    容忍度: CRITICAL 容忍度 4, IMPORTANT 3, WATCH 2
    """
    tolerance = POLLUTION_TOLERANCE.get(primary_level, 2)
    return pollution_score <= tolerance
