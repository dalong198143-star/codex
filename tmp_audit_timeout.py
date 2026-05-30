# 审计: SCAN_TIMEOUT 是否对新节点不足
# 老方案: timeout=180s，15个节点轮询，如果每个 Bing 搜索要 20-30s，15个 = 450s 不够
# 问题: 后几个节点总是 timeout

import re
with open(r"D:\maozhua\Codex\codex\scripts\monitor\main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 找到 SCAN_TIMEOUT 定义和扫描循环
timeout_line = re.search(r"total_timeout.*=.*int\(.*SCAN_TIMEOUT.*\"(\d+)\"\)", content)
if timeout_line:
    print(f"当前 SCAN_TIMEOUT: {timeout_line.group(1)}s")

# 检查每个采集器 timeout
for col in ["bing.py", "google_news.py"]:
    with open(f"D:\maozhua\Codex\codex\scripts\monitor\collector\{col}", "r") as f:
        c = f.read()
    tos = re.findall(r"timeout\s*[:=]\s*(\d+)", c)
    print(f"  {col}: timeout 配置 = {tos}s")

# scan() 中节点遍历逻辑
print("\n=== scan() 节点遍历逻辑 ===")
for_match = re.search(r"for node in nodes_batch.*?time\.monotonic\(\) > deadline", content, re.DOTALL)
if for_match:
    print("  有 deadline 超时检测，超时后 SKIP 剩余节点")
else:
    print("  WARN: 未找到 deadline 超时检测")
