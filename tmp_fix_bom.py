import os

for fname in ["utils.py", "collector/__init__.py"]:
    fp = os.path.join(r"D:\maozhua\Codex\codex\scripts\monitor", fname)
    with open(fp, "rb") as f:
        raw = f.read()
    if raw[:3] == b"\xef\xbb\xbf":
        raw_clean = raw[3:]
        with open(fp, "wb") as f:
            f.write(raw_clean)
        print(f"FIX: {fname} BOM removed ({len(raw)} -> {len(raw_clean)} bytes)")
    else:
        print(f"OK: {fname} 无BOM")

# 验证
import ast
for fname in ["utils.py", "collector/__init__.py"]:
    fp = os.path.join(r"D:\maozhua\Codex\codex\scripts\monitor", fname)
    with open(fp, "r", encoding="utf-8") as f:
        ast.parse(f.read())
    print(f"  OK: {fname} 编译通过")
