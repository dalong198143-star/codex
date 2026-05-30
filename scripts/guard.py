"""PreToolUse safety guard — block dangerous commands before execution.

Called by Claude Code PreToolUse hook.
Reads CLAUDE_TOOL_NAME and CLAUDE_TOOL_INPUT from environment.
Exits 0 to allow, non-zero to block (stderr = reason shown to user).
"""
import os
import json
import re
import sys

TOOL_NAME = os.environ.get("CLAUDE_TOOL_NAME", "")
TOOL_INPUT = os.environ.get("CLAUDE_TOOL_INPUT", "")

# Only guard Bash / PowerShell / Write / Edit tools
if TOOL_NAME not in ("Bash", "PowerShell", "Write", "Edit"):
    sys.exit(0)

# Parse tool input
try:
    inp = json.loads(TOOL_INPUT) if TOOL_INPUT else {}
except json.JSONDecodeError:
    sys.exit(0)

command = inp.get("command", "") or inp.get("content", "") or ""

# ── Dangerous command patterns ──
DANGEROUS = [
    # Destructive filesystem
    (r"\brm\s+-rf\s+/", "rm -rf / 会摧毁系统"),
    (r"\brm\s+-rf\s+\/\*", "rm -rf /* 会删除根目录"),
    (r"\brm\s+-rf\s+~", "rm -rf ~ 会删除用户目录"),
    (r"\brm\s+-rf\s+\$HOME", "rm -rf \$HOME 会删除用户目录"),
    (r">\s*/dev/sd[a-z]", "重定向到块设备会损坏磁盘"),
    (r"\bdd\s+if=.*of=/dev/sd", "dd 写入块设备会损坏磁盘"),
    (r"\bmkfs\.", "mkfs 会格式化磁盘"),
    (r"\bchmod\s+777\s+/", "chmod 777 在根路径极危险"),

    # Git force push to main/master
    (r"git\s+push\s+.*--force.*\b(main|master)\b", "禁止 force push 到 main/master"),

    # Database destruction
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", "DROP TABLE/DATABASE 不可逆，请手动确认"),
    (r"\bDELETE\s+FROM\b(?![\s\S]*\bWHERE\b)", "DELETE FROM 缺少 WHERE 条件"),

    # Git internals
    (r"\.git/", "禁止直接操作 .git 目录"),
    (r"\bgit\s+config\b", "git config 不建议通过 AI 修改"),
]

for pattern, reason in DANGEROUS:
    if re.search(pattern, command, re.IGNORECASE):
        print(f"[GUARD] BLOCKED: {reason}", file=sys.stderr)
        print(f"[GUARD] Command: {command[:200]}", file=sys.stderr)
        sys.exit(1)

sys.exit(0)
