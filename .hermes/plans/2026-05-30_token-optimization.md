# Token 优化方案 v2.0

> 目标：日常 token 消耗降低 40-50%
> 日期：2026-05-30
> 状态：📋 方案就绪
> 审计：v1.0 发现 11 个问题（4❌/5⚠️），v2.0 全部修复

---

## 完整消耗画像

```
每轮注入（每次对话都烧）：
  AGENTS.md             6,017 字节  ← 138行，53%是治理规则
  user-profile.md       3,901 字节  ← 未审计，可能有冗余
  Memory                2,111 字    ← 19条，95%满
  技能清单              不定        ← 80+技能名+描述

场景额外加载（按需但往往不必要）：
  local-kb skill        ~3KB        ← 简单搜KB也全量加载
  ima-knowledge-base    ~5KB        ← cron备份每次加载

对话额外消耗（今天的大头）：
  Council L3 审计       5次LLM调用  ← 监理+扣带思+克劳德+局外人+爱马仕
  cron KB备份           加载双技能  ← local-kb + ima-knowledge-base
```

---

## Phase 1：AGENTS.md 瘦身（两刀）

### 第一刀：拆分治理规则

删除 AGENTS.md 第 62-134 行（多Agent治理规则，73行），搬入新文件 `D:/maozhua/Codex/GOVERNANCE.md`。

原位置替换为：
```
## 多Agent治理规则
详见 D:/maozhua/Codex/GOVERNANCE.md
⚠️ 执行 Council/审计/监理任务前，必须先 read_file 该文件。
```

节省 ~3KB/轮。

### 第二刀：删除 KB 命令冗余

删除 AGENTS.md 第 7-23 行（本地知识库命令/topic/路由），替换为：
```
## 本地知识库
遵循 local-kb skill。先搜再做，做完必写。
```

local-kb skill 里已经定义了完整命令、8个topic、三层路由，AGENTS.md 里不需要重复。

节省 ~500 字节/轮。

### AGENTS.md 最终结构

```
# 项目概述（6行）
## 目录结构（12行）
## 启动方式（4行）
## 关键配置（9行）
## 编码规范（3行）
## 多Agent治理 → GOVERNANCE.md（3行）
## 全局约束（2行）
```

瘦身后约 39 行，比原来的 138 行减少 72%。

### 验证

`wc -c D:/maozhua/Codex/AGENTS.md` — 瘦身前 6,017 字节，瘦身后应 < 2,500 字节。

---

## Phase 2：模型分级（可执行版）

### 问题

Hermes 不动态切换模型，模型在 config.yaml 里固定。不能指望"爱马仕自己判断"。

### 方案：改默认模型 + 手动升级

把 Hermes config.yaml 的默认模型从 `deepseek-v4-pro` 改为 `deepseek-v4-flash`。

```
大多数对话用 flash（便宜，够用）
需要深度推理时 → 用户手动 /model deepseek-v4-pro
或者 → 爱马仕在回答开头判断"这轮需要pro"，提示用户切换
```

### 判断清单（写进 memory，我每轮自问）

- 涉及代码审查/审计？ → 需要 pro
- 涉及架构设计/技术选型？ → 需要 pro
- 涉及复杂排错（3步以上）？ → 需要 pro
- 其他（闲聊/配置/查询/文件操作）→ flash 够用

### flash 可用性

已确认：`litellm_config.yaml` 中 deepseek-v4-flash 配置完整，降级链 → xiaomi-mimo-v2.5。代理 :1234 能正常路由。

### 验证

改完默认模型后，发一条简单消息（"查状态"），确认走 flash 且响应正常。

---

## Phase 3：Memory 瘦身 + user-profile.md 审计

### 先审计，再动手（不凭印象）

第一步：列出 memory 全部 19 条 + user-profile.md 全文，逐条判断保留/删除/合并。

第二步：执行删除/合并。

第三步：验证 memory 使用率 < 85%。

### 已知候选

SkillHub 企查查那条（用的时候现查）、技能vs方法区分（已在 skill 里定义）。

### user-profile.md

3,901 字节，每轮注入。需读全文审计过时内容。

---

## Phase 4：Council 审计降本

### 问题

L3 审计 = 五人链 = 5 次 LLM 调用，每次带完整上下文。今天监理+局外人各跑一次就烧了不少。

### 方案：监理分层

```
第一层（flash，日常）：
  监理用 deepseek-v4-flash 快速扫描：
  - 文件存在性（ls / find）
  - 数字核实（目录数、文件行数 wc -l）
  - 配置一致性（diff）
  只输出差异，不重复原文。

第二层（pro，发现疑似问题后）：
  监理发现数字不对、逻辑矛盾 → 升级 pro 深度分析
```

### 修改位置

`D:/hermes-tools/agents/监理.txt` — 系统提示词加一条：
"先用 flash 做事实核查（文件存在/数字/配置），发现不一致再升级 pro 做深度分析。"

### Council 报告模板精简

监理/局外人回复模板：只输出差异和修正建议，不重复原始声明。省掉"克劳德声称：xxx"这种原文复述。

---

## Phase 5：cron 技能瘦身

### 问题

KB 备份 cron（每天 02:00）每次都加载 local-kb + ima-knowledge-base 两个技能，合计 ~8KB。

### 方案

备份脚本 `backup_to_ima.py` 本身就是独立 Python 脚本，cron 用 `no_agent=true` 跑，不需要加载技能。

修改 cron job：去掉 skills 参数，只留 script + no_agent=true。

---

## Phase 6：kb-quick 精简技能（可选）

新建 `kb-quick` skill，只含 query_kb.py 三条命令 + topic 列表。description 写死"仅查询，不写入"。

触发规则：用户说"搜KB"/"查一下" → 加载 kb-quick。说"存"/"写入"/"备份" → 加载完整 local-kb。

---

## 执行顺序

```
Phase 1: AGENTS.md 两刀     ← 最优先，收益最大，5分钟搞定
Phase 2: 默认模型改 flash   ← 第二优先，改一行配置
Phase 3: Memory + profile审计 ← 需要先读再判
Phase 4: Council 监理分层   ← 改监理.txt 系统提示词
Phase 5: cron 去技能        ← 改 cron job 配置
Phase 6: kb-quick           ← 可选，不急
```

---

## 结论

```
做这五件事，日常 token 降 40-50%：

  1. AGENTS.md 从 138 行砍到 39 行
     → 治理规则拆到 GOVERNANCE.md（审计时按需读）
     → KB 命令删掉（local-kb skill 里已有）
     验证：wc -c 对比 6017 → <2500

  2. 默认模型改 flash，pro 手动切
     → Hermes config.yaml 改 model 字段
     → memory 记判断清单，我每轮自问是否需 pro
     验证：发一条简单消息确认走 flash

  3. Memory + user-profile.md 逐条审计后删冗余
     验证：memory 使用率 < 85%

  4. 监理日常扫描用 flash，发现疑似问题才升 pro
     → 改 监理.txt 系统提示词
     验证：下次审计看监理用了什么模型

  5. cron 备份去掉技能加载
     → 改 cron job 的 skills 参数为空
     验证：明天 02:00 看 cron 日志
```
