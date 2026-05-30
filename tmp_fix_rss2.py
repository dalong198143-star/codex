fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
content = open(fp).read()

# 始终先初始化 _rss_cache
old = '    feeds = get_enabled_feeds(force_reload=True)\n\n    # RSS预取(凌晨模式: 所有节点共享)\n    _rss_cache = []\n    if _night_mode and feeds:'
new = '    feeds = get_enabled_feeds(force_reload=True)\n\n    # RSS预取(凌晨模式: 所有节点共享)\n    _rss_cache = []\n    if _night_mode:'

assert old in content
content = content.replace(old, new, 1)

# 验证编译
import ast; ast.parse(content)
with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("OK")