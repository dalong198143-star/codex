# Codex 项目配置 — 克劳德专用

## 本地知识库（宪法级强制）

**所有操作必须遵循 `D:/hermes-tools/KB_AGENTS.md`。**

核心铁律：**先搜再做，做完必写。** Query before acting. Write after solving.

### 何时查 KB（MUST，不查就是违规）
1. 遇到任何报错或异常 → 先搜 KB，不要盲调
2. 修改任何工具/代理/模型配置前 → 先搜 KB
3. 不确定怎么做 → 搜 `methodology` topic
4. 用户问"之前怎么做的" → 查 KB，不凭记忆
5. 任何非 trivial 任务开工前 → 花 5 秒搜一下

### 何时写 KB（MUST，不写就是透支）
1. 修了报错/故障 → 根因 + 修复步骤 + 关键命令
2. 发现新方法/技巧 → 可复用的方法论
3. 工具链变更 → 配置迁移、路径变化、版本升级
4. 踩了坑花了时间 → 值得记录的经验
5. 用户说"记住" → 立刻写
6. 聊出实质性结论 → 主动问"要不要存进知识库"

### 命令
```bash
# 查询（全量搜索返回 5 条，可按 topic 过滤）
python D:/hermes-tools/scripts/query_kb.py "关键词"
python D:/hermes-tools/scripts/query_kb.py "关键词" --topic ai-coding
python D:/hermes-tools/scripts/query_kb.py "关键词" -t ai-coding -n 10
python D:/hermes-tools/scripts/query_kb.py --list-topics

# 写入（topic 必填，8选1）
python D:/hermes-tools/scripts/add_to_kb.py "内容" ai-coding "标题"
```

8 个 topic: `ai-coding` `ai-models` `prompt-engineering` `methodology` `kb-system` `knowledge-management` `行业百态` `global-infra`

### 三层路由
本地 KB (:8765) → IMA OpenAPI → 推理 + WebSearch

---

## 代理配置

- 本地代理: LiteLLM (127.0.0.1:1235 → DeepSeek) + Codex Proxy (127.0.0.1:1234)
- 启动: `D:\maozhua\Codex\启动代理.bat`（双窗口：LiteLLM + Proxy）
- 健康检查: `curl -s http://127.0.0.1:1234/health`
- Proxy 已升级为 Waitress 4 线程（2026-05-28），不再因 generator 异常崩溃

## 模型

- 主力: deepseek-v4-pro
- 代理地址: http://127.0.0.1:1234/v1
- provider: local-deepseek

## 多Agent治理（2026-05-30 订立）

五Agent体系治理模块：`src/agent_governance.py`

克劳德作为唱反调者，额外职责：
1. **验证其他Agent的发现** — 每个报告必须被交叉验证
2. **追踪幽灵事件** — 任何自愈异常必须追问根因
3. **维护信用评分** — 监理/执行者/诊断者的每次报告都计入信用
4. **度量效率** — 每次多Agent任务的投入产出比

详见 `AGENTS.md` 第五章「多Agent治理规则」。

## 全局约束

- ⛔ 禁止写入 C 盘任何路径
- ✅ 所有文件只能写入 D 盘及当前工作区目录
