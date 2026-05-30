import sys; sys.path.insert(0, r"D:\maozhua\Codex\codex\scripts")
from monitor.config import get_enabled_feeds

feeds = get_enabled_feeds(force_reload=True)
print("=== 最终 RSS 源列表 (16个) ===")
for f in feeds:
    flag = "ON" if f.get("enabled", True) else "OFF"
    print(f"  [{flag}] {f['name']:30s}  {f['url'][:60]}")

print(f"\n=== 配置验证 ===")
from monitor.config import validate_config
errs = validate_config()
if errs:
    for e in errs: print(f"  FAIL: {e}")
else:
    print("  OK: 无配置错误")
