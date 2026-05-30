import shutil, ast
fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
shutil.copy2(fp + ".bak", fp)
print("已恢复备份")