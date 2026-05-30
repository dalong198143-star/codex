import os, re

fp = r"D:\maozhua\Codex\codex\scripts\monitor\config\feeds.yaml"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# 替换挂掉的源
replacements = [
    (r"https://www\.reutersagency\.com/feed/", "https://www.reuters.com/tools/rss"),
    (r"https://www\.datacenterdynamics\.com/feed/", "https://www.datacenterdynamics.com/en/feed/"),
    (r"https://www\.submarinenetworks\.com/feed", "https://www.capacitymedia.com/rss"),
]

for old_url, new_url in replacements:
    if old_url in content:
        content = content.replace(old_url, new_url)
        print(f"  REPLACE: {old_url[:40]}... -> {new_url}")
    else:
        print(f"  SKIP: {old_url[:40]}... 未找到")

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("feeds.yaml 更新完成")
