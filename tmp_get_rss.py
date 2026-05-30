fp = "D:\\maozhua\\Codex\\codex\\scripts\\monitor\\main.py"
content = open(fp).read()
idx = content.find("兜底")
# 找到 RSS 块结束位置(下一个 for node 或 except)
end_idx = content.find("for node in", idx)
if end_idx == -1:
    end_idx = idx + 500
# 取实际 RSS 块
actual_rss = content[idx:end_idx]
# 只保留到 except 结尾的完整块
except_idx = actual_rss.find("RSS error")
if except_idx > 0:
    actual_rss = actual_rss[:except_idx + 50]  # 取到 except 结束
    # 找到最近的行尾
    actual_rss = actual_rss[:actual_rss.rfind("\n")+1]
else:
    actual_rss = actual_rss[:actual_rss.rfind("\n")+1]

# 输出精确字符串以便复制
print("=== ACTUAL RSS BLOCK ===")
print(repr(actual_rss))
print("=== END ===")
print(f"Length: {len(actual_rss)}")