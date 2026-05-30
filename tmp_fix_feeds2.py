import re

fp = r"D:\maozhua\Codex\codex\scripts\monitor\config\feeds.yaml"
with open(fp, "r", encoding="utf-8") as f:
    content = f.read()

# 直接替换整个条目
old_reuters = '''  - name: "Reuters"
    url: "https://www.reutersagency.com/feed/"
    tags: [finance, global]
    enabled: true'''

new_reuters = '''  - name: "Reuters"
    url: "https://www.reuters.com/tools/rss"
    tags: [finance, global]
    enabled: true'''

old_dcd = '''  - name: "DataCenterDynamics"
    url: "https://www.datacenterdynamics.com/feed/"
    tags: [dc, infra]
    enabled: true'''

new_dcd = '''  - name: "DataCenterDynamics"
    url: "https://www.datacenterdynamics.com/en/feed/"
    tags: [dc, infra]
    enabled: true'''

old_subnet = '''  - name: "SubmarineNetworks"
    url: "https://www.submarinenetworks.com/feed"
    tags: [cable, infra]
    enabled: true'''

new_subnet = '''  - name: "Capacity Media"
    url: "https://www.capacitymedia.com/rss"
    tags: [cable, infra]
    enabled: true'''

changes = 0
for old, new in [(old_reuters, new_reuters), (old_dcd, new_dcd), (old_subnet, new_subnet)]:
    if old in content:
        content = content.replace(old, new)
        changes += 1
        print(f"OK: 替换成功")
    else:
        print(f"FAIL: 未匹配到源")

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print(f"feeds.yaml 更新完成 ({changes}/3)")
