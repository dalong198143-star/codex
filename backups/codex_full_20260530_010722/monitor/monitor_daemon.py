"""情报系统 v2 守护进程

每 2 小时自动触发一次扫描。
替代方案（Windows 计划任务不可用时）。
用法:
  python monitor_daemon.py
"""

import subprocess
import time
import sys
import os

SCAN_INTERVAL = 7200
SCAN_CMD = [sys.executable, "-m", "monitor.main", "scan"]
WORK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def run_scan():
    try:
        result = subprocess.run(
            SCAN_CMD, cwd=WORK_DIR,
            capture_output=True, text=True, timeout=300,
        )
        for line in result.stdout.splitlines():
            print(f"  [scan] {line}")
        if result.returncode != 0:
            print(f"  [scan] WARN: exit code {result.returncode}")
            for line in result.stderr.splitlines():
                print(f"  [scan] ERR: {line}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("  [scan] TIMEOUT (5min)")
        return False
    except Exception as e:
        print(f"  [scan] FAIL: {e}")
        return False


if __name__ == "__main__":
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
        time.sleep(SCAN_INTERVAL)

