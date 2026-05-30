import sys; sys.path.insert(0, r"D:\maozhua\Codex\codex\scripts")
from monitor.collector.rss import _fetch_feed, parse_feed

tests = [
    ("Google News Business", "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB"),
    ("Google News DC", "https://news.google.com/rss/search?q=data+center&hl=en-US&gl=US&ceid=US:en"),
]
for name, url in tests:
    raw = _fetch_feed(url)
    if raw:
        items = parse_feed(url)
        print(f"  OK: {name:20s} ({len(raw):6d} bytes, {len(items)} items)")
    else:
        print(f"  FAIL: {name}")
