import ast

fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1) 凌晨模式 header
old1 = '    print("=" * 50)\n\n    # 初始化'
new1 = '    print("=" * 50)\n\n    _night_mode = _now_c().hour < 8\n\n    _rss_cache = []\n    if _night_mode:\n        try:\n            from monitor.collector.rss import search_feeds as _sf\n            _rss_cache = _sf(feeds)\n            print(f"  [RSS] 预取 {len(_rss_cache)} 条")\n        except Exception as _e:\n            print(f"  [RSS] 预取失败: {_e}")\n\n    # 初始化'
if old1 in content:
    content = content.replace(old1, new1, 1)
    changes.append("HDR")
else:
    changes.append("HDR_FAIL")

# 2) Bing
old2 = '                items = bing_search(kw)'
new2 = '                items = [] if _night_mode else bing_search(kw)'
if old2 in content:
    content = content.replace(old2, new2, 1)
    changes.append("BNG")
else:
    changes.append("BNG_FAIL")

# 3) Google
old3 = '                items = google_news_search(kw)'
new3 = '                items = [] if _night_mode else google_news_search(kw)'
if old3 in content:
    # 只替换第一个（Bing后面还有一个）
    content = content.replace(old3, new3, 1)
    changes.append("GGL")
else:
    changes.append("GGL_FAIL")

# 4) RSS - 只改 兜底 块内的 search_feeds 调用
old4_rss = '                rss_items = search_feeds(feeds)'
new4_rss = '                rss_items = _rss_cache'
if old4_rss in content:
    content = content.replace(old4_rss, new4_rss, 1)
    changes.append("RSS")
else:
    changes.append("RSS_FAIL")

# 验证
ast.parse(content)
with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("修改:", " ".join(changes))
print("编译OK")