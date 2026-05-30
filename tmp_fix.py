import ast

fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1) 凌晨模式 + RSS预取
old1 = '    print("=" * 50)\n\n    # 初始化'
new1 = '    print("=" * 50)\n\n    # 凌晨模式: 0-8点跳过Bing/Google搜索(国外源限速)\n    if _now_c().hour < 8:\n        print("[凌晨模式] 跳过Bing/Google搜索, 仅RSS")\n        _night_mode = True\n    else:\n        print("[日间模式] 全链路采集")\n        _night_mode = False\n\n    # RSS预取(所有节点共享)\n    _rss_cache = []\n    if feeds:\n        try:\n            from monitor.collector.rss import search_feeds as _sf\n            _rss_cache = _sf(feeds)\n            print(f"  [RSS] 预取 {len(_rss_cache)} 条")\n        except Exception as _e:\n            print(f"  [RSS] 预取失败: {_e}")\n\n    # 初始化'
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
    content = content.replace(old3, new3, 1)
    changes.append("GGL")
else:
    changes.append("GGL_FAIL")

# 4) RSS
old4 = '        # 兜底: RSS feed（如果前两个都挂了）\n        if not source_ok and feeds:\n            try:\n                rss_items = search_feeds(feeds)\n                # 只取跟当前节点关键词相关的条目\n                for it in rss_items:\n                    t = (it["t"] + " " + it["s"]).lower()\n                    if any(kw.lower() in t for kw in keywords):\n                        all_items.append(it)\n                if all_items:\n                    source_ok = True\n                    print("[RSS]", end=" ", flush=True)\n            except Exception as e:\n                print(f"  [{node_name}] RSS error: {e}")'
new4 = '        # 兜底: RSS匹配(使用预取数据)\n        if not source_ok and _rss_cache:\n            for _rit in _rss_cache:\n                _rt = (_rit["t"] + " " + _rit["s"]).lower()\n                if any(_kw.lower() in _rt for _kw in keywords):\n                    all_items.append(_rit)\n            if all_items:\n                source_ok = True\n                print("[RSS]", end=" ", flush=True)'
if old4 in content:
    content = content.replace(old4, new4, 1)
    changes.append("RSS")
else:
    changes.append("RSS_FAIL")

ast.parse(content)
with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("修改:", " ".join(changes))
print("编译OK")