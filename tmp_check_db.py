import sqlite3
conn = sqlite3.connect(r"D:\maozhua\Codex\data\monitor\monitor.db")
cur = conn.cursor()

# 各节点扫描统计
cur.execute("SELECT node, COUNT(*), SUM(n), SUM(new) FROM log GROUP BY node ORDER BY node")
print("=== 节点扫描统计 ===")
for r in cur.fetchall():
    print(f"  {str(r[0]):30s} | 扫描{r[1]}次 | 共采集{int(r[2]):3d}条 | 新增{int(r[3]):2d}条")

# 总扫描情况
cur.execute("SELECT MIN(ts), MAX(ts) FROM log")
r = cur.fetchone()
print(f"\n首末次扫描: {r[0]} ~ {r[1]}")
cur.execute("SELECT COUNT(*) FROM log")
print(f"总扫描记录: {cur.fetchone()[0]} 条")
cur.execute("SELECT SUM(n) FROM log")
print(f"总采集条目: {int(cur.fetchone()[0])} 条")
cur.execute("SELECT SUM(new) FROM log")
print(f"总新增条目: {int(cur.fetchone()[0])} 条")
cur.execute("SELECT COUNT(*) FROM seen")
print(f"去重后条目: {cur.fetchone()[0]} 条")
