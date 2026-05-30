import sys; sys.path.insert(0, r"D:\maozhua\Codex\codex\scripts")
from monitor.collector.rss import _fetch_feed, parse_feed

tests = [
    ("Reuters (new)", "https://www.reuters.com/tools/rss"),
    ("DataCenterDynamics (new)", "https://www.datacenterdynamics.com/en/feed/"),
    ("Capacity Media (new)", "https://www.capacitymedia.com/rss"),
]
for name, url in tests:
    raw = _fetch_feed(url)
    if raw:
        items = parse_feed(url)
        print(f"  OK: {name:25s} ({len(raw):6d} bytes, {len(items)} items)")
    else:
        print(f"  FAIL: {name}")
