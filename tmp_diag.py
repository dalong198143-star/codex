import sqlite3, datetime
conn = sqlite3.connect(r"D:\maozhua\Codex\data\monitor\monitor.db")
cur = conn.cursor()

# 最后3条扫描记录
cur.execute("SELECT ts, node, n, new FROM log ORDER BY rowid DESC LIMIT 3")
print("=== 最后3条扫描记录 ===")
for r in cur.fetchall():
    print(f"  [{r[0]}] {r[1]} 采集{r[2]} 新增{r[3]}")

# 节流表结构
cur.execute("SELECT sql FROM sqlite_master WHERE name='throttle_cooldown'")
print(f"\nthrottle_cooldown: {cur.fetchone()[0]}")

# 冷却记录
cur.execute("SELECT * FROM throttle_cooldown")
rows = cur.fetchall()
print(f"\n冷却记录: {len(rows)} 条")
for r in rows:
    print(f"  {str(r[0])[:25]:25s} | {str(r[1])[:25]} | {r[2] if len(r)>2 else '?'}")

# 健康记录
cur.execute("SELECT ts, name, status, last_error FROM health ORDER BY ts DESC LIMIT 5")
print("\n=== 健康记录(最近5条) ===")
for r in cur.fetchall():
    err = (r[3] or "")[:40]
    print(f"  [{str(r[0])[:19]}] {r[1]}: {r[2]} | {err}")

# 心跳记录
cur.execute("SELECT ts, name, status FROM health WHERE name='heartbeat' ORDER BY ts DESC LIMIT 3")
print("\n=== 心跳记录 ===")
for r in cur.fetchall():
    print(f"  [{str(r[0])[:19]}] {r[1]}: {r[2]}")
