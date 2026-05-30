import re, ast

fp = r"D:\maozhua\Codex\codex\scripts\monitor\main.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# 1) 凌晨模式插入
old_1 = '    print("=" * 50)\n\n    # 初始化'
new_1 = '    print("=" * 50)\n\n    # 凌晨模式(0-8点): 跳过Bing/Google搜索(凌晨国外源限速严重)\n    _current_hour = _now_c().hour\n    night_mode = _current_hour < 8\n    if night_mode:\n        _t = _now_str_c()[:5]\n        print(f"[{_t}] 凌晨模式: 跳过Bing/Google搜索, 仅RSS源")\n    else:\n        _t = _now_str_c()[:5]\n        print(f"[{_t}] 日间模式: 全链路采集")\n\n    # RSS预取: 所有节点共享, 避免每个节点都重新抓取全部源\n    _prefetched_rss = []\n    if feeds:\n        try:\n            from monitor.collector.rss import search_feeds as _sf\n            _prefetched_rss = _sf(feeds)\n            print("  [RSS] 预取", len(_prefetched_rss), "条候选条目")\n        except Exception as _e:\n            print("  [RSS] 预取失败:", _e)\n\n    # 初始化'

assert old_1 in content
content = content.replace(old_1, new_1, 1)
print("1 OK")

# 2) Bing跳过
old_2 = '        for kw in keywords:\n            try:\n                items = bing_search(kw)'
new_2 = '        if night_mode:\n            items = []\n        else:\n            for kw in keywords:\n                try:\n                    items = bing_search(kw)'
assert old_2 in content
content = content.replace(old_2, new_2, 1)
print("2 OK")

# 3) Google跳过
old_3 = '        if not source_ok:\n            for kw in keywords:\n                try:\n                    items = google_news_search(kw)'
new_3 = '        if not source_ok and not night_mode:\n            for kw in keywords:\n                try:\n                    items = google_news_search(kw)'
assert old_3 in content
content = content.replace(old_3, new_3, 1)
print("3 OK")

# 4) RSS兜底
old_4 = ('        # 兜底: RSS feed（如果前两个都挂了）\n'
    '        if not source_ok and feeds:\n'
    '            try:\n'
    '                rss_items = search_feeds(feeds)\n'
    '                # 只取跟当前节点关键词相关的条目\n'
    '                for it in rss_items:\n'
    '                    t = (it["t"] + " " + it["s"]).lower()\n'
    '                    if any(kw.lower() in t for kw in keywords):\n'
    '                        all_items.append(it)\n'
    '                        print("    [" + node_name + "] RSS match: " + it["t"][:50])\n'
    '            except Exception as e:\n'
    '                print(f"  [{node_name}] RSS error: {e}")')

new_4 = ('        # 兜底: RSS匹配(使用预取数据, 不重复请求)\n'
    '        if not source_ok and _prefetched_rss:\n'
    '            for _rss_it in _prefetched_rss:\n'
    '                _rt = (_rss_it["t"] + " " + _rss_it["s"]).lower()\n'
    '                if any(_kw.lower() in _rt for _kw in keywords):\n'
    '                    all_items.append(_rss_it)\n'
    '                    print("    [" + node_name + "] RSS match: " + _rss_it["t"][:50])\n'
    '                    source_ok = True\n'
    '                    print("[RSS]", end=" ", flush=True)')

assert old_4 in content, "old_4 not found:\n" + repr(content[content.find("兜底"):content.find("兜底")+200])
content = content.replace(old_4, new_4, 1)
print("4 OK")

ast.parse(content)
print("编译OK")

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("写入完成")
