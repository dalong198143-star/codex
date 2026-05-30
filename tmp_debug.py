content = open("D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py").read()
idx = content.find('print("=" * 50)')
print(content[idx:idx+500])