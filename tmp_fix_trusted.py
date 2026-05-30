with open(r"D:\maozhua\Codex\codex\scripts\monitor\engine\classifier.py", "r", encoding="utf-8") as f:
    content = f.read()

# 在 wired.com 后面加上新源
old_sources = '"wired.com", "nature.com", "science.org",'
new_sources = '"wired.com", "venturebeat.com", "crunchbase.com", "spectrum.ieee.org", "thenextweb.com", "nature.com", "science.org",'

if old_sources in content:
    content = content.replace(old_sources, new_sources)
    print("TRUSTED_SOURCES 更新成功")
else:
    print("未匹配到原 TRUSTED_SOURCES 位置")

with open(r"D:\maozhua\Codex\codex\scripts\monitor\engine\classifier.py", "w", encoding="utf-8") as f:
    f.write(content)
