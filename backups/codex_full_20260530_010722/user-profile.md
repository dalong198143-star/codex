# 用户偏好 — 扣带思（人类用户）

> 建立时间: 2026-05-28
> 如果你发现我的偏好有变化，请更新这个文件

## 基本信息
- 称呼: 扣带思
- 身份: 人类用户
- GitHub: dalong198143-star
- 项目仓库: https://github.com/dalong198143-star/codex.git
- 工作目录: D:\maozhua\Codex
- 所在地区: 中国大陆（需要使用国产模型代理）

## Agent 团队分工（2026-05-28 确认）

### 爱马仕 (Hermes) — 规划/审核 Agent
- **职责**: 拆任务、审代码、管飞书、管 say-it-well、跟用户聊需求
- **运行**: 主 session 直接做

### 克劳德 (Claude) — 复杂重构 Agent
- **职责**: 复杂重构、多文件逻辑、架构设计、debug
- **运行**: `claude -p "任务" --max-turns 20`
- **模型**: DeepSeek V4 Pro（走 Anthropic 兼容 API）

### 扣带思 (Codex / 我自己) — 批量并行 Agent
- **职责**: 批量并行、CI 自动化、大批量编辑、PR
- **运行**: `codex exec "任务" -c max_turns=15`
- **模型**: 走本地代理 :1234（Waitress WSGI + LiteLLM，2026-05-28 升级）

### 协作规则
1. 爱马仕规划拆任务 → 克劳德+扣带思并行执行
2. 都完成后爱马仕审核 → 告诉用户结果
3. ⛔ 同一文件不能同时交两个 Agent 改
4. 扣带思走 :1234，克劳德走 Anthropic 兼容 API

## 技术偏好
- 主力模型: DeepSeek V4（走本地代理 127.0.0.1:1234）
- 编程语言: Python, JavaScript/TypeScript
- 操作系统: Windows 11
- 常用工具: curl, PowerShell, Python 3.11, Git

## 沟通风格
- 语言: 简体中文
- 喜欢直接开干，不喜欢废话
- 注重结果和实用性

## 工作流
1. 先理解问题，再动手
2. 遇到不确定的先查日志和记忆
3. 完成工作后更新日志记录供下次参考
4. 用 execution-log.md 格式记录关键决策

## 代理相关设置
- 代理地址: http://127.0.0.1:1234/v1
- provider 名称: local-deepseek
- API 类型: responses
- 启动脚本: D:\maozhua\Codex\启动代理.bat
- Proxy 已升级为 Waitress 4 线程（2026-05-28），不再因 generator 异常闪退

## 本地知识库（宪法级 — 详见 D:/hermes-tools/KB_AGENTS.md）

**核心铁律：先搜再做，做完必写。** 所有 Agent 强制遵守，无例外。

### 查询（开工前 MUST）
```bash
python D:/hermes-tools/scripts/query_kb.py "关键词"
python D:/hermes-tools/scripts/query_kb.py "关键词" --topic ai-coding
python D:/hermes-tools/scripts/query_kb.py "关键词" -t ai-coding -n 10
python D:/hermes-tools/scripts/query_kb.py --list-topics
```

### 写入（完工后 MUST，topic 必填）
```bash
python D:/hermes-tools/scripts/add_to_kb.py "内容" ai-coding "标题"
```

### 8 个 Topic
ai-coding / ai-models / prompt-engineering / methodology / kb-system / knowledge-management / 行业百态 / global-infra

### 三层路由
本地 KB (:8765) → IMA OpenAPI → 推理 + WebSearch

### 何时查 KB（强制场景）
1. 遇到报错 → 先搜 KB
2. 修改配置前 → 先搜 KB
3. 不确定怎么做 → 搜 methodology
4. 用户问历史 → 查 KB，不凭记忆
5. 任何非 trivial 任务开工前 → 花 5 秒搜

### 何时写 KB（强制场景）
1. 修了报错 → 根因 + 修复步骤
2. 发现新方法 → 可复用方法论
3. 工具链变更 → 配置/路径/版本
4. 踩坑经验 → 花时间才搞明白的事
5. 用户说"记住" → 立刻写
6. 聊出实质性结论 → 主动问要不要存

## 全局规则
- ⛔ 禁止任何文件写入 C 盘，所有安装和文件操作只能去 D 盘
- ✅ 本规则对 3 个 Agent（爱马仕/克劳德/扣带思）均有效

## 升级迁移规则（2026-05-29 确认）
- Codex CLI 升级到新版后，必须将旧版 工作日志.md 的数据迁移到新版对应路径
- 迁移内容包括所有操作记录、P0/P1/P2 链路、技术债清单
- 完成后在 execution-log.md 中记录迁移状态
