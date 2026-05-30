fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
content = open(fp).read()

# 把 RSS 预取移到 feeds 赋值之后
old_pos = '    feeds = get_enabled_feeds(force_reload=True)\n\n    # 初始化'
new_pos = '    feeds = get_enabled_feeds(force_reload=True)\n\n    # RSS预取(凌晨模式: 所有节点共享)\n    _rss_cache = []\n    if _night_mode and feeds:\n        try:\n            from monitor.collector.rss import search_feeds as _sf\n            _rss_cache = _sf(feeds)\n            print(f"  [RSS] 预取 {len(_rss_cache)} 条")\n        except Exception as _e:\n            print(f"  [RSS] 预取失败: {_e}")\n\n    # 初始化'

# 删除原来在 print(=) 后的预取代码
old_header_rss = '\n    _rss_cache = []\n    if _night_mode:\n        try:\n            from monitor.collector.rss import search_feeds as _sf\n            _rss_cache = _sf(feeds)\n            print(f"  [RSS] 预取 {len(_rss_cache)} 条")\n        except Exception as _e:\n            print(f"  [RSS] 预取失败: {_e}")'

content = content.replace(old_header_rss, "")
content = content.replace(old_pos, new_pos, 1)

import ast; ast.parse(content)
with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("RSS预取移到feeds赋值后 OK")
print("编译OK")