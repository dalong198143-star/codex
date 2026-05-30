import os, re

codebase = r"D:\maozhua\Codex\codex\scripts\monitor"

print("=== 1. 代码安全检查 ===")
for root, dirs, files in os.walk(codebase):
    for f in files:
        if not f.endswith(".py"): continue
        fp = os.path.join(root, f)
        with open(fp, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                s = line.strip()
                if "eval(" in s or "exec(" in s:
                    print(f"  FAIL: {f}:{i} eval/exec!")
                if "pickle.load" in s:
                    print(f"  WARN: {f}:{i} pickle.load")
                if "sys.path.insert" in s:
                    print(f"  WARN: {f}:{i} sys.path.insert")
                if "os.system(" in s or "subprocess.call" in s or "subprocess.Popen" in s:
                    if "monitor_daemon" not in s:
                        print(f"  WARN: {f}:{i} shell execution")

print("\n=== 2. 硬编码路径检查 ===")
for root, dirs, files in os.walk(codebase):
    for f in files:
        if not f.endswith(".py"): continue
        fp = os.path.join(root, f)
        with open(fp, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if re.search(r'["\'](?:C:|D:\\|/mnt/|/home/)', line):
                    print(f"  WARN: {f}:{i} 可能硬编码路径: {line.strip()[:80]}")

print("\n=== 3. TRUSTED_SOURCES 是否包括新增源 ===")
with open(os.path.join(codebase, "engine", "classifier.py")) as f:
    c = f.read()
sources = re.findall(r'"([^"]+)"', re.search(r"TRUSTED_SOURCES\s*=\s*\[(.*?)\]", c, re.DOTALL).group(1))
missing = []
for s in ["venturebeat.com", "crunchbase.com", "spectrum.ieee.org", "thenextweb.com", "cnbc.com"]:
    if not any(s in src for src in sources):
        missing.append(s)
if missing:
    for s in missing:
        print(f"  MISS: {s} 不在 TRUSTED_SOURCES")
else:
    print("  OK: 所有新增源都在信任名单")

print("\n=== 4. 检查 feeds.yaml 中 failed 的 3 个源 ===")
print("  Reuters: 可能 RSS URL 已变")
print("  DataCenterDynamics: 可能 feed 地址过期")
print("  SubmarineNetworks: 可能 feed 地址过期")

print("\n=== 5. 检查 main.py 对新节点的容错 ===")
with open(os.path.join(codebase, "main.py")) as f:
    lines = f.readlines()
timeout_lines = [i for i, l in enumerate(lines, 1) if "SKIP (timeout)" in l or "timeout" in l.lower()]
print(f"  超时处理行号: {timeout_lines[:5]}")

print("\n=== 6. 检查 monitor_daemon.py sys.path.insert ===")
with open(os.path.join(codebase, "monitor_daemon.py")) as f:
    for i, l in enumerate(f, 1):
        if "sys.path.insert" in l:
            print(f"  WARN: monitor_daemon.py:{i} sys.path.insert(0, ...)")
