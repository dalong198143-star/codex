import ast

fp = r"D:\maozhua\Codex\codex\scripts\monitor\main.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# 1-3 已经成功，继续
# 4) RSS兜底 - 精确匹配原文
old_4 = (
    '        # 兜底: RSS feed（如果前两个都挂了）\n'
    '        if not source_ok and feeds:\n'
    '            try:\n'
    '                rss_items = search_feeds(feeds)\n'
    '                # 只取跟当前节点关键词相关的条目\n'
    '                for it in rss_items:\n'
    '                    t = (it["t"] + " " + it["s"]).lower()\n'
    '                    if any(kw.lower() in t for kw in keywords):\n'
    '                        all_items.append(it)\n'
    '                if all_items:\n'
    '                    source_ok = True\n'
    '                    print("[RSS]", end=" ", flush=True)\n'
    '            except Exception as e:\n'
    '                print(f"  [{node_name}] RSS error: {e}")'
)

new_4 = (
    '        # 兜底: RSS匹配(使用预取数据, 不重复请求)\n'
    '        if not source_ok and _prefetched_rss:\n'
    '            for _rss_it in _prefetched_rss:\n'
    '                _rt = (_rss_it["t"] + " " + _rss_it["s"]).lower()\n'
    '                if any(_kw.lower() in _rt for _kw in keywords):\n'
    '                    all_items.append(_rss_it)\n'
    '                    print("    [" + node_name + "] RSS match: " + _rss_it["t"][:50])\n'
    '                    source_ok = True\n'
    '                    print("[RSS]", end=" ", flush=True)'
)

if old_4 in content:
    content = content.replace(old_4, new_4, 1)
    print("4 OK")
else:
    # 打印差异来调试
    idx = content.find("兜底")
    snippet = content[idx:idx+450]
    print("old_4:")
    print(repr(old_4[:200]))
    print("\nactual:")
    print(repr(snippet[:200]))

ast.parse(content)
print("编译OK")

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("写入完成")
