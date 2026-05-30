fp = r"D:\maozhua\Codex\codex\scripts\monitor\monitor_daemon.py"
lines = open(fp, "r", encoding="utf-8").readlines()

# 找到 subprocess.run 的 timeout=300 改成 timeout=SCAN_TIMEOUT+60
new_lines = []
for line in lines:
    if "timeout=300" in line and "subprocess.run" in line:
        new_lines.append(line.replace("timeout=300", "timeout=SCAN_TIMEOUT+60"))
        print(f"  已改: {line.strip()} → timeout=SCAN_TIMEOUT+60")
    else:
        new_lines.append(line)

import ast
ast.parse("".join(new_lines))

with open(fp, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("✅ subprocess timeout 已改为动态")