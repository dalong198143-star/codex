"""
Agent Governance Module — 五Agent体系的运行治理

四条命门的代码级修复：
  1. 技能矩阵 + 修复分派  → 打破爱马仕单点瓶颈
  2. 信用评分 + 误报税    → 监理误报自校准
  3. 幽灵事件追踪         → 自愈不是解除，是升级
  4. 时间度量引擎         → 每次行动的效率基线

用法：
  from src.agent_governance import (
      AgentRegistry, CredibilityEngine, GhostTracker, EfficiencyMeter
  )

设计原则：
  - 不引入新依赖，纯 Python 标准库
  - SQLite 为持久化后端（与现有 monitor 体系一致）
  - 所有评分可被外部工具读取（CLI / API）
"""

import json
import os
import sqlite3
import time
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

# ── 数据目录 ──────────────────────────────────────────────
GOVERNANCE_DIR = Path("D:/maozhua/Codex/data/governance")
GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = GOVERNANCE_DIR / "agent_governance.db"


# ================================================================
#  一、技能矩阵 + 修复分派 → 打破单点瓶颈
# ================================================================

class AgentRole(Enum):
    """Agent 角色枚举 — 每个 Agent 有诊断域和修复域"""
    COMMANDER = "commander"       # 总指挥：分派 + 仲裁
    DIAGNOSTICIAN = "diagnostician"  # 诊断师：发现 + 分类
    DEVILS_ADVOCATE = "devils_advocate"  # 唱反调：审计 + 驳斥
    EXECUTOR = "executor"         # 执行者：修复 + 部署
    OVERSEER = "overseer"         # 监理：验证 + 度量


# 技能矩阵：每个角色在自己的诊断域内 CAN_FIX
# 格式: {角色: {能力域: [可执行的操作]}}
SKILL_MATRIX: dict[str, dict[str, list[str]]] = {
    "commander": {
        "task-routing": ["dispatch", "reassign", "escalate"],
        "config-management": ["update_config", "reload_config", "validate_config"],
        "dependency-resolution": ["resolve_conflict", "merge_branches"],
    },
    "diagnostician": {
        "data-collection": ["fix_collector", "retry_failed_source", "add_fallback"],
        "classification": ["fix_pattern", "add_label", "adjust_threshold"],
        "rss-management": ["replace_dead_feed", "add_backup_feed", "validate_feed"],
    },
    "devils_advocate": {
        "audit-findings": ["fix_audit_gap", "add_check", "update_policy"],
        "security-review": ["patch_vulnerability", "harden_config"],
    },
    "executor": {
        "code-fix": ["edit_file", "run_test", "deploy"],
        "infrastructure": ["restart_service", "clear_cache", "rotate_logs"],
    },
    "overseer": {
        "metrics-collection": ["fix_metric_pipeline", "add_metric", "update_baseline"],
        "quality-gate": ["adjust_threshold", "update_criteria"],
    },
}


@dataclass
class RepairContract:
    """修复合约：诊断Agent可自修其域内问题，超越阈值才升级到爱马仕"""
    agent_id: str              # 谁诊断的
    domain: str                # 哪个域
    issue_id: str              # 问题ID
    severity: str              # CRITICAL / IMPORTANT / WATCH
    can_self_repair: bool = False  # 诊断者可否自修
    self_repair_attempted: bool = False
    self_repair_success: bool = False
    escalated_to_commander: bool = False
    escalation_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None

    # ── 自动判断：诊断者能否自修 ──
    def evaluate_capability(self, role: str) -> bool:
        """检查该角色在此域是否有修复能力"""
        role_caps = SKILL_MATRIX.get(role, {})
        return self.domain in role_caps

    def should_escalate(self) -> tuple[bool, str]:
        """决定是否需要升级到总指挥"""
        if self.can_self_repair and not self.self_repair_attempted:
            return False, "自修域内，无需升级"
        if self.self_repair_attempted and self.self_repair_success:
            return False, "自修成功，无需升级"
        if self.severity == "CRITICAL":
            return True, "CRITICAL 级别强制升级"
        if self.self_repair_attempted and not self.self_repair_success:
            return True, "自修失败，升级到总指挥"
        return False, ""


# ================================================================
#  二、信用评分 + 误报税 → 监理自校准
# ================================================================

@dataclass
class CredibilityScore:
    """Agent 信用评分 — 喊错了负责，喊对了加分"""
    agent_id: str
    role: str

    # 核心指标
    total_reports: int = 0           # 报告总数
    confirmed_true: int = 0          # 确认为真的
    confirmed_false: int = 0         # 确认为假（误报）
    unverified: int = 0              # 待验证

    # 派生指标
    precision: float = 1.0           # 精确率 = TP / (TP + FP)，初始1.0（无罪推定）
    credibility: float = 1.0         # 信用分 = precision × recency_decay
    false_positive_rate: float = 0.0 # 误报率
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # 误报惩罚参数
    FALSE_ALARM_TAX: float = 0.15    # 每次误报扣 15% 信用
    TRUE_POSITIVE_BONUS: float = 0.02  # 每次命中加 2% 信用（上限1.0）
    RECENCY_HALF_LIFE_DAYS: int = 7   # 7天半衰期：旧报告权重衰减

    def report_filed(self):
        """Agent 提交了一份报告"""
        self.total_reports += 1
        self.unverified += 1
        self._recalc()

    def report_confirmed(self, is_true: bool):
        """某份报告被核实（可由其他Agent或人工确认）"""
        if self.unverified > 0:
            self.unverified -= 1
        if is_true:
            self.confirmed_true += 1
            self.credibility = min(1.0, self.credibility + self.TRUE_POSITIVE_BONUS)
        else:
            self.confirmed_false += 1
            # 误报税：指数衰减
            self.credibility *= (1 - self.FALSE_ALARM_TAX)
        self._recalc()

    def _recalc(self):
        """重新计算派生指标"""
        total_verified = self.confirmed_true + self.confirmed_false
        if total_verified > 0:
            self.precision = self.confirmed_true / total_verified
            self.false_positive_rate = self.confirmed_false / total_verified
        else:
            self.precision = 1.0  # 无罪推定
            self.false_positive_rate = 0.0
        self.last_updated = datetime.now().isoformat()

    def get_weight(self) -> float:
        """返回该Agent报告的可信权重（用于排序/过滤）"""
        # 低于 0.3 信用的Agent报告自动降级
        return max(0.0, self.credibility)

    def get_status(self) -> str:
        """信用状态标签"""
        if self.credibility >= 0.8:
            return "trusted"       # 可信
        elif self.credibility >= 0.5:
            return "probation"     # 观察期
        elif self.credibility >= 0.3:
            return "distrusted"    # 不信任：报告降级处理
        else:
            return "muted"         # 静默：报告仅记录，不下发


class CredibilityEngine:
    """信用评分引擎 — 全局单例，管理所有Agent的信用"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._scores: dict[str, CredibilityScore] = {}
        self._init_db()
        self._load_all()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credibility_scores (
                    agent_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    total_reports INTEGER DEFAULT 0,
                    confirmed_true INTEGER DEFAULT 0,
                    confirmed_false INTEGER DEFAULT 0,
                    unverified INTEGER DEFAULT 0,
                    precision REAL DEFAULT 1.0,
                    credibility REAL DEFAULT 1.0,
                    false_positive_rate REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS report_verdicts (
                    report_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    is_true INTEGER,           -- NULL=未验证, 1=真, 0=假
                    verified_by TEXT,           -- 谁验证的
                    verified_at TEXT,
                    notes TEXT
                )
            """)
            conn.commit()

    def _load_all(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM credibility_scores").fetchall()
            for row in rows:
                score = CredibilityScore(
                    agent_id=row["agent_id"],
                    role=row["role"],
                    total_reports=row["total_reports"],
                    confirmed_true=row["confirmed_true"],
                    confirmed_false=row["confirmed_false"],
                    unverified=row["unverified"],
                    precision=row["precision"],
                    credibility=row["credibility"],
                    false_positive_rate=row["false_positive_rate"],
                    last_updated=row["last_updated"],
                )
                self._scores[row["agent_id"]] = score

    def get_or_create(self, agent_id: str, role: str = "unknown") -> CredibilityScore:
        if agent_id not in self._scores:
            self._scores[agent_id] = CredibilityScore(agent_id=agent_id, role=role)
            self._save(agent_id)
        return self._scores[agent_id]

    def _save(self, agent_id: str):
        score = self._scores[agent_id]
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO credibility_scores
                (agent_id, role, total_reports, confirmed_true, confirmed_false,
                 unverified, precision, credibility, false_positive_rate, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score.agent_id, score.role, score.total_reports,
                score.confirmed_true, score.confirmed_false, score.unverified,
                score.precision, score.credibility, score.false_positive_rate,
                score.last_updated,
            ))
            conn.commit()

    def file_report(self, agent_id: str, report_id: str, role: str = "unknown"):
        """Agent 提交报告 → 信用分数更新"""
        score = self.get_or_create(agent_id, role)
        score.report_filed()
        self._save(agent_id)
        # 记录报告待验证
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO report_verdicts (report_id, agent_id) VALUES (?, ?)",
                (report_id, agent_id),
            )
            conn.commit()

    def verify_report(self, report_id: str, is_true: bool, verified_by: str, notes: str = ""):
        """验证报告 → 更新Agent信用"""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT agent_id FROM report_verdicts WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            if not row:
                return
            agent_id = row[0]
            conn.execute(
                """UPDATE report_verdicts
                   SET is_true = ?, verified_by = ?, verified_at = ?, notes = ?
                   WHERE report_id = ?""",
                (1 if is_true else 0, verified_by, datetime.now().isoformat(), notes, report_id),
            )
            conn.commit()
        score = self.get_or_create(agent_id)
        score.report_confirmed(is_true)
        self._save(agent_id)

    def get_credibility_report(self) -> list[dict]:
        """获取所有Agent的信用报告（可被外部CLI/API读取）"""
        report = []
        for agent_id, score in self._scores.items():
            report.append({
                "agent_id": agent_id,
                "role": score.role,
                "credibility": round(score.credibility, 3),
                "precision": round(score.precision, 3),
                "status": score.get_status(),
                "total_reports": score.total_reports,
                "confirmed_true": score.confirmed_true,
                "confirmed_false": score.confirmed_false,
                "unverified": score.unverified,
            })
        return sorted(report, key=lambda x: x["credibility"], reverse=True)

    def get_weighted_findings(self, findings: list[dict], agent_id_key: str = "agent_id") -> list[dict]:
        """对一批发现按Agent信用加权排序 — 低信用Agent的发现自动降级"""
        weighted = []
        for f in findings:
            agent_id = f.get(agent_id_key, "unknown")
            score = self._scores.get(agent_id)
            weight = score.get_weight() if score else 0.5
            f["_credibility_weight"] = weight
            f["_credibility_status"] = score.get_status() if score else "unknown"
            weighted.append(f)
        # 按权重降序排列
        return sorted(weighted, key=lambda x: x["_credibility_weight"], reverse=True)


# ================================================================
#  三、幽灵事件追踪 → 自愈不是解除，是升级
# ================================================================

class GhostSeverity(Enum):
    """幽灵事件严重度 — 随时间自动升级"""
    OBSERVED = 1     # 刚发现自愈
    ESCALATED = 2    # 24h 未查根因
    CRITICAL = 3     # 72h 未查根因
    INCIDENT = 4     # 7天未查根因 → 必须中断当前任务处理


@dataclass
class GhostEvent:
    """幽灵事件：异常自行消失，但根因未明"""
    ghost_id: str
    description: str                # 什么异常
    observed_at: str                # 何时发现
    resolved_at: str                # 何时自愈（消失）
    domain: str                     # 哪个域：data / network / model / storage
    affected_agents: list[str]      # 哪些Agent受影响
    severity: str = "OBSERVED"
    rca_completed: bool = False     # 根因分析是否完成
    rca_finding: str = ""           # 根因
    rca_completed_at: Optional[str] = None
    escalated_at: Optional[str] = None
    escalation_count: int = 0
    notes: str = ""

    def time_since_resolved_hours(self) -> float:
        resolved = datetime.fromisoformat(self.resolved_at)
        return (datetime.now() - resolved).total_seconds() / 3600

    def auto_escalate(self) -> tuple[bool, str]:
        """根据时间自动升级严重度"""
        hours = self.time_since_resolved_hours()
        if self.rca_completed:
            return False, "RCA已完成，无需升级"

        if hours >= 168:  # 7天
            if self.severity != "INCIDENT":
                self.severity = "INCIDENT"
                self.escalation_count += 1
                self.escalated_at = datetime.now().isoformat()
                return True, f"幽灵事件 {self.ghost_id} 升级为 INCIDENT：{hours:.0f}h 未查根因，必须中断当前任务"
        elif hours >= 72:  # 3天
            if self.severity != "CRITICAL":
                self.severity = "CRITICAL"
                self.escalation_count += 1
                self.escalated_at = datetime.now().isoformat()
                return True, f"幽灵事件 {self.ghost_id} 升级为 CRITICAL：{hours:.0f}h 未查根因"
        elif hours >= 24:  # 1天
            if self.severity != "ESCALATED":
                self.severity = "ESCALATED"
                self.escalation_count += 1
                self.escalated_at = datetime.now().isoformat()
                return True, f"幽灵事件 {self.ghost_id} 升级为 ESCALATED：{hours:.0f}h 未查根因"
        return False, ""


class GhostTracker:
    """幽灵事件追踪器 — 任何异常自行消失都必须记录"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ghost_events (
                    ghost_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    resolved_at TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    affected_agents TEXT NOT NULL,  -- JSON array
                    severity TEXT DEFAULT 'OBSERVED',
                    rca_completed INTEGER DEFAULT 0,
                    rca_finding TEXT DEFAULT '',
                    rca_completed_at TEXT,
                    escalated_at TEXT,
                    escalation_count INTEGER DEFAULT 0,
                    notes TEXT DEFAULT ''
                )
            """)
            conn.commit()

    def log_ghost(self, description: str, domain: str,
                  affected_agents: list[str],
                  observed_at: Optional[str] = None,
                  resolved_at: Optional[str] = None) -> GhostEvent:
        """记录一个自愈的异常"""
        ghost_id = hashlib.sha256(
            f"{description}{domain}{time.time()}".encode()
        ).hexdigest()[:16]

        now = datetime.now().isoformat()
        event = GhostEvent(
            ghost_id=ghost_id,
            description=description,
            observed_at=observed_at or now,
            resolved_at=resolved_at or now,
            domain=domain,
            affected_agents=affected_agents,
        )

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO ghost_events
                (ghost_id, description, observed_at, resolved_at, domain,
                 affected_agents, severity, rca_completed, escalation_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                event.ghost_id, event.description, event.observed_at,
                event.resolved_at, event.domain,
                json.dumps(event.affected_agents), event.severity,
            ))
            conn.commit()
        return event

    def get_pending_ghosts(self) -> list[dict]:
        """获取所有未完成RCA的幽灵事件"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM ghost_events WHERE rca_completed = 0 ORDER BY observed_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def complete_rca(self, ghost_id: str, finding: str):
        """完成根因分析"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                UPDATE ghost_events
                SET rca_completed = 1, rca_finding = ?, rca_completed_at = ?
                WHERE ghost_id = ?
            """, (finding, datetime.now().isoformat(), ghost_id))
            conn.commit()

    def check_and_escalate(self) -> list[str]:
        """检查所有未完成RCA的幽灵事件，自动升级过期的"""
        alerts = []
        pending = self.get_pending_ghosts()
        for p in pending:
            event = GhostEvent(
                ghost_id=p["ghost_id"],
                description=p["description"],
                observed_at=p["observed_at"],
                resolved_at=p["resolved_at"],
                domain=p["domain"],
                affected_agents=json.loads(p["affected_agents"]),
                severity=p["severity"],
                rca_completed=bool(p["rca_completed"]),
                rca_finding=p["rca_finding"],
                rca_completed_at=p["rca_completed_at"],
                escalated_at=p["escalated_at"],
                escalation_count=p["escalation_count"],
                notes=p["notes"],
            )
            escalated, msg = event.auto_escalate()
            if escalated:
                alerts.append(msg)
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute("""
                        UPDATE ghost_events
                        SET severity = ?, escalated_at = ?, escalation_count = escalation_count + 1
                        WHERE ghost_id = ?
                    """, (event.severity, event.escalated_at, event.ghost_id))
                    conn.commit()
        return alerts

    def get_ghost_summary(self) -> dict:
        """幽灵事件概要"""
        pending = self.get_pending_ghosts()
        return {
            "total_ghosts": len(pending),
            "by_severity": {
                "OBSERVED": sum(1 for g in pending if g["severity"] == "OBSERVED"),
                "ESCALATED": sum(1 for g in pending if g["severity"] == "ESCALATED"),
                "CRITICAL": sum(1 for g in pending if g["severity"] == "CRITICAL"),
                "INCIDENT": sum(1 for g in pending if g["severity"] == "INCIDENT"),
            },
            "rca_pending": sum(1 for g in pending if not g["rca_completed"]),
        }


# ================================================================
#  四、效率度量引擎 → 每次行动都有时间基线
# ================================================================

@dataclass
class ActionLog:
    """Agent 行动日志 — 每次工具调用/决策的时间度量"""
    action_id: str
    agent_id: str
    action_type: str          # diagnose / fix / audit / report / verify
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    token_count: int = 0       # LLM token 消耗
    task_description: str = ""
    success: bool = False
    parent_task_id: Optional[str] = None  # 属于哪个上层任务

    def complete(self, token_count: int = 0, success: bool = False):
        self.completed_at = datetime.now().isoformat()
        start = datetime.fromisoformat(self.started_at)
        self.duration_seconds = (datetime.now() - start).total_seconds()
        self.token_count = token_count
        self.success = success


class EfficiencyMeter:
    """效率度量引擎 — 回答'多出来的时间买到了什么'"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_logs (
                    action_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL DEFAULT 0,
                    token_count INTEGER DEFAULT 0,
                    task_description TEXT DEFAULT '',
                    success INTEGER DEFAULT 0,
                    parent_task_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_sessions (
                    session_id TEXT PRIMARY KEY,
                    task_description TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    total_duration_seconds REAL DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    agent_count INTEGER DEFAULT 0,
                    issues_found INTEGER DEFAULT 0,
                    issues_fixed INTEGER DEFAULT 0,
                    false_positives INTEGER DEFAULT 0,
                    baseline_human_minutes INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def start_action(self, agent_id: str, action_type: str,
                     task_description: str = "",
                     parent_task_id: Optional[str] = None) -> ActionLog:
        """记录一次行动的启动"""
        action_id = f"{agent_id}_{int(time.time() * 1000)}"
        action = ActionLog(
            action_id=action_id,
            agent_id=agent_id,
            action_type=action_type,
            started_at=datetime.now().isoformat(),
            task_description=task_description,
            parent_task_id=parent_task_id,
        )
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO action_logs
                (action_id, agent_id, action_type, started_at, task_description, parent_task_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (action.action_id, action.agent_id, action.action_type,
                  action.started_at, action.task_description, action.parent_task_id))
            conn.commit()
        return action

    def complete_action(self, action_id: str, token_count: int = 0, success: bool = False):
        """记录行动完成"""
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT started_at FROM action_logs WHERE action_id = ?", (action_id,)
            ).fetchone()
            if row:
                start = datetime.fromisoformat(row[0])
                duration = (datetime.now() - start).total_seconds()
                conn.execute("""
                    UPDATE action_logs
                    SET completed_at = ?, duration_seconds = ?, token_count = ?, success = ?
                    WHERE action_id = ?
                """, (now, duration, token_count, 1 if success else 0, action_id))
                conn.commit()

    def start_session(self, session_id: str, task_description: str,
                      agent_count: int = 0, baseline_human_minutes: int = 0) -> str:
        """开始一个任务会话"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO task_sessions
                (session_id, task_description, started_at, agent_count, baseline_human_minutes)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, task_description, datetime.now().isoformat(),
                  agent_count, baseline_human_minutes))
            conn.commit()
        return session_id

    def complete_session(self, session_id: str, issues_found: int = 0,
                         issues_fixed: int = 0, false_positives: int = 0):
        """完成任务会话，自动生成效率报告"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 汇总所有属于此session的行动
            rows = conn.execute("""
                SELECT SUM(duration_seconds), SUM(token_count)
                FROM action_logs WHERE parent_task_id = ?
            """, (session_id,)).fetchone()

            total_duration = rows[0] or 0
            total_tokens = rows[1] or 0

            conn.execute("""
                UPDATE task_sessions
                SET completed_at = ?, total_duration_seconds = ?, total_tokens = ?,
                    issues_found = ?, issues_fixed = ?, false_positives = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), total_duration, total_tokens,
                  issues_found, issues_fixed, false_positives, session_id))
            conn.commit()

    def get_efficiency_report(self, session_id: str) -> dict:
        """生成效率报告"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            session = conn.execute(
                "SELECT * FROM task_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not session:
                return {"error": "session not found"}

            agent_actions = conn.execute("""
                SELECT agent_id, action_type, COUNT(*) as count,
                       SUM(duration_seconds) as total_time,
                       SUM(token_count) as total_tokens
                FROM action_logs WHERE parent_task_id = ?
                GROUP BY agent_id, action_type
            """, (session_id,)).fetchall()

            s = dict(session)
            total_agent_minutes = (s["total_duration_seconds"] or 0) / 60
            baseline = s["baseline_human_minutes"] or 30  # 默认30分钟

            efficiency_ratio = baseline / max(total_agent_minutes, 0.01)
            precision = 0.0
            if (s["issues_found"] or 0) > 0:
                precision = (s["issues_found"] - s["false_positives"]) / max(s["issues_found"], 1)

            return {
                "session_id": session_id,
                "task": s["task_description"],
                "agent_count": s["agent_count"],
                "duration_agent_minutes": round(total_agent_minutes, 1),
                "baseline_human_minutes": baseline,
                "efficiency_ratio": round(efficiency_ratio, 2),
                "interpretation": self._interpret(efficiency_ratio),
                "total_tokens": s["total_tokens"] or 0,
                "issues_found": s["issues_found"] or 0,
                "issues_fixed": s["issues_fixed"] or 0,
                "false_positives": s["false_positives"] or 0,
                "precision": round(precision, 3),
                "per_agent_breakdown": [
                    {
                        "agent_id": r["agent_id"],
                        "action_type": r["action_type"],
                        "actions": r["count"],
                        "total_seconds": round(r["total_time"] or 0, 1),
                        "total_tokens": r["total_tokens"] or 0,
                    }
                    for r in agent_actions
                ],
            }

    @staticmethod
    def _interpret(ratio: float) -> str:
        if ratio >= 2.0:
            return f"多Agent效率是单人的 {ratio:.1f}x → 值回票价"
        elif ratio >= 1.0:
            return f"多Agent效率 {ratio:.1f}x → 持平，但覆盖更全面"
        elif ratio >= 0.5:
            return f"多Agent效率 {ratio:.1f}x → 低于单人，需优化分工"
        else:
            return f"多Agent效率仅 {ratio:.1f}x → 血亏，必须重构"


# ================================================================
#  CLI 入口 — 供外部工具和Agent调用
# ================================================================

def cli_main():
    """CLI 工具入口，可从命令行查询所有治理数据"""
    import sys
    if len(sys.argv) < 2:
        print("用法: python agent_governance.py <command> [args]")
        print("命令:")
        print("  credibility              — 信用评分报告")
        print("  ghosts                   — 幽灵事件清单")
        print("  ghosts-check             — 检查并自动升级幽灵事件")
        print("  efficiency <session_id>  — 效率报告")
        print("  sessions                 — 所有任务会话列表")
        return

    cmd = sys.argv[1]

    if cmd == "credibility":
        engine = CredibilityEngine()
        report = engine.get_credibility_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))

    elif cmd == "ghosts":
        tracker = GhostTracker()
        pending = tracker.get_pending_ghosts()
        summary = tracker.get_ghost_summary()
        print(json.dumps({"summary": summary, "pending": pending}, ensure_ascii=False, indent=2))

    elif cmd == "ghosts-check":
        tracker = GhostTracker()
        alerts = tracker.check_and_escalate()
        if alerts:
            for a in alerts:
                print(f"[ALERT] {a}")
        else:
            print("[OK] 无待升级幽灵事件")

    elif cmd == "efficiency":
        if len(sys.argv) < 3:
            print("用法: python agent_governance.py efficiency <session_id>")
            return
        meter = EfficiencyMeter()
        report = meter.get_efficiency_report(sys.argv[2])
        print(json.dumps(report, ensure_ascii=False, indent=2))

    elif cmd == "sessions":
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT session_id, task_description, started_at, completed_at, "
                "total_duration_seconds, issues_found, issues_fixed, false_positives "
                "FROM task_sessions ORDER BY started_at DESC LIMIT 20"
            ).fetchall()
            sessions = [dict(r) for r in rows]
            print(json.dumps(sessions, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    cli_main()
