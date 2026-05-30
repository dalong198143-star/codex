import sqlite3
conn = sqlite3.connect(r"D:\maozhua\Codex\data\monitor\monitor.db")
cur = conn.cursor()
cur.execute("SELECT ts, node, n, new FROM log WHERE ts < '2026-05-29T08:02' ORDER BY ts")
rows = cur.fetchall()
print(f"全天首次扫描: {len(rows)} 条记录")
if rows:
    from datetime import datetime
    t1 = datetime.fromisoformat(rows[0][0])
    t2 = datetime.fromisoformat(rows[-1][0])
    print(f"  首条: {rows[0][0]}  末条: {rows[-1][0]}")
    print(f"  耗时: {(t2-t1).seconds} 秒")