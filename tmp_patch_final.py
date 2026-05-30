import ast

fp = r"D:\maozhua\Codex\codex\scripts\monitor\main.py"
with open(fp, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
hdr = bng = ggl = rss = False

i = 0
while i < len(lines):
    line = lines[i]
    s = line.strip()

    if not hdr and "print("=" * 50)" in s:
        new_lines.append(line)
        new_lines.append("\n")
        new_lines.append("    # 凌晨模式(0-8点): 跳过Bing/Google搜索(凌晨国外源限速严重)\n")
        new_lines.append("    _current_hour = _now_c().hour\n")
        new_lines.append("    night_mode = _current_hour < 8\n")
        new_lines.append("    if night_mode:\n")
        new_lines.append("        _t = _now_str_c()[:5]\n")
        new_lines.append('        print(f"[{_t}] 凌晨模式: 跳过Bing/Goog" + "le搜索, 仅RSS源")\n')
        new_lines.append("    else:\n")
        new_lines.append("        _t = _now_str_c()[:5]\n")
        new_lines.append('        print(f"[{_t}] 日间模式: 全链路采集")\n')
        new_lines.append("\n")
        new_lines.append("    # RSS预取: 所有节点共享\n")
        new_lines.append("    _prefetched_rss = []\n")
        new_lines.append("    if feeds:\n")
        new_lines.append("        try:\n")
        new_lines.append("            from monitor.collector.rss import search_feeds as _sf\n")
        new_lines.append("            _prefetched_rss = _sf(feeds)\n")
        new_lines.append('            print(f"  [RSS] 预取 {len(_prefetched_rss)} 条候选条目")\n')
        new_lines.append("        except Exception as _e:\n")
        new_lines.append('            print(f"  [RSS] 预取失败: {_e}")\n')
        new_lines.append("\n")
        hdr = True
        i += 1
        continue

    if not bng and s == "items = bing_search(kw)":
        ind = line[:len(line) - len(line.lstrip())]
        new_lines.append(f"{ind}if night_mode:\n")
        new_lines.append(f"{ind}    items = []\n")
        new_lines.append(f"{ind}else:\n")
        new_lines.append(f"{ind}    items = bing_search(kw)\n")
        bng = True
        i += 1
        continue

    if not ggl and s == "items = google_news_search(kw)":
        ind = line[:len(line) - len(line.lstrip())]
        new_lines.append(f"{ind}if night_mode:\n")
        new_lines.append(f"{ind}    items = []\n")
        new_lines.append(f"{ind}else:\n")
        new_lines.append(f"{ind}    items = google_news_search(kw)\n")
        ggl = True
        i += 1
        continue

    if not rss and "# 兜底: RSS feed" in s:
        ind = line[:len(line) - len(line.lstrip())]
        new_lines.append(f"{ind}# 兜底: RSS匹配(使用预取数据, 不重复请求)\n")
        new_lines.append(f"{ind}if not source_ok and _prefetched_rss:\n")
        new_lines.append(f"{ind}    for _rss_it in _prefetched_rss:\n")
        new_lines.append(f'{ind}        _rt = (_rss_it["t"] + " " + _rss_it["s"]).lower()\n')
        new_lines.append(f"{ind}        if any(_kw.lower() in _rt for _kw in keywords):\n")
        new_lines.append(f"{ind}            all_items.append(_rss_it)\n")
        new_lines.append(f'{ind}            print("    [" + str(node_name) + "] RSS match: " + _rss_it.get("t","")[:50])\n')
        new_lines.append(f"{ind}            source_ok = True\n")
        new_lines.append(f'{ind}            print("[RSS]", end=" ", flush=True)\n')
        rss = True
        while i < len(lines):
            if "for node in nodes:" in lines[i]:
                break
            i += 1
        continue

    new_lines.append(line)
    i += 1

with open(fp, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"HDR={hdr} BNG={bng} GGL={ggl} RSS={rss}")
ast.parse(open(fp).read())
print("编译OK")