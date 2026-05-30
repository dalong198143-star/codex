fp = r"D:\maozhua\Codex\codex\scripts\monitor\config\feeds.yaml"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# 替换挂掉的源为更可靠的替代
old_reuters = '''  - name: "Reuters"
    url: "https://www.reuters.com/tools/rss"
    tags: [finance, global]
    enabled: true'''

new_reuters = '''  - name: "Google News - Business"
    url: "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB"
    tags: [finance, global]
    enabled: true'''

old_dcd = '''  - name: "DataCenterDynamics"
    url: "https://www.datacenterdynamics.com/en/feed/"
    tags: [dc, infra]
    enabled: true'''

new_dcd = '''  - name: "DCD Magazine (via Google News)"
    url: "https://news.google.com/rss/search?q=data+center&hl=en-US&gl=US&ceid=US:en"
    tags: [dc, infra]
    enabled: true'''

content = content.replace(old_reuters, new_reuters)
content = content.replace(old_dcd, new_dcd)

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("feeds.yaml 再次更新完成（Reuters->Google News Business, DCD->Google News搜索）")
