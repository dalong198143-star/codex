fp = r"D:\maozhua\Codex\codex\scripts\monitor\monitor_daemon.py"
content = open(fp, "r", encoding="utf-8").read()

# 替换循环体，加入时域自适应
old_loop = """if __name__ == "__main__":
    os.chdir(WORK_DIR)
    sys.path.insert(0, WORK_DIR)
    t0 = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 5))
    print(f"[Daemon] Monitor daemon started (interval={SCAN_INTERVAL}s)")
    print(f"[Daemon] Work dir: {WORK_DIR}")
    print(f"[Daemon] Next scan: {t0}")
    print()
    time.sleep(5)
    while True:
        now = time.strftime("%Y-%m-%d %H:%M")
        print(f"[{now}] === Scan start ===")
        ok = run_scan()
        now2 = time.strftime("%Y-%m-%d %H:%M")
        print(f"[{now2}] === Scan {'OK' if ok else 'FAILED'} ===")
        print()
        next_t = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + SCAN_INTERVAL))
        print(f"[Daemon] Next scan: {next_t}")
        print()
        time.sleep(SCAN_INTERVAL)"""

new_loop = """if __name__ == "__main__":
    os.chdir(WORK_DIR)
    sys.path.insert(0, WORK_DIR)
    print(f"[Daemon] Monitor daemon started")
    print(f"[Daemon] Work dir: {WORK_DIR}")
    print()
    time.sleep(5)
    while True:
        # 时域自适应: 凌晨(0-8点)快扫, 白天(8-24点)全量
        _h = time.localtime().tm_hour
        if _h < 8:
            SCAN_TIMEOUT, SCAN_INTERVAL = 90, 7200
            _mode = "凌晨模式"
        else:
            SCAN_TIMEOUT, SCAN_INTERVAL = 450, 14400
            _mode = "日间模式"
        os.environ["SCAN_TIMEOUT"] = str(SCAN_TIMEOUT)

        now = time.strftime("%Y-%m-%d %H:%M")
        print(f"[{now}] === {_mode} 扫描开始 (timeout={SCAN_TIMEOUT}s, interval={SCAN_INTERVAL}s) ===")
        ok = run_scan()
        now2 = time.strftime("%Y-%m-%d %H:%M")
        print(f"[{now2}] === Scan {'OK' if ok else 'FAILED'} ===")
        print()
        next_t = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + SCAN_INTERVAL))
        print(f"[Daemon] Next scan: {next_t}")
        print()
        time.sleep(SCAN_INTERVAL)"""

assert old_loop in content, "找不到原循环体"
content = content.replace(old_loop, new_loop, 1)

# 验证编译
import ast
ast.parse(content)

with open(fp, "w", encoding="utf-8") as f:
    f.write(content)
print("monitor_daemon.py 已更新 ✅")
print("时域自适应: 凌晨2h/90s → 白天4h/450s")