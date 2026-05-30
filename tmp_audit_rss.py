import sys; sys.path.insert(0, r"D:\maozhua\Codex\codex\scripts")
from monitor.collector.rss import _fetch_feed, parse_feed

feeds = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("VentureBeat", "https://venturebeat.com/feed/"),
    ("Crunchbase News", "https://news.crunchbase.com/feed/"),
    ("CNBC Tech", "https://www.cnbc.com/id/10001147/device/rss/rss.html"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("IEEE Spectrum", "https://spectrum.ieee.org/feed/rss"),
    ("The Next Web", "https://thenextweb.com/feed"),
    ("Reuters", "https://www.reutersagency.com/feed/"),
    ("DataCenterDynamics", "https://www.datacenterdynamics.com/feed/"),
    ("LightReading", "https://www.lightreading.com/rss.xml"),
    ("SubmarineNetworks", "https://www.submarinenetworks.com/feed"),
]

print("=== RSS 可达性测试（用实际采集器）===")
ok = fail = 0
for name, url in feeds:
    raw = _fetch_feed(url)
    if raw:
        items = parse_feed(url)
        print(f"  OK: {name:25s} ({len(raw):6d} bytes, {len(items)} items)")
        ok += 1
    else:
        print(f"  FAIL: {name}")
        fail += 1
print(f"\nOK={ok} FAIL={fail}")
