import sys; sys.path.insert(0, r"D:\maozhua\Codex\codex\scripts")
from monitor.config import get_enabled_nodes, get_enabled_feeds
nodes = get_enabled_nodes(force_reload=True)
feeds = get_enabled_feeds(force_reload=True)
print(f"节点数: {len(nodes)}")
for n in nodes:
    print(f"  [{n['mail_level']:>8}] {n['name']}")
print(f"\nRSS 源数: {len(feeds)}")
for f in feeds:
    print(f"  {f['name']}")
