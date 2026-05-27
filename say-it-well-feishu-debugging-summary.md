# say-it-well 飞书集成调试总结

> 调试日期：2026-05-26（今天）
> Skill 路径：`D:/hermes/skills/software-development/say-it-well/SKILL.md`
> Gateway 配置：`D:/hermes/config.yaml`
> 运行模型：deepseek-v4-pro（主）+ qwen3-max（备用）

---

## 一、核心问题与根因

### 1.1 平台适配鸿沟（最严重，耗时最长）

| 问题 | 根因 | 影响面 |
|------|------|--------|
| **飞书不支持 /skill 斜杠命令** | Feishu adapter 未实现 slash command handler | 无法手动加载 skill |
| **channel_prompt 和 auto_skill 不生效** | config.py 只对 Discord/Slack 做 skill binding 解析；feishu.py 的 MessageEvent 根本不传这两个字段 | Bot 不按 skill 方法论工作 |
| **clarify 工具卡死** | clarify 是同步交互工具，飞书消息通道是异步单向的，无实时输入机制 | Bot 永久阻塞 "Still working..." |
| **模型默认 fallback 到 qwen3-max** | DEEPSEEK_API_KEY 不在 .env 中，Gateway 的模型解析链在某些路径下不读 custom_providers 的 key | 用户配置的 deepseek-v4-pro 不生效 |

### 1.2 技能方法论缺陷

| 问题 | 根因 | 影响面 |
|------|------|--------|
| **不询问行业领域** | 11 个维度中没有"行业领域"维度，假设所有需求通用 | 餐饮/教育/金融/电商的不同规则未被考虑，prompt 质量差 |
| **用户拿到 prompt 后无下一步指引** | 输出模板只到 prompt 就结束，非技术用户不知道怎么办 | 用户流失，无效交付 |
| **行业追问机械死板** | 固定两轮 "什么行业" + "具体业务"，用户已说清仍追问 | 用户体验差，像机器人 |
| **用户答非所问时直接跳过** | 模型收到不相关回答时怕用户烦，选择跳过而不是重新措辞追问 | 信息漏采集，prompt 不准 |
| **输出到 prompt 即止** | 没有"上路指南"告诉用户下一步具体操作 | 非技术用户无法落地 |

### 1.3 对话质量细节问题

| 问题 | 根因 |
|------|------|
| **"另外先问一句"语气太弱** | 行业问句放在开场末尾，用户容易忽略 |
| **"这个维度就过了"太敷衍** | 用户感觉被应付，而不是被理解 |
| **误分类企业微信机器人为"后端服务"** | 上路指南分类粒度不够细 |
| **群聊和私聊的 chat_id 不同，只配了一个** | 配置时只抓了私聊 chat_id，群聊 skill 不加载 |

### 1.4 技术基建问题

| 问题 | 根因 |
|------|------|
| **IMA MCP 连接失败** | config.yaml 配的是 stdio transport（`command`/`args`），但 IMA 是 HTTP 服务 |
| **IMA 进程频繁掉线** | 启动命令不稳定，需手动重启 |
| **飞书不支持 session 模型切换** | 模型在 session 创建时锁定；配置变更后旧 session 仍用旧模型 |
| **上下文频繁压缩** | System prompt 过大（skill + memory + 工具 schema），默认压缩阈值 50% 触发太早 |

---

## 二、技术修复清单

### 2.1 源码修改（Gateway）

**文件：`gateway/config.py` ~861 行**
- 改动：`{DISCORD, SLACK}` → `{DISCORD, SLACK, FEISHU}`
- 效果：飞书平台进入 channel_skill_bindings 白名单

**文件：`gateway/platforms/feishu.py` ~3020 行**
- 改动：在 MessageEvent 创建前插入 `resolve_channel_prompt()` 和 `resolve_channel_skills()` 调用
- 效果：channel_prompt + auto_skill 正确传递到 Agent

### 2.2 配置修复

**`.env` 文件**（`D:/hermes/.env`）
- 新增 `DEEPSEEK_API_KEY=sk-...`
- Gateway 重启后新 session 使用配置模型

**`config.yaml` 修改**
```yaml
# IMA MCP: stdio → HTTP
mcp_servers:
  ima:
    url: http://127.0.0.1:8081/mcp
    # 移除 command/args

# 压缩阈值
compression.threshold: 0.8

# feishu channel_skill_bindings
feishu:
  channel_skill_bindings:
    - id: "oc_ef8176eb941646b3bfff30dc0cb62319"    # 私聊
      skills: ["say-it-well"]
    - id: "oc_28d8d090f9c8d425ee4799a2d0ea85f4"    # 群聊
      skills: ["say-it-well"]
```

### 2.3 工具路径统一
- 所有工具放到 D 盘，不在 C 盘
- IMA 手动启动脚本放在 `D:/tools/` 下

---

## 三、技能方法论改进

### 3.1 新增"行业领域"维度（SKILL.md 第 83-91 行）

**铁律**：复述确认后、进入多维度追问前，必须问行业。用"关键问题"开头：
> "先问一个关键问题——你们是什么行业的？餐饮、教育、游戏、电商、金融、还是别的？"

**智能判断**：用户回答后模型自行判断是否需要深挖：
- 够具体（如"电竞俱乐部的游戏陪玩业务"）→ 跳过第二轮
- 太笼统（如"餐饮"）→ 补问"具体做什么业务？堂食还是外卖？"

**判断标准**：用户说的能不能让你脑子里有画面。

### 3.2 新增"上路指南"（SKILL.md 第 188-215 行）

输出模板新增第六个板块，根据项目类型给出平台级操作指南：
- **网页/网站** → 推荐 Trae，粘贴 prompt，预览
- **微信小程序** → 微信开发者工具 + Trae → 上传审核
- **企业微信/飞书 Bot** → 明确区分"后端服务"和"企业微信"两类，给出 HTTPS + 服务器要求
- **后端/API/脚本** → Trae/Codex 写代码，自己找服务器
- **零基础用户** → Bolt.new 浏览器一站式方案（需翻墙）

### 3.3 触发条件精炼（SKILL.md 第 17-27 行）

新增触发规则，防止 say-it-well 对天气、闲聊、信息查询等非编程需求误触发：
- **触发**：用户说"做/建/写/开发/搞/弄/搭/整一个" + 名词是工具/网站/小程序/App/脚本/系统/软件
- **不触发**：闲聊、咨询、信息查询、文字创作

### 3.4 追问策略优化

- **答非所问不跳过**：用户回答跟问题不相关时，换方式再问一遍，不假装收到答案
- **闭合维度不说"这个维度就过了"**：改为"明白了，这一块清楚了"
- **行业问句强化**：从"另外先问一句"改为"先问一个关键问题"
- **双向兜底**：关键铁律同时写在 SKILL.md 主体 + channel_prompt（短小难忽略）

### 3.5 飞书平台特殊规则

在 SKILL.md 的"常见错误"中新增飞书专有规则：
> "飞书平台上不要用 clarify 工具。需要给用户选项时，直接文字列出来：1. ... 2. ... 3. ..."

---

## 四、经验教训

### 4.1 平台适配不是配置问题，是代码问题

一开始以为飞书不支持 auto_skill 是配置问题，反复尝试 config.yaml 格式。实际上问题在 Gateway 源码——config.py 的 whitelist 和 feishu.py 的 MessageEvent 构造都没考虑到飞书。**跨平台开发时，不要假设所有平台走同一套逻辑，源码确认每个平台的数据流路径。**

### 4.2 .env 和 config.yaml 是两套配置系统

DEEPSEEK_API_KEY 写在 config.yaml 的 custom_providers 中但飞书 session 在某些路径下不读取它。Gateway 的模型解析链：
1. 读 `model.default` / `model.provider`
2. 读 custom_providers 中的 api_key
3. 也读 `.env` 中的 `DEEPSEEK_API_KEY`

step 2 和 step 3 之间可能有优先级问题。**结论：两个地方都放一个 key 最稳妥。**

### 4.3 Session 模型在创建时锁定

改模型配置后旧 session 仍用旧模型。用户必须在飞书发 `/new`（走 approve 流程）新开 session。**这不是 bug，是设计——但文档里应该明确告知用户。**

### 4.4 clarify 工具不适合异步消息平台

CLI 等同步平台用 clarify 很好。但飞书、QQ 等异步消息通道不支持。**技能开发者需要显式标注哪些平台禁用 clarify。** 不能在 skill 逻辑里统一调 clarify + 期待在各平台都工作。

### 4.5 群聊和私聊是两个独立问题

飞书的群聊 `chat_id` 和私聊不同，skill binding 需要分别配。每次拉 Bot 进新群后都需要更新配置并重启 Gateway。**这不是一次性的工作——运维视角需要考虑。** 建议后续做成自动发现。

### 4.6 系统提示词太大导致压缩频繁

DeepSeek V4 Pro 的 128K 上下文看起来很大，但 say-it-well 的 SKILL.md 约 5000 字 + memory + 工具 schema + 历史消息，很快就会触碰到 50% 阈值。**压缩阈值从 0.5 调到 0.8 后问题缓解。** 40%（128K 的 ~50K）才触发压缩。

### 4.7 非技术用户的预期管理

say-it-well 的用户群体是完全不懂代码的人。调试中发现：
- 他们不知道"拿到 prompt 之后"怎么做 → 上路指南
- 他们说不清需求但能判断选项 → 给选项而非开放式问题
- 他们看到"关注公众号"（clarify 的界面）会迷茫 → 全文字列选项

**技能设计必须以用户的认知水平为基准，而非工具的功能边界。**

---

## 五、剩余缺口

### 5.1 运维侧

| 缺口 | 严重程度 | 说明 |
|------|---------|------|
| **IMA MCP 进程不稳定** | 中 | 需要 process manager 或自动重启机制 |
| **新群需要手动配置 skill binding** | 中 | 目前没有自动注册机制，每拉 Bot 进新群需手动更新 config.yaml |
| **启动步骤多且无统一脚本** | 低 | 需要一次启动多个服务（Gateway、IMA）尚无一键启动脚本 |
| **日志聚合不足** | 低 | 出错时需分别查 agent.log、gateway-stdio.log、gateway.log |

### 5.2 功能侧

| 缺口 | 严重程度 | 说明 |
|------|---------|------|
| **技能自检机制** | 高 | 没有机制验证当前 Bot 是否按预期加载了 skill、使用了正确模型 |
| **群聊@Bot 时自动激活 skill** | 中 | 当前触发靠 channel_skill_bindings，群聊中@Bot 可能不触发 auto_skill 逻辑 |
| **飞书斜杠命令支持** | 中 | 飞书适配器不支持 /skill 和 /new（/new 走 approve 流程勉强可用） |
| **多 skill 共存策略** | 低 | 当前只绑了 say-it-well 一个 skill。如果有多个 skill 绑定到同一个 chat_id，如何 triage？ |

### 5.3 方法论侧

| 缺口 | 严重程度 | 说明 |
|------|---------|------|
| **技能调试方法论文档化** | 低 | 本次调试的经验（从 config 到源码到 skill 逻辑的排查路径）没有标准化文档，下次类似问题可能重新踩坑 |
| **A/B 测试能力** | 低 | 技能迭代（如行业追问改为智能判断）缺乏量化的效果验证 |

---

*文档编写：2026-05-26 | 基于今日调试全程记录整理*
