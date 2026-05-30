import ast

fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
content = open(fp).read()

# 把 _night_mode 和 _rss_cache 移到 feeds 赋值之后
old = (
    "    _night_mode = _now_c().hour < 8\n"
    "    _rss_cache = []  # RSS缓存(所有节点共享,凌晨预取)\n"
    "\n"
    "\n"
    "    # 初始化\n"
    "    init_db()\n"
    "    nodes = get_enabled_nodes(force_reload=True)\n"
    "    feeds = get_enabled_feeds(force_reload=True)"
)
new = (
    "    # 初始化\n"
    "    init_db()\n"
    "    nodes = get_enabled_nodes(force_reload=True)\n"
    "    feeds = get_enabled_feeds(force_reload=True)\n"
    "\n"
    "    # 凌晨模式+RSS预取\n"
    "    _night_mode = _now_c().hour < 8\n"
    "    _rss_cache = []\n"
    "    if feeds:\n"
    '        print(f"  [缓存] RSS预取中...")\n'
    "        try:\n"
    "            from monitor.collector.rss import search_feeds as _sf\n"
    "            _rss_cache = _sf(feeds)\n"
    '            print(f"  [RSS] 预取 {len(_rss_cache)} 条")\n'
    "        except Exception as _e:\n"
    '            print(f"  [RSS] 预取失败: {_e}")\n'
    "    if _night_mode:\n"
    '        print("  [模式] 凌晨模式: 跳过Bing/Google搜索, 仅RSS源")\n'
    "    else:\n"
    '        print("  [模式] 日间模式: 全链路采集")\n'
)

assert old in content, "段1不匹配"
content = content.replace(old, new, 1)

ast.parse(content)
with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("_rss_cache 填充逻辑已修复")
print("编译OK")