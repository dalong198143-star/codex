content = open("D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py").read()
idx = content.find("兜底")
snippet = content[idx:]
# 输出 snippet 的前 5 行来确认换行符
lines = snippet.splitlines(True)
print("前5行repr:")
for l in lines[:5]:
    print(repr(l))