import ast

fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# HDR + BNG + GGL 成功

# 4) RSS - 仅替换到 print("[RSS]", end=" ", flush=True) 这一行
old4 = '        # 兜底: RSS feed（如果前两个都挂了）\n        if not source_ok and feeds:\n            try:\n                rss_items = search_feeds(feeds)\n                # 只取跟当前节点关键词相关的条目\n                for it in rss_items:\n                    t = (it["t"] + " " + it["s"]).lower()\n                    if any(kw.lower() in t for kw in keywords):\n                        all_items.append(it)\n                if all_items:\n                    source_ok = True\n                    print("[RSS]", end=" ", flush=True)\n            except Exception as e:\n                print(f"  [{node_name}] RSS error: {e}")'
                
# 先检查块在不带 except 的情况下是否匹配
old4_noexcept = '        # 兜底: RSS feed（如果前两个都挂了）\n        if not source_ok and feeds:\n            try:\n                rss_items = search_feeds(feeds)\n                # 只取跟当前节点关键词相关的条目\n                for it in rss_items:\n                    t = (it["t"] + " " + it["s"]).lower()\n                    if any(kw.lower() in t for kw in keywords):\n                        all_items.append(it)\n                if all_items:\n                    source_ok = True\n                    print("[RSS]", end=" ", flush=True)'

new4 = '        # 兜底: RSS匹配(使用预取数据)\n        if not source_ok and _rss_cache:\n            for _rit in _rss_cache:\n                _rt = (_rit["t"] + " " + _rit["s"]).lower()\n                if any(_kw.lower() in _rt for _kw in keywords):\n                    all_items.append(_rit)\n            if all_items:\n                source_ok = True\n                print("[RSS]", end=" ", flush=True)'

if old4 in content:
    content = content.replace(old4, new4, 1)
    changes.append("RSS")
elif old4_noexcept in content:
    # 替换不带except的部分，然后找到并删除except行
    content = content.replace(old4_noexcept, new4, 1)
    # 找到旧的 except 行并删除
    idx = content.find("RSS error")
    if idx > 0:
        # 删除从 idx 往回找的整行
        line_start = content.rfind("\n", 0, idx) + 1
        line_end = content.find("\n", idx)
        if line_end == -1:
            line_end = len(content)
        old_except = content[line_start:line_end+1]
        content = content.replace(old_except, "")
    changes.append("RSS_fix")
else:
    changes.append("RSS_FAIL")
    # 输出诊断
    idx = content.find("兜底")
    print("RSS实际内容开头repr:", repr(content[idx:idx+300]))

ast.parse(content)
with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("修改:", " ".join(changes))
print("编译OK")