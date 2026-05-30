import os, ast

codebase = r"D:\maozhua\Codex\codex\scripts\monitor"
files_found = []

for root, dirs, files in os.walk(codebase):
    for f in sorted(files):
        if f.endswith(".py") and f != "__pycache__":
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, codebase)
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    ast.parse(fh.read())
                files_found.append(f"  OK: {rel}")
            except SyntaxError as e:
                files_found.append(f"  FAIL: {rel} - {e}")

print("=== 编译检查 ===")
for l in files_found:
    print(l)
