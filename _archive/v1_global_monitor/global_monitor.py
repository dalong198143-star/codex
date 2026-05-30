"""Global Node Monitor v2 ? ??????????

Usage:
    python global_monitor.py scan             # one-time scan
    python global_monitor.py daemon           # continuous mode (default 120min)
    python global_monitor.py show-config      # show config
    python global_monitor.py summary          # scan summary & trends
    python global_monitor.py query <keyword>  # active query
    python global_monitor.py dashboard        # generate HTML dashboard
    python global_monitor.py hot              # show trending topics
"""

import urllib.request, urllib.parse, re, html as html_module
import smtplib, email.utils, json
from email.message import EmailMessage
import datetime, os, sys, time, hashlib, sqlite3, pathlib, collections

# ???????????????????????????????????????????????????????????????
# CONFIG
# ???????????????????????????????????????????????????????????????

NODE_CONFIG = {
    "IXP: \u6cd5\u5170\u514b\u798f (DE-CIX)": {"kw": "DE-CIX Frankfurt internet exchange", "tags": ["ixp","europe"]},
    "IXP: \u4f26\u6566 (LINX)":       {"kw": "LINX London internet exchange",     "tags": ["ixp","europe"]},
    "IXP: \u65b0\u52a0\u5761 (SGIX)":     {"kw": "Singapore internet exchange hub",   "tags": ["ixp","asia"]},
    "IXP: \u4e1c\u4eac":              {"kw": "Tokyo internet exchange traffic",   "tags": ["ixp","asia"]},
    "\u6d77\u7f06: \u5168\u7403\u52a8\u6001":          {"kw": "submarine cable system 2026",      "tags": ["cable","infra"]},
    "\u6570\u636e\u4e2d\u5fc3: \u5317\u5f17\u5409\u5c3c\u4e9a":    {"kw": "Northern Virginia data center",     "tags": ["dc","north-america"]},
    "\u6570\u636e\u4e2d\u5fc3: \u5168\u7403\u6295\u8d44":      {"kw": "hyperscale data center investment","tags": ["dc","investment"]},
    "AI: \u57fa\u7840\u8bbe\u65bd\u6295\u8d44":        {"kw": "AI infrastructure investment 2026","tags": ["ai","infra"]},
    "\u653f\u7b56: \u4e92\u8054\u7f51\u76d1\u7ba1":        {"kw": "internet regulation AI regulation","tags": ["policy","geo"]},
    "\u536b\u661f: \u4e92\u8054\u7f51":           {"kw": "Starlink satellite internet new",  "tags": ["satellite","infra"]},
    "\u4e2d\u4e1c: \u6570\u5b57\u5316\u67a2\u7ebd":        {"kw": "UAE Dubai data center hub",        "tags": ["middle-east","infra"]},
    "\u975e\u6d32: \u4e92\u8054\u7f51\u57fa\u5efa":        {"kw": "Africa submarine cable internet",  "tags": ["africa","emerging"]},
}

# ?? ??????? ??????????????????????????????????????????????
# CRITICAL: ??/??/????/????  ? ?????
# IMPORTANT: ????/??/??/??   ? ???
# WATCH: ??????                 ? ??????

CRITICAL_PATTERNS = re.compile(
    r"(cable cut|outage|disrupt|breach|cyber attack|"
    r"billion\s*(?:investment|funding|deal)|"
    r"export control|ban|sanction|blocked|"
    r"new\s*(?:submarine|cable|landing\s*station|"
    r"internet\s*(?:exchange|backbone)|data\s*center\s*campus)|"
    r"Starlink\s*(?:launch|constellation|expansion)|"
    r"record\s*(?:traffic|bandwidth|capacity))", re.IGNORECASE)

IMPORTANT_PATTERNS = re.compile(
    r"(launch|invest|fund|partner|expand|breakthrough|"
    r"data center|internet exchange|IXP|"
    r"AI\s*(?:infrastructure|data center|chip|model)|"
    r"semiconductor|chip\s*(?:manufacturing|factory|plant)|"
    r"hyperscale|cloud region|edge\s*node|"
    r"satellite|LEO|constellation|"
    r"regulation|regulatory|"
    r"(?:million|billion)\s*(?:users|deploy|project))", re.IGNORECASE)

WATCH_PATTERNS = re.compile(
    r"(AI|artificial intelligence|"
    r"funding|acquir|investment|"
    r"digit(al|ization)|transformation|"
    r"emerging market|undersea|submarine|"
    r"UAE|Dubai|Saudi|Africa|Southeast Asia|"
    r"chip|semiconductor)", re.IGNORECASE)

LEVEL_COLORS = {"CRITICAL": "#dc3545", "IMPORTANT": "#e67e22", "WATCH": "#3498db"}
LEVEL_LABELS = {"CRITICAL": "\U0001f534 \u5173\u952e", "IMPORTANT": "\U0001f7e0 \u91cd\u8981", "WATCH": "\U0001f535 \u5173\u6ce8"}

# ??: ???????
SOURCE_BLACKLIST = [
    "dictionary.com", "vocabulary.com", "merriam-webster.com", "cambridge.org",
    "wikipedia.org", "youtube.com", "instagram.com", "facebook.com",
    "reddit.com", "ebay.com", "amazon.com", "imdb.com",
]
# ??: ????????????????????????
NODE_NOISE_FLOOR = {"default": 0}

BLOCKED = ["dictionary", "vocabulary", "merriam", "cambridge.org"]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "codex_monitor")
DB_PATH = os.path.join(DB_DIR, "monitor.db")
DASHBOARD_PATH = os.path.join(DB_DIR, "dashboard.html")

# ?? ?????? ?????????????????????????????????????????????????
_env_loaded = False
def _load_env():
    global _env_loaded
    if _env_loaded:
        return
    env_path = pathlib.Path(__file__).parent / ".monitor.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k not in os.environ:
                os.environ[k] = v
    _env_loaded = True

_load_env()

# KB sync
_KB_CLIENT = None
def _get_kb():
    global _KB_CLIENT
    if _KB_CLIENT is not None:
        return _KB_CLIENT
    try:
        import sys as _sys
        _p = "D:/hermes-tools/scripts"
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
        from kb_client import kb_add
        _KB_CLIENT = kb_add
    except Exception as e:
        _KB_CLIENT = False
    return _KB_CLIENT

def _sync_to_kb(items):
    """向知识库同步高质量内容 — 配合 kb_server 的 topic/去重机制"""
    kb_add = _get_kb()
    if not kb_add:
        return
    for it in items:
        if it.get("level") not in ("CRITICAL", "IMPORTANT"):
            continue
        try:
            node = it.get("n", "?")
            title = it["t"][:120]
            snippet = it["s"][:400]
            url = it.get("u", "")
            level = it.get("level", "WATCH")
            kw = ", ".join(it.get("kw", []))
            content = f"[{level}] [{node}] {title}\n{snippet}\n来源: {url}\n关键词: {kw}"
            section = f"{node} - {title[:60]}"
            kb_add(content, topic="global-infra", section=section)
        except Exception as e:
            print(f"  [KB] sync fail: {e}")

MAIL = {
    "to": os.environ.get("MAIL_TO", ""),
    "from": os.environ.get("MAIL_FROM", "monitor@localhost"),
    "host": os.environ.get("SMTP_HOST", "smtp.qq.com"),
    "port": int(os.environ.get("SMTP_PORT", "465")),
    "user": os.environ.get("SMTP_USER", ""),
    "pass": os.environ.get("SMTP_PASS", ""),
    "ssl": os.environ.get("SMTP_SSL", "1") == "1",
}

# ???????????????????????????????????????????????????????????????
# CLASSIFICATION
# ???????????????????????????????????????????????????????????????

def classify(item):
    t = (item["t"] + " " + item["s"]).lower()
    crit = CRITICAL_PATTERNS.findall(t)
    if crit:
        return ("CRITICAL", crit)
    imp = IMPORTANT_PATTERNS.findall(t)
    if imp:
        return ("IMPORTANT", imp)
    wat = WATCH_PATTERNS.findall(t)
    if wat:
        return ("WATCH", wat)
    return (None, [])

def is_val(item):
    t = (item["t"]+" "+item["s"]).lower()
    if len(t) <= 60:
        return (False, None, [])
    level, kw = classify(item)
    return (level is not None, level, kw)

# ?? ???? ??????????????????????????????????????????????????
# AI ??????
AI_GEN_PATTERNS = re.compile(
    r"(here is|here are|below are|as an ai|as a language model|"
    r"I cannot|I don't have|I'm not able to|"
    r"in conclusion|in summary|to summarize|"
    r"it is important to note that|"
    r"this is a great question|"
    r"based on my research|according to my sources|"
    r"certainly!|absolutely!|of course!)", re.IGNORECASE)

# SEO ??????
SEO_CLUE_PATTERNS = re.compile(
    r"(click here|read more|learn more|sponsored|advertisement|"
    r"best\s*(?:price|deal|offer|discount|coupon)|"
    r"top\s*\d+\s*(?:way|tip|trick|reason|thing)|"
    r"you need to know|you should know|"
    r"this is why|the reason why|"
    r"affiliate|promo code|exclusive deal)", re.IGNORECASE)

# ??/?????
STALE_CLUE = re.compile(
    r"(2024|2023|2022|last year|two years ago|"
    r"was announced|was launched|earlier this year|"
    r"according to reports|reportedly|"
    r"is said to be|is believed to be)", re.IGNORECASE)

# ???????
CLICHE_PATTERNS = re.compile(
    r"(revolutionary|game-changing|groundbreaking|"
    r"unprecedented|next-generation|cutting-edge|"
    r"industry-leading|world-class|best-in-class|"
    r"disruptive|innovative|transformative)", re.IGNORECASE)

# ????/????
FLOOD_PATTERNS = re.compile(
    r"(stock\s*(?:market|price|trading)|"
    r"cryptocurrency|bitcoin|nft|"
    r"metaverse|web3|blockchain|"
    r"sports|entertainment|celebrity|"
    r"weather|forecast|earthquake|"
    r"recipe|diet|fitness|workout)", re.IGNORECASE)

# ??????????????
TRUSTED_SOURCES = [
    "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com",
    "nytimes.com", "bbc.com", "bbc.co.uk", "cnbc.com", "economist.com",
    "techcrunch.com", "theverge.com", "arstechnica.com",
    "wired.com", "nature.com", "science.org",
    "datacenterdynamics.com", "lightreading.com", "fierce-network.com",
    "submarinenetworks.com", "telecompaper.com",
]

def quality_score(item):
    """?????? (0=??, ????) ?????"""
    t = (item["t"] + " " + item["s"]).lower()
    url = item.get("u", "").lower()
    flags = []
    score = 0

    # ???????
    if any(trusted in url for trusted in TRUSTED_SOURCES):
        return (0, ["trusted_source"])

    # AI ???? - ???? (+3)
    ai_hits = AI_GEN_PATTERNS.findall(t)
    if ai_hits:
        score += 3
        flags.append(f"ai_gen({len(ai_hits)})")

    # SEO ???? (+2)
    seo_hits = SEO_CLUE_PATTERNS.findall(t)
    if seo_hits:
        score += 2
        flags.append(f"seo({len(seo_hits)})")

    # ???? (+2)
    stale_hits = STALE_CLUE.findall(t)
    if stale_hits:
        score += 2
        flags.append(f"stale({len(stale_hits)})")

    # ???? (+1)
    cliche_hits = CLICHE_PATTERNS.findall(t)
    if cliche_hits:
        score += 1
        flags.append(f"cliched({len(cliche_hits)})")

    # ?????? (+2)
    flood_hits = FLOOD_PATTERNS.findall(t)
    if flood_hits:
        score += 2
        flags.append(f"off_topic({len(flood_hits)})")

    # URL ????
    if url.count("-") > 8:  # ??SEO??URL
        score += 1
        flags.append("seo_url")
    if any(bl in url for bl in SOURCE_BLACKLIST):
        score += 2
        flags.append("blacklisted_domain")

    return (score, flags)

# ????????
POLLUTION_TOLERANCE = {
    "CRITICAL": 4,   # CRITICAL ???????????????
    "IMPORTANT": 3,  # IMPORTANT ????
    "WATCH": 2,      # WATCH ????
}

def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS seen(id TEXT PRIMARY KEY,ts TIMESTAMP)")
    conn.execute("CREATE TABLE IF NOT EXISTS log(ts TIMESTAMP,node TEXT,n INTEGER,new INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS hotwords(word TEXT PRIMARY KEY,count INTEGER,last_seen TIMESTAMP,peak INTEGER)")
    conn.commit()
    return conn

def seen(h):
    conn = _db()
    r = conn.execute("SELECT 1 FROM seen WHERE id=?",(h,)).fetchone()
    conn.close()
    return r is not None

def mark(h):
    conn = _db()
    conn.execute("INSERT OR IGNORE INTO seen VALUES(?,?)",(h,datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def log_scan(node, n, new):
    conn = _db()
    conn.execute("INSERT INTO log VALUES(?,?,?,?)",(datetime.datetime.utcnow().isoformat(),node,n,new))
    conn.commit()
    conn.close()

def track_hotwords(keywords):
    """???????????????"""
    conn = _db()
    now = datetime.datetime.utcnow().isoformat()
    heated = []
    for kw in keywords:
        kw = kw.lower().strip()
        if len(kw) < 3:
            continue
        row = conn.execute("SELECT count, peak FROM hotwords WHERE word=?", (kw,)).fetchone()
        if row:
            cnt = row[0] + 1
            peak = max(cnt, row[1])
            conn.execute("UPDATE hotwords SET count=?, last_seen=?, peak=? WHERE word=?", (cnt, now, peak, kw))
        else:
            cnt = 1
            conn.execute("INSERT INTO hotwords VALUES(?,?,?,?)", (kw, cnt, now, cnt))
        # ???2??????????>=3?????
        if cnt >= 3:
            heated.append(kw)
    conn.commit()
    conn.close()
    return heated

# ???????????????????????????????????????????????????????????????
# MULTI-SOURCE SEARCH
# ???????????????????????????????????????????????????????????????

def _fetch_url(url, timeout=8):
    """获取 URL 内容 — 绕过系统代理，带重试"""
    import urllib.request as _ur
    handler = _ur.ProxyHandler({})
    opener = _ur.build_opener(handler)
    for attempt in range(2):
        try:
            req = _ur.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            return opener.open(req, timeout=timeout).read().decode("utf-8", errors="replace")
        except Exception:
            if attempt == 0:
                time.sleep(1)
                continue
            return None
    return None
_SOURCE_HEALTH = {
    "bing": {"last_ok": 0.0, "fail_count": 0},
    "google-news-rss": {"last_ok": 0.0, "fail_count": 0},
}


def _check_sources():
    """检查数据源可达性，返回 (ok: bool, report: str)"""
    report_lines = []
    all_ok = True
    now = time.time()
    for src_name, src_url in [
        ("bing", "https://www.bing.com"),
        ("google-news-rss", "https://news.google.com"),
    ]:
        data = _fetch_url(src_url, timeout=5)
        if data:
            _SOURCE_HEALTH[src_name]["last_ok"] = now
            _SOURCE_HEALTH[src_name]["fail_count"] = 0
        else:
            _SOURCE_HEALTH[src_name]["fail_count"] += 1
            all_ok = False
        status = "OK" if data else "DOWN"
        fails = _SOURCE_HEALTH[src_name]["fail_count"]
        report_lines.append(f"  {src_name}: {status} (fail streak: {fails})")
    report = "\n".join(report_lines)
    # 连续失败 3 次才告警，避免偶发超时误报
    critical = any(
        h["fail_count"] >= 3 for h in _SOURCE_HEALTH.values()
    )
    return all_ok or not critical, report



def bing(query):
    """Bing??"""
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query) + "&count=6"
    data = _fetch_url(url)
    if not data:
        return []
    results = []
    for block in re.split(r'<li class="b_algo"', data)[1:9]:
        try:
            tm = re.search(r'<h2><a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block)
            sm = re.search(r'<p[^>]*>(.*?)</p>', block)
            if not tm:
                continue
            url = tm.group(1)
            if any(d in url for d in BLOCKED):
                continue
            if not sm:
                continue
            title = html_module.unescape(tm.group(2))[:150]
            snippet = html_module.unescape(sm.group(1))[:500]
            results.append({"t": title, "u": url, "s": snippet, "src": "bing"})
        except:
            continue
    return results

def google_news_rss(query):
    """Google News RSS (??API key)"""
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en"
    data = _fetch_url(url)
    if not data:
        return []
    results = []
    for item in re.findall(r'<item>.*?</item>', data, re.DOTALL):
        try:
            title = re.search(r'<title>(.*?)</title>', item)
            link = re.search(r'<link>(.*?)</link>', item)
            desc = re.search(r'<description>(.*?)</description>', item)
            if not title or not link:
                continue
            results.append({
                "t": html_module.unescape(title.group(1))[:150],
                "u": link.group(1),
                "s": html_module.unescape(desc.group(1)[:500] if desc else title.group(1)),
                "src": "google-news"
            })
        except:
            continue
    return results[:6]

def search_all(query):
    """????????????"""
    all_items = []
    seen_urls = set()
    for src_fn in [bing, google_news_rss]:
        try:
            items = src_fn(query)
            for it in items:
                if it["u"] not in seen_urls:
                    seen_urls.add(it["u"])
                    all_items.append(it)
        except Exception as e:
            pass
    return all_items

# ???????????????????????????????????????????????????????????????
# MAIL
# ???????????????????????????????????????????????????????????????

def send(subject, html_body):
    if not MAIL["to"]:
        print("[Mail] No MAIL_TO, printing report...")
        print(html_body[:600])
        return
    m = EmailMessage()
    m["Subject"] = subject; m["From"] = MAIL["from"]; m["To"] = MAIL["to"]
    m["Date"] = email.utils.formatdate()
    m.set_content(re.sub(r"<[^>]+>","",html_body))
    m.add_alternative(html_body, subtype="html")
    try:
        if MAIL["ssl"]:
            with smtplib.SMTP_SSL(MAIL["host"], MAIL["port"], timeout=15) as s:
                if MAIL["user"]: s.login(MAIL["user"], MAIL["pass"])
                s.send_message(m)
        else:
            with smtplib.SMTP(MAIL["host"], MAIL["port"], timeout=15) as s:
                s.starttls()
                if MAIL["user"]: s.login(MAIL["user"], MAIL["pass"])
                s.send_message(m)
        print(f"[Mail] Sent: {subject}")
    except Exception as e: print(f"[Mail] Fail: {e}")

def send_hot_alert(hotwords, details):
    """????????"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""<html><meta charset='utf-8'><body style='max-width:700px;margin:20px auto;font:14px/1.5 system-ui'>
    <h1 style='color:#e67e22'>?? Hot Topic Alert</h1>
    <p>{now}</p>
    <p>Keywords surging: {', '.join(hotwords)}</p>
    <hr>"""
    for d in details[:10]:
        html += f"<div style='margin:8px 0;padding:8px;background:#fff3cd'><b>{html_module.escape(d['t'])}</b><br><span style='color:#666'>{html_module.escape(d['s'][:200])}</span></div>"
    html += "</body></html>"
    send(f"[Hot] {', '.join(hotwords[:3])} surging | {datetime.datetime.now():%m-%d %H:%M}", html)

def _get_source_domain(url):
    import re
    m = re.search(r"https?://([^/]+)", url)
    if m:
        return m.group(1).replace("www.", "")
    return url[:40]

def build_report(items):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    by_level = {"CRITICAL": [], "IMPORTANT": [], "WATCH": []}
    for i in items:
        by_level.setdefault(i.get("level","WATCH"), []).append(i)
    # === 生成内容简介 ===
    by_node_summary = {}
    for i in items:
        n = i.get("n", "?")
        lv = i.get("level", "WATCH")
        by_node_summary.setdefault(n, {"CRITICAL": 0, "IMPORTANT": 0, "WATCH": 0})
        by_node_summary[n][lv] = by_node_summary[n].get(lv, 0) + 1

    summary_lines = []
    for n in sorted(by_node_summary.keys()):
        parts_line = []
        for lv in ["CRITICAL", "IMPORTANT", "WATCH"]:
            c = by_node_summary[n].get(lv, 0)
            if c:
                color = LEVEL_COLORS[lv]
                parts_line.append(f'<span style="color:{color};font-weight:700">{c}{{"关键" if lv=="CRITICAL" else "重要" if lv=="IMPORTANT" else "关注"}}</span>')
        if parts_line:
            summary_lines.append(f"  &bull; {html_module.escape(n)}: {" + ".join(parts_line)}")
    summary_html = "<br>".join(summary_lines) if summary_lines else "<em>无内容</em>"

    parts = [
        f"<h1>🌍 Global Monitor</h1>",
        f"<p style='color:#888;margin:-8px 0 12px 0'>{now} | {len(items)} items from Bing+Google News</p>",
        f"<div style='padding:10px 14px;background:#f0f4f8;border-radius:6px;margin-bottom:16px;font-size:13px;line-height:1.8'>"
        f"<b style='font-size:14px'>📋 本期概要</b><br>{summary_html}</div>"
    ]
    for level in ["CRITICAL", "IMPORTANT", "WATCH"]:
        its = by_level.get(level, [])
        if not its:
            continue
        color = LEVEL_COLORS.get(level, "#666")
        label = LEVEL_LABELS.get(level, level)
        by_node = {}
        for i in its:
            by_node.setdefault(i.get("n","?"), []).append(i)
        parts.append(f"<h2 style='color:{color}'>{label} ({len(its)})</h2>")
        for n, nitems in by_node.items():
            parts.append(f"<h3 style='margin:6px 0;font-size:13px;color:#555'>{n}</h3>")
            for i in nitems:
                t = html_module.escape(i["t"]); s = html_module.escape(i["s"][:280])
                kw = " | ".join(i.get("kw", []))
                u_raw = i.get("u", "")
                src_raw = i.get("src", "")
                if "google-news" in src_raw:
                    link_display = f'<a href="{html_module.escape(u_raw)}">{html_module.escape(_get_source_domain(u_raw))}</a>'
                else:
                    display_trunc = u_raw[:50] + ("..." if len(u_raw) > 50 else "")
                    link_display = f'链接: <a href="{html_module.escape(u_raw)}">{html_module.escape(display_trunc)}</a>'
                src = html_module.escape(i.get("src", ""))
                flags = ""
                if i.get("pol_score", 0) > 0:
                    flags = f" | pollute:{i['pol_score']}"
                parts.append(f"<div style='border-left:4px solid {color};margin:6px 0;padding:6px 10px;background:#f8f9fa'><b>{t}</b><br>{s}<br>{link_display}<br><span style='font-size:11px;color:#888'>[{kw}] src:{src}{flags}</span></div>")
    html = "<html><meta charset='utf-8'><body style='max-width:700px;margin:20px auto;font:14px/1.5 system-ui'>"
    html += "".join(parts) + "</body></html>"
    return html

# ???????????????????????????????????????????????????????????????
# SCAN
# ???????????????????????????????????????????????????????????????

_scan_start = None

def scan():
    global _scan_start
    all_val = []
    hot_candidates = []
    stats = {"CRITICAL": 0, "IMPORTANT": 0, "WATCH": 0}
    filtered_count = 0
    deadline = time.monotonic() + 90  # 90s total (longer with multi-source)
    for name, cfg in NODE_CONFIG.items():
        if time.monotonic() > deadline:
            print(f"[{name}] SKIP (timeout)")
            continue
        print(f"[{name}] ...", end=" ", flush=True)
        items = search_all(cfg["kw"])  # ? ????
        new = 0
        for it in items:
            h = hashlib.sha256(it["s"].encode()).hexdigest()[:16]
            valuable, level, kw = is_val(it)
            if valuable and not seen(h):
                # ???????
                if any(bl in it.get("u","").lower() for bl in SOURCE_BLACKLIST):
                    continue
                # ????
                pol_score, pol_flags = quality_score(it)
                tolerance = POLLUTION_TOLERANCE.get(level, 2)
                if pol_score > tolerance:
                    filtered_count += 1
                    print(f"      [filtered] pol_score={pol_score} {pol_flags}")
                    continue
                mark(h)
                it["n"] = name
                it["level"] = level
                it["kw"] = kw[:3]
                it["pol_score"] = pol_score
                it["pol_flags"] = pol_flags
                all_val.append(it)
                hot_candidates.extend(kw)
                stats[level] = stats.get(level, 0) + 1
                new += 1
        log_scan(name, len(items), new)
        print(f"{len(items)} items, {new} new")
        time.sleep(0.3)
    print(f"\nTotal: {len(all_val)} new items (CRITICAL={stats['CRITICAL']}, IMPORTANT={stats['IMPORTANT']}, WATCH={stats['WATCH']}), filtered={filtered_count}")
    return all_val, stats, hot_candidates

# ???????????????????????????????????????????????????????????????
# CLI COMMANDS
# ???????????????????????????????????????????????????????????????

def show_config():
    print(f"Nodes: {len(NODE_CONFIG)}")
    for n,c in NODE_CONFIG.items():
        print(f"  {n} | {c['kw']}")
    print(f"Mail to: {MAIL['to'] or '[not set]'}")
    print(f"Data sources: Bing + Google News RSS")
    print(f"DB: {DB_PATH}")
    print(f"Dashboard: {DASHBOARD_PATH}")

def cmd_scan():
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] Global Node Scan (multi-source)")
    print("="*50)
    val, stats, hot_candidates = scan()
    if not val:
        print("No new valuable info.")
        return

    # ????
    heated = track_hotwords(hot_candidates)
    if heated:
        print(f"\n?? Hot keywords detected: {heated}")
        send_hot_alert(heated, val[:10])

    crit = [v for v in val if v.get("level") == "CRITICAL"]
    imp = [v for v in val if v.get("level") == "IMPORTANT"]
    watch = [v for v in val if v.get("level") == "WATCH"]
    # ? DB ?????????24h?
    conn = sqlite3.connect(DB_PATH)
    day_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat()
    total_fetched = conn.execute("SELECT COALESCE(SUM(n),0) FROM log WHERE ts > ?", (day_ago,)).fetchone()[0]
    total_accepted = conn.execute("SELECT COUNT(*) FROM seen WHERE ts > ?", (day_ago,)).fetchone()[0]
    conn.close()
    filtered_24h = max(0, total_fetched - total_accepted)
    print(f"[Filter] 24h: {total_fetched} fetched, {total_accepted} accepted, ~{filtered_24h} filtered")

    _sync_to_kb(val)

    if crit or imp:
        send(f"[Monitor] C={len(crit)} I={len(imp)} | {datetime.datetime.now():%m-%d %H:%M}", build_report(val))
    if watch:
        print(f"[Watch] {len(watch)} watch-level items logged (no mail)")

    # ???????
    try:
        cmd_dashboard()
    except:
        pass

def cmd_daemon():
    interval = int(os.environ.get("INTERVAL", "120"))
    print(f"Daemon mode - every {interval} min")
    while True:
        try:
            cmd_scan()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
        nxt = datetime.datetime.now() + datetime.timedelta(minutes=interval)
        print(f"Next: {nxt:%H:%M}\n{'='*50}")
        time.sleep(interval * 60)

def cmd_summary():
    conn = sqlite3.connect(DB_PATH)
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] Monitor Summary")
    print("="*50)
    r = conn.execute("SELECT COUNT(*), MAX(ts) FROM log").fetchone()
    print(f"Total scans: {r[0]}  |  Last scan: {r[1] or 'never'}")
    r = conn.execute("SELECT COUNT(*) FROM seen").fetchone()
    print(f"Unique discoveries: {r[0]}")
    print()
    print("--- Last 24h by node ---")
    day_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat()
    rows = conn.execute("SELECT node, SUM(n), SUM(new) FROM log WHERE ts > ? GROUP BY node ORDER BY node", (day_ago,)).fetchall()
    for node, total, new in rows:
        print(f"  {node}: {total} items, {new} new")
    print()
    # ???
    print("--- Hot Keywords ---")
    rows = conn.execute("SELECT word, count, peak, last_seen FROM hotwords ORDER BY peak DESC LIMIT 15").fetchall()
    for w, cnt, peak, last in rows:
        print(f"  {w}: count={cnt}, peak={peak}")
    conn.close()

def cmd_query():
    if len(sys.argv) < 3:
        print("Usage: python global_monitor.py query <keyword or node_name>")
        print("  Built-in nodes:")
        for n in NODE_CONFIG:
            print(f"    - {n}")
        return
    q = sys.argv[2]
    matched = [n for n in NODE_CONFIG if q.lower() in n.lower()]
    if matched:
        for name in matched:
            kw = NODE_CONFIG[name]["kw"]
            print(f"[{name}] searching (Bing+Google News): {kw}")
            items = search_all(kw)
            print(f"  {len(items)} results")
            for it in items[:5]:
                valuable, level, _ = is_val(it)
                tag = f"[{level}]" if level else ""
                print(f"  {tag} {it['t'][:80]}")
                print(f"      {it['u']}  [{it['src']}]")
                print()
    else:
        print(f"Searching: {q}")
        items = search_all(q)
        print(f"  {len(items)} results")
        for it in items[:5]:
            valuable, level, _ = is_val(it)
            tag = f"[{level}]" if level else ""
            print(f"  {tag} {it['t'][:80]}")
            print(f"      {it['u']}  [{it['src']}]")
            print()

def cmd_hot():
    """?????"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT word, count, peak, last_seen FROM hotwords ORDER BY peak DESC LIMIT 20").fetchall()
    if not rows:
        print("No hot keywords tracked yet.")
    else:
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] Hot Keywords")
        print("="*50)
        for w, cnt, peak, last in rows:
            bar = "\u2588" * min(peak, 20)
            print(f"  {bar} {w} (count={cnt}, peak={peak})")
    conn.close()

def cmd_dashboard():
    """?? HTML ???"""
    conn = sqlite3.connect(DB_PATH)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # ????
    total_scans = conn.execute("SELECT COUNT(*) FROM log").fetchone()[0]
    last_scan = conn.execute("SELECT MAX(ts) FROM log").fetchone()[0] or "never"
    discoveries = conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]

    # 24h ????
    day_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat()
    node_rows = conn.execute("SELECT node, SUM(n), SUM(new) FROM log WHERE ts > ? GROUP BY node ORDER BY node", (day_ago,)).fetchall()

    # ???
    hot_rows = conn.execute("SELECT word, peak FROM hotwords ORDER BY peak DESC LIMIT 20").fetchall()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Global Monitor Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font:14px/1.6 system-ui; background:#f5f6fa; color:#333; padding:20px; }}
  .container {{ max-width:900px; margin:0 auto; }}
  h1 {{ font-size:24px; margin-bottom:4px; }}
  .subtitle {{ color:#888; margin-bottom:20px; }}
  .cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:24px; }}
  .card {{ background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .card h3 {{ font-size:13px; color:#888; text-transform:uppercase; }}
  .card .num {{ font-size:28px; font-weight:700; }}
  .section {{ background:#fff; border-radius:8px; padding:16px 20px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .section h2 {{ font-size:16px; margin-bottom:12px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; font-size:12px; color:#888; padding:6px 0; border-bottom:1px solid #eee; }}
  td {{ padding:6px 0; border-bottom:1px solid #f0f0f0; }}
  .bar {{ display:inline-block; height:14px; border-radius:3px; min-width:2px; }}
</style>
</head>
<body>
<div class="container">
  <h1>\U0001f30d Global Monitor Dashboard</h1>
  <p class="subtitle">{now} | Multi-source (Bing + Google News)</p>

  <div class="cards">
    <div class="card"><h3>Scans</h3><div class="num">{total_scans}</div></div>
    <div class="card"><h3>Discoveries</h3><div class="num">{discoveries}</div></div>
    <div class="card"><h3>Last Scan</h3><div class="num" style="font-size:14px">{last_scan[:16]}</div></div>
  </div>

  <div class="section">
    <h2>24h \u8282\u70b9\u52a8\u6001</h2>
    <table><tr><th>Node</th><th>Items</th><th>New</th></tr>"""
    for node, total, new_ in node_rows:
        html += f"<tr><td>{html_module.escape(node)}</td><td>{total}</td><td>{new_}</td></tr>"
    html += "</table></div>"

    if hot_rows:
        max_peak = max(r[1] for r in hot_rows) if hot_rows else 1
        html += '<div class="section"><h2>?? Hot Keywords</h2><table><tr><th>Keyword</th><th>Trend</th><th>Peak</th></tr>'
        for w, p in hot_rows:
            pct = p / max_peak * 100
            color = "#dc3545" if p >= 5 else "#e67e22" if p >= 3 else "#3498db"
            html += f'<tr><td>{html_module.escape(w)}</td><td><span class="bar" style="width:{pct}%;background:{color}"></span></td><td>{p}</td></tr>'
        html += "</table></div>"

    html += "</div></body></html>"
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard: {DASHBOARD_PATH}")

if __name__ == "__main__":
    cmds = {
        "scan": cmd_scan, "daemon": cmd_daemon, "show-config": show_config,
        "summary": cmd_summary, "query": cmd_query, "dashboard": cmd_dashboard,
        "hot": cmd_hot,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__.strip())
        sys.exit(1)
    cmds[sys.argv[1]]()

