import ast

fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
content = open(fp).read()

print("=== 1. _rss_cache 填充逻辑审计 ===")
# 查找所有 _rss_cache 引用
import re
for m in re.finditer(r"[^#\n]*_rss_cache[^#\n]*", content):
    print(f"  {m.group().strip()[:100]}")

print("\n=== 2. 凌晨模式代码 ===")
idx = content.find("night_mode")
if idx >= 0:
    print(content[idx:idx+200])

print("\n=== 3. 测试再跑 ===")
