import sys; sys.path.insert(0, r"D:\maozhua\Codex\codex\scripts")
from monitor.config import get_enabled_nodes, get_enabled_feeds, validate_config

print("=== 1. 配置验证 ===")
errs = validate_config()
if errs:
    for e in errs: print(f"  FAIL: {e}")
else:
    print("  OK")

nodes = get_enabled_nodes(force_reload=True)
feeds = get_enabled_feeds(force_reload=True)
print(f"\n=== 2. 节点 ({len(nodes)}) ===")
names = [n["name"] for n in nodes]
for n in set([x for x in names if names.count(x) > 1]):
    print(f"  DUP: {n}")
print("  无重复" if len(set(names)) == len(names) else "")

print(f"\n=== 3. RSS 源 ({len(feeds)}) ===")
urls = [f["url"] for f in feeds]
for u in set([x for x in urls if urls.count(x) > 1]):
    print(f"  DUP: {u}")
print("  无重复" if len(set(urls)) == len(urls) else "")

print(f"\n=== 4. 检查 RSS URL 可访问性 ===")
import urllib.request, ssl
ctx = ssl.create_default_context()
handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(handler)
for f in feeds:
    url = f["url"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = opener.open(req, timeout=5, context=ctx)
        print(f"  OK: {f['name']} ({r.status})")
    except Exception as e:
        print(f"  FAIL: {f['name']} - {str(e)[:60]}")
