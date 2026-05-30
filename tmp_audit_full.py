import sys, os, re, ast

codebase = r"D:\maozhua\Codex\codex\scripts\monitor"
issues = []

def check_file(path, label):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        ast.parse(content)
    except SyntaxError as e:
        issues.append(f"  FAIL: {label} 语法错误: {e}")
        return content
    issues.append(f"  OK: {label} ({len(content)} bytes, {len(content.splitlines())} lines)")
    return content

print("=== 1. 全部文件编译检查 ===")
for root, dirs, files in os.walk(codebase):
    for f in sorted(files):
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, codebase)
            check_file(fp, rel)

print("\n=== 2. 代码安全问题 ===")
for root, dirs, files in os.walk(codebase):
    for f in files:
        if not f.endswith(".py"): continue
        fp = os.path.join(root, f)
        with open(fp, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                line_s = line.strip()
                if "sys.path.insert" in line_s:
                    issues.append(f"  WARN: {f}:{i} sys.path.insert 反模式")
                if "eval(" in line_s or "exec(" in line_s:
                    issues.append(f"  FAIL: {f}:{i} eval/exec")

print("\n=== 3. TRUSTED_SOURCES 完整性 ===")
with open(os.path.join(codebase, "engine", "classifier.py")) as f:
    c = f.read()
m = re.search(r"TRUSTED_SOURCES\s*=\s*\[(.*?)\]", c, re.DOTALL)
if m:
    sources = re.findall(r'"([^"]+)"', m.group(1))
    print(f"  TRUSTED_SOURCES: {len(sources)} 个")
    for s in sorted(sources): print(f"    {s}")

print("\n=== 4. 数据流关键路径检查 ===")
# 检查 scan() 是否对新节点有特殊处理
with open(os.path.join(codebase, "main.py")) as f:
    mainc = f.read()
print(f"  main.py: {len(mainc.splitlines())} lines")

print("\n=== 5. 检查 nodes.yaml 新增节点关键词完整性 ===")
with open(os.path.join(codebase, "config", "nodes.yaml")) as f:
    yamlc = f.read()
# 找新节点
for seg in re.split(r"\n  - name:", yamlc):
    if "金融" in seg or "半导体" in seg or "AI 创业" in seg:
        kws = re.findall(r'"([^"]+)"', seg)
        print(f"  {seg.split(chr(10))[0].strip()}: {len(kws)} kw -> {kws}")
