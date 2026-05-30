import ast

fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
content = open(fp).read()

# 直接在文件尾部搜索并修改
# 问题：_rss_cache 没有在凌晨模式之外初始化
# 方案：在 _night_mode 定义后立即加上 _rss_cache = []

# 找到 '_night_mode = _now_c().hour < 8' 这一行，在后面加初始化
old = "_night_mode = _now_c().hour < 8"
new = "_night_mode = _now_c().hour < 8\n    _rss_cache = []  # RSS缓存(所有节点共享,凌晨预取)"
if old in content:
    content = content.replace(old, new, 1)
    print("_rss_cache 初始化插入 OK")
else:
    # 可能内容已被修改过，再查
    print("_night_mode 找不到, 当前内容中 _rss_cache 出现:", content.count("_rss_cache"))
    print("_night_mode 出现:", content.count("_night_mode"))

ast.parse(content)
with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("编译OK")