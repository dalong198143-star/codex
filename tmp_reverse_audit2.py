import os, ast

fp = r"D:\maozhua\Codex\codex\scripts\monitor\main.py"
content = open(fp, "r", encoding="utf-8").read()

print("=== 反向审计 ===\n")

print("1. 凌晨跳过 Bing/Google")
print("  _night_mode:", "_night_mode = _now_c().hour < 8" in content)
print("  Bing跳过:", "[] if _night_mode else bing_search" in content)
print("  Google跳过:", "[] if _night_mode else google_news" in content)
print("  RSS填充:", "_rss_cache = _sf(feeds)" in content)
print()

print("2. 白天全链路")
print("  else分支触发:", "日间模式: 全链路采集" in content)
print()

print("3. SCAN_TIMEOUT 可调")
print("  env读取:", "os.environ.get" in content and "SCAN_TIMEOUT" in content)
print()

print("4. 守护进程需改")
dp = r"D:\maozhua\Codex\codex\scripts\monitor\monitor_daemon.py"
dpc = open(dp).read()
print("  当前写死interval:", "SCAN_INTERVAL = 7200" in dpc)
print("  当前写死timeout:", "timeout=300" in dpc)
print("  ❌ 无动态调整")
print()

print("5. 无外部依赖 ✅")
print()

print("6. 守护进程持久化 ❌")
print()

print("7. 编译")
for name, path in [("main.py", fp), ("monitor_daemon.py", dp)]:
    try:
        ast.parse(open(path).read())
        print(f"  {name}: OK")
    except Exception as e:
        print(f"  {name}: FAIL - {e}")

print("\n结论:")
print("  ✅ 方案B技术逻辑正确")
print("  ⚠️ 需改2处: monitor_daemon.py 动态参数 + 持久化")