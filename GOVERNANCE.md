# 多Agent治理规则

> 五Agent体系首次实战测试后，局外人评估揭示四条命门。以下规则为代码级修复的规则层配套。
> 订立日期：2026-05-30

## 一、修复分派规则（打破爱马仕单点瓶颈）

1. **域内自修原则**：诊断Agent在自身能力域内发现问题后，**必须尝试自修**，不得无条件升级给爱马仕。
   参见 `src/agent_governance.py` → `SKILL_MATRIX` + `RepairContract`

2. **升级门禁**：仅在以下情况升级到总指挥：
   - 自修尝试后失败
   - 问题标注为 CRITICAL
   - 问题跨越多个能力域
   - 修改涉及启动脚本/系统配置（安全边界）

3. **修复合约追踪**：每次修复必须记录 `RepairContract`，含自修尝试/成功/升级链路。

## 二、信用评分规则（监理误报自校准）

1. **报告即承诺**：Agent 每次提交发现（issue/bug/finding），自动记入信用系统。
   信用分初始 1.0（无罪推定），最大惩罚为单次误报扣 15%。

2. **验证闭环**：每个发现必须被另一个Agent独立验证（交叉验证），验证结果写入 `report_verdicts` 表。

3. **信用驱动的报告排序**：多Agent报告合并时按信用权重排序。
   信用 < 0.3 的Agent报告自动降级为"仅供参考"，不下发给执行者。

4. **监理自身的信用也需被评估**：监理（overseer）的每次评估也是一份"报告"。
   监理说49条实际5条 → 监理自己信用被扣到0.3以下 → 其后续评估自动降级。

## 三、幽灵事件强制RCA（自愈即升级）

1. **任何异常自行消失 → 必须记录幽灵事件**，冻结24小时观察窗口。

2. **自动升级时间线**：
   - 24h 未完成 RCA → 升级为 ESCALATED
   - 72h 未完成 RCA → 升级为 CRITICAL
   - 168h（7天）未完成 RCA → 升级为 INCIDENT（中断当前任务，强制处理）

3. **RCA 模板**：每个幽灵事件必须回答：
   - 什么异常？何时出现？何时消失？
   - 可能根因（至少3个假设，逐个排除）
   - 是否有数据残留/污染？
   - 如何复现？无法复现的原因？

## 四、效率基线规则（每次任务必须度量）

1. **任务启动时**：记录 `baseline_human_minutes`（单人预估耗时）和 `agent_count`。

2. **任务完成时**：自动生成效率报告（`EfficiencyMeter.get_efficiency_report`），
   含：Agent总耗时、token总量、发现数、修复数、误报数、效率比。

3. **效率阈值**：
   - ratio ≥ 2.0 → 多Agent效率显著高于单人
   - 1.0 ≤ ratio < 2.0 → 持平，需审视是否大材小用
   - ratio < 1.0 → 血亏，必须复盘（是任务不适合多Agent？还是分工错了？）

4. **效率报告公开**：每次任务完成后，效率报告追加到 `.agent-memory/efficiency-reports.md`

## 五、治理工具命令

```powershell
# 信用评分报告
python D:/maozhua/Codex/src/agent_governance.py credibility

# 幽灵事件清单 + 自动升级检查
python D:/maozhua/Codex/src/agent_governance.py ghosts
python D:/maozhua/Codex/src/agent_governance.py ghosts-check

# 效率报告
python D:/maozhua/Codex/src/agent_governance.py efficiency <session_id>
python D:/maozhua/Codex/src/agent_governance.py sessions
```
