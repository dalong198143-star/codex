# Codex 国产模型代理 — 项目全面分析与工作计划

> 分析日期：2026-05-23 | 版本：v1.0

---

## 一、项目概述

### 1.1 项目定位

**Codex 国产模型代理** 是一个本地运行的协议转换代理，使 Codex CLI（一个 AI 编程助手）能够使用中国大陆的国产大模型，替代 OpenAI / Anthropic 等境外 API。

核心原理：
- Codex CLI 发送 **Anthropic Responses API** 格式的 SSE 流式请求
- 本代理将其转换为 **OpenAI Chat Completions API** 格式
- 通过 **LiteLLM** 网关路由到 DeepSeek、智谱、Kimi、通义千问等国产模型
- 将 Chat Completions 响应再包装为 SSE 事件流返回给 Codex

### 1.2 架构图

```
┌──────────┐     SSE Events (Responses API)     ┌───────────────┐
│          │  POST /v1/responses  ──────────────▶│               │
│  Codex   │  GET  /v1/models     ──────────────▶│  codex_proxy  │
│   CLI    │  GET  /health        ──────────────▶│   Flask :1234 │
│          │◀────────────────────────────────────│               │
└──────────┘                                     └───────┬───────┘
                                                         │
                                           Chat Completions API
                                           POST /v1/chat/completions
                                                         │
                                                 ┌───────▼───────┐
                                                 │   LiteLLM     │
                                                 │   :1235        │
                                                 │               │
                                                 │ 路由/重试/降级 │
                                                 └───┬───┬───┬───┘
                                                     │   │   │
                                      ┌──────────────┼───┼───┼──────────────┐
                                      │              │   │   │              │
                                 DeepSeek        智谱GLM  Kimi     通义千问
                              (主力/推理/Flash)  (GLM-4.6) (K2.6)  (Qwen-Coder)
```

### 1.3 技术栈

| 组件 | 技术 | 版本/规格 |
|------|------|-----------|
| 协议转换代理 | Python 3.11 + Flask | 265 行单文件 |
| LLM 网关 | LiteLLM (pip 包) | 配置文件驱动 |
| 环境变量 | Windows Batch `.env.bat` | 5 个 API Key |
| 启动方式 | Windows 批处理 | 双窗口后台启动 |
| 运行环境 | Windows 11 | Python 3.11 + curl |

### 1.4 文件清单（共 6 个文件，总计 ~16KB）

| 文件 | 大小 | 用途 | 状态 |
|------|------|------|------|
| `codex_proxy.py` | 9.1KB / 265行 | 核心 SSE 协议转换代理 | **主力** |
| `litellm_config.yaml` | 2.7KB / 102行 | LiteLLM 模型路由配置 | **主力** |
| `start_proxy.bat` | 1.7KB / 52行 | 一键启动脚本 | 使用中 |
| `test_proxy.bat` | 2.0KB / 48行 | 诊断测试脚本 | 使用中 |
| `.env.bat` | 224B / 6行 | 真实 API Key（敏感） | **切勿提交** |
| `.env.example` | 312B / 8行 | API Key 模板 | 参考用 |

---

## 二、当前进度评估

### 2.1 已完成 ✅

- [x] **基础协议转换**：Responses API → Chat Completions 的核心映射已实现
  - message / function_call / function_call_output 三种输入类型
  - 输出 message 和 function_call 两种输出项
  - SSE 事件格式符合 Anthropic Responses API 规范（`response.created → in_progress → output_item.added/done → completed`）
- [x] **多模型支持**：通过 LiteLLM 注册了 7 个模型，覆盖 4 个国产厂商
  - DeepSeek V4（主力）/ V4 Flash（快思考）/ V4 Pro（深度推理）/ R1（推理）
  - 智谱 GLM-4.6 / Kimi K2.6 / Qwen-Coder-Plus
- [x] **模型别名映射**：GPT 系列模型名自动转换为 deepseek-v4
- [x] **高可用基础**：LiteLLM 层面已配置重试（3次）、超时（120s）、熔断（10次失败/5秒冷却）、模型间 fallback 链
- [x] **智能路由**：LiteLLM 基于延迟感知的动态路由（latency-based-routing）
- [x] **健康检查**：`/health` 和 `/v1/models` 端点可用
- [x] **启动脚本**：一键启动双服务（LiteLLM + Flask），含健康等待和说明

### 2.2 进行中 / 半成品 🔄

- [ ] **SSE 流式传输是假的**：代理先拿到整个 Chat Completions 响应，再一次性构造所有 SSE 事件。真正的 SSE 应该逐 token 流式输出。
- [ ] **工具调用仅支持单轮**：function_call / function_call_output 只处理了基本格式，未覆盖多工具并行调用、工具调用失败的 retry 等复杂场景
- [ ] **推理模型支持不完整**：DeepSeek R1 / V4 Pro 的 reasoning_content 被直接丢弃，未映射到 Responses API 的 thinking 事件

### 2.3 待办 ❌

- [ ] 真正的流式传输（stream: true）
- [ ] 增量内容事件（`response.content_part.added`、`response.content_part.delta`）
- [ ] reasoning / thinking 内容支持
- [ ] 单元测试 / 集成测试
- [ ] 日志系统
- [ ] 配置管理
- [ ] 认证授权
- [ ] Docker 容器化
- [ ] 速率限制
- [ ] 优雅关闭（graceful shutdown）
- [ ] 命令行参数化
- [ ] 性能监控 / 可观测性

---

## 三、问题与改进空间

### 3.1 🔴 严重问题（安全 / 正确性）

#### P0-1：`.env.bat` 包含真实 API Key
**文件**：`.env.bat`  
**问题**：DeepSeek 和 DashScope 的真实 API Key 硬编码在文件中。一旦提交到 Git 或被共享，密钥即泄露。  
**修复**：立即将 `.env.bat` 加入 `.gitignore`；如果已经提交过，需要在服务商后台轮换密钥。

#### P0-2：SSE 流式传输是假的（核心架构缺陷）
**文件**：`codex_proxy.py:210-230`  
**问题**：当前代码向 LiteLLM 发的是非流式请求（无 `stream: true`），收到完整响应后才构造 SSE 事件。用户看到的是"卡住→突然全部输出"，而不是逐词打字效果。  
**影响**：用户体验差（长时间等待无反馈）；首 token 延迟 = 总延迟。  
**修复**：需要重写 `handle_responses()`，开启 LiteLLM 流式请求，每收到一个 chunk 就实时转发为 SSE 事件。

#### P0-3：测试脚本绕过了代理层
**文件**：`test_proxy.bat:30-37`  
**问题**：测试脚本直接调用 port 1235（LiteLLM），而不是 port 1234（代理）。这意味着 SSE 协议转换逻辑从未被测试过。  
**修复**：测试脚本应调用 `http://localhost:1234/v1/responses`，验证 SSE 事件格式。

### 3.2 🟡 中等问题（可靠性 / 可维护性）

#### P1-1：没有流式增量事件
**文件**：`codex_proxy.py:167-225`  
**问题**：`build_sse_events()` 只生成了 `output_item.added` 和 `output_item.done`，缺少：
- `response.content_part.added`（内容分片开始）
- `response.content_part.delta`（增量内容，这才是流式的核心）
- `response.reasoning_text.delta`（推理过程增量）
**影响**：即使修复了流式传输，缺少增量事件也会导致前端显示异常。

#### P1-2：推理模型 thinking/reasoning 内容被丢弃
**文件**：`codex_proxy.py:85-93`、`build_sse_events()`  
**问题**：DeepSeek R1 返回的 `reasoning_content` 字段和 V4 Pro 的 thinking tokens 没有被处理。这些模型在给出最终答案前会先输出推理链，这部分内容应该映射为 Responses API 的 `reasoning_text` 类型输出。  
**影响**：R1 和 V4 Pro 的用户无法看到模型的推理过程，模型能力被浪费。

#### P1-3：系统提示词注入过于粗暴
**文件**：`codex_proxy.py:13-17, 59-63`  
**问题**：无论调用者传入什么 `instructions`，`AGENT_SYSTEM_PROMPT` 都会强制前置拼接到 system message 最前面。如果调用者已经有了自己的 agent 提示词，会出现重复或冲突。  
**修复**：改为可配置的开关；或者检测调用者是否已提供 agent 相关指令。

#### P1-4：无请求级错误恢复
**文件**：`codex_proxy.py:125-148`  
**问题**：上游 LiteLLM 返回非 200 时，直接返回 502 错误文本。Codex CLI 收到后通常直接报错退出，无法重试。  
**修复**：对 transient errors 进行重试；区分 4xx（不重试）和 5xx（重试）。

#### P1-5：单文件巨石架构
**问题**：265 行全部在一个 `codex_proxy.py` 中，包含转换逻辑、SSE 构造、HTTP 处理、配置。随着功能增加，维护难度线性增长。  
**建议**：拆分为 `converter.py`（协议转换）、`sse.py`（SSE 事件）、`server.py`（Flask 路由）。

### 3.3 🟢 轻微问题（体验 / 工程化）

#### P2-1：无日志系统
**问题**：只使用 `print()` 输出，无法按级别过滤、无法落盘持久化。排查问题时缺乏请求级别的 trace ID。

#### P2-2：无认证机制
**问题**：`/v1/responses` 端点完全开放，任何能访问 localhost:1234 的进程都可以调用。

#### P2-3：硬编码值过多
**问题**：LiteLLM 地址 `http://127.0.0.1:1235`、端口 1234、超时 180s、模型映射表 `KNOWN_MODELS` 全部硬编码。应该支持环境变量或配置文件覆盖。

#### P2-4：无优雅关闭
**问题**：`app.run()` 直接启动，没有信号处理。Ctrl+C 时 Flask 直接终止，未完成的请求丢失。

#### P2-5：start_proxy.bat 硬编码 Python 路径
**问题**：`set "PATH=%APPDATA%\Python\Python311\Scripts;%PATH%"` 假设 Python 3.11 安装在 AppData。如果用户使用其他版本或全局安装则会失败。

#### P2-6：无 Docker 支持
**问题**：项目仅支持 Windows 批处理启动。对 Linux/Mac 用户不友好，也无法在 CI 或服务器环境中部署。

#### P2-7：零测试覆盖
**问题**：没有任何自动化测试。每次修改后只能手动启动 + curl 验证。

---

## 四、工作计划

### 4.1 任务依赖关系图

```
                    ┌──────────────────────┐
                    │  P0-1: 密钥安全加固   │ (无依赖，立即执行)
                    └──────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
   ┌──────────────────────┐     ┌──────────────────────┐
   │  P0-2: 真流式传输     │     │  P0-3: 修复测试脚本   │
   │  (架构核心改造)        │◄────│                      │
   └──────────┬───────────┘     └──────────────────────┘
              │
              ▼
   ┌──────────────────────┐
   │  P1-1: 增量 SSE 事件  │ (依赖 P0-2)
   └──────────┬───────────┘
              │
   ┌──────────┴───────────┐
   ▼                      ▼
┌──────────┐     ┌──────────────┐
│ P1-2     │     │ P1-4         │
│ thinking │     │ 错误恢复      │
│ 支持     │     │              │
└────┬─────┘     └──────┬───────┘
     │                  │
     └──────┬───────────┘
            ▼
   ┌──────────────────────┐
   │  P1-3: 提示词可配置    │
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  P1-5: 模块化拆分     │ ← 建议在此之后再做后续功能
   └──────────┬───────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
┌──────────┐    ┌──────────────┐
│ P2-1     │    │ P2-4         │
│ 日志系统  │    │ 优雅关闭      │
└────┬─────┘    └──────┬───────┘
     │                 │
     └────────┬────────┘
              ▼
   ┌──────────────────────┐
   │  P2-2: 认证 (可选)    │
   └──────────┬───────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
┌──────────┐    ┌──────────────┐
│ P2-5     │    │ P2-6         │
│ 跨平台    │    │ Docker 化    │
└──────────┘    └──────────────┘
```

### 4.2 短期任务（1-3 天，立即启动）

| 编号 | 任务 | 优先级 | 预估工时 | 依赖 | 描述 |
|------|------|--------|----------|------|------|
| **S1** | 密钥安全加固 | 🔴 P0 | 15 分钟 | 无 | 创建 `.gitignore`，将 `.env.bat` 加入忽略列表；在 `.env.example` 顶部显式加安全警告注释 |
| **S2** | 修复测试脚本 | 🔴 P0 | 30 分钟 | 无 | `test_proxy.bat` 改为调用 port 1234 的 `/v1/responses` 端点，真正测试 SSE 协议转换 |
| **S3** | 真流式 SSE 传输 | 🔴 P0 | 4-6 小时 | 无 | 重写核心流式逻辑：向 LiteLLM 发 `stream: true`，逐 chunk 实时转发为 SSE 事件 |
| **S4** | 增量 SSE 事件支持 | 🟡 P1 | 2-3 小时 | S3 | 在流式基础上，为每个文本片段发送 `response.content_part.added` + `response.content_part.delta` + `response.content_part.done` |
| **S5** | 请求级错误恢复 | 🟡 P1 | 1-2 小时 | 无 | 区分 4xx/5xx，对可重试错误进行有限次数重试（含指数退避） |

**短期里程碑**：代理实现真正的逐 token 流式输出，Codex CLI 用户能看到实时打字效果。

### 4.3 中期任务（1-2 周）

| 编号 | 任务 | 优先级 | 预估工时 | 依赖 | 描述 |
|------|------|--------|----------|------|------|
| **M1** | reasoning/thinking 内容支持 | 🟡 P1 | 3-4 小时 | S3 | 解析 DeepSeek R1 的 `reasoning_content` 和 V4 Pro 的 thinking tokens，映射为 Responses API `reasoning_text` 输出。需要在 `build_sse_events` 中增加 reasoning 相关事件类型 |
| **M2** | 系统提示词可配置化 | 🟡 P1 | 1-2 小时 | 无 | 通过环境变量 `CODEX_SYSTEM_PROMPT` 控制是否注入 agent 提示词、注入什么内容。支持 `CODEX_SYSTEM_PROMPT=none` 关闭注入 |
| **M3** | 模块化拆分 | 🟡 P1 | 3-4 小时 | S4, M1 | 将 `codex_proxy.py` 拆分为 `converter.py`（协议转换）、`sse_builder.py`（SSE 事件）、`server.py`（Flask 路由）+ `config.py`（配置）。保持功能不变，纯重构 | ✅ **已完成** |
| **M4** | 日志系统 | 🟢 P2 | 1-2 小时 | 无 | 引入 `logging` 模块，按请求生成 `request_id`（trace_id），支持 DEBUG/INFO/WARN/ERROR 级别，控制台 + 文件双输出。LiteLLM 层也开启 `set_verbose: true`（仅 DEBUG 模式） |
| **M5** | 单元测试覆盖 | 🟢 P2 | 4-6 小时 | M3 | 对 `converter.py` 和 `sse_builder.py` 编写 pytest 测试：已知模型映射、各种 input 类型解析、工具调用格式转换、SSE 事件格式验证 |
| **M6** | 优雅关闭 | 🟢 P2 | 1-2 小时 | 无 | 捕获 SIGINT/SIGTERM，等待进行中的请求完成（最多 30s），然后关闭 Flask。`start_proxy.bat` 同步处理 |

**中期里程碑**：项目结构清晰，有测试保护，日志可追踪，支持推理模型。

### 4.4 长期规划（2-4 周+）

| 编号 | 任务 | 优先级 | 预估工时 | 依赖 | 描述 |
|------|------|--------|----------|------|------|
| **L1** | 配置管理重构 | 🟢 P2 | 2-3 小时 | M3 | 所有硬编码值（端口、超时、LiteLLM 地址、模型映射）迁移到 YAML/TOML 配置文件 + 环境变量覆盖。支持 `CODEX_CONFIG=path/to/config.yaml` |
| **L2** | 认证中间件 | 🟢 P2 | 2-3 小时 | M3 | 通过 `LITELLM_MASTER_KEY` 或独立 `CODEX_API_KEY` 环境变量启用 Bearer Token 认证。开发环境下可关闭 |
| **L3** | Docker 容器化 | 🟢 P2 | 3-4 小时 | L1 | 编写 `Dockerfile` + `docker-compose.yml`。两个容器（codex-proxy + litellm）通过内部网络通信。支持 `.env` 文件注入密钥 |
| **L4** | 跨平台启动脚本 | 🟢 P2 | 1-2 小时 | L3 | 提供 `start_proxy.sh`（Linux/Mac）和 `.ps1`（PowerShell 原生）版本，替代纯 Batch |
| **L5** | 速率限制 | 🟢 P2 | 2-3 小时 | M3 | Flask 层增加基于令牌桶的速率限制，防止本地其他进程滥用（按 IP + 端点粒度） |
| **L6** | 可观测性 | 🟢 P2 | 3-4 小时 | M4 | Prometheus metrics（请求量/延迟/错误率/首token延迟）。可选 Grafana dashboard。结构化日志（JSON 格式）支持 ELK/Loki 采集 |
| **L7** | 模型热切换 | 🟢 P2 | 2-3 小时 | L1 | 通过 SIGHUP 信号重新加载模型配置，无需重启代理。或者监听配置文件变化自动重载 |
| **L8** | 输入校验 | 🟢 P2 | 1-2 小时 | M3 | 对 `/v1/responses` 的请求体进行 schema 校验（必填字段、类型检查），返回结构化错误而非 500 |
| **L9** | 集成测试 | 🟢 P2 | 3-4 小时 | M5, L3 | 使用 docker-compose 启动全套环境，通过 pytest 发送真实请求到代理，验证端到端流式响应 |

**长期里程碑**：生产级可部署的代理服务，支持容器化部署、监控告警、热更新。

### 4.5 优先级矩阵

```
                    高影响
                      │
         S3 S4       │       S1 S2
         (流式)      │       (安全/测试)
                      │
    ──────────────────┼──────────────────
                      │
         M1 M2 M3    │       S5 M4 M5
         (功能增强)   │       (可靠性)
                      │
         L3 L6 L7    │       L1 L2 L5 L8
         (运维体验)   │       (工程化)
                      │
                    低影响
    低紧急 ←──────────────────────→ 高紧急
```

---

## 五、实现顺序建议

### 第一阶段：修复基础（第 1-2 天）

1. **S1 密钥安全** → 创建 `.gitignore`，轮换已暴露的密钥（可选）
2. **S3 真流式传输** → 这是项目当前最大的功能缺陷，修复后用户体验质的提升
3. **S4 增量事件** → 紧跟在 S3 之后，补全 SSE 事件完整性
4. **S2 修复测试** → 用新的流式端点验证整套链路

### 第二阶段：增强功能（第 3-5 天）

5. **S5 错误恢复** → 减少请求失败率
6. **M1 reasoning 支持** → 释放推理模型完整能力
7. **M2 提示词配置** → 提升灵活性，避免硬编码提示词造成的冲突

### 第三阶段：工程化（第 6-10 天）

8. **M3 模块化拆分** → 为后续所有功能打好地基
9. **M4 日志系统** → 可追踪、可调试
10. **M5 单元测试** → 回归保护
11. **M6 优雅关闭** → 减少数据丢失风险

### 第四阶段：生产化（第 3-4 周）

12. **L1 配置管理** → 消除硬编码
13. **L3 Docker 化** → 跨平台/可部署
14. **L4 跨平台脚本** → 服务 Linux/Mac 用户
15. **L6 可观测性** → 生产运维必备
16. 其余 L 任务按需推进

---

## 六、风险与注意事项

1. **API 密钥轮换**：`.env.bat` 中的 DeepSeek 和 DashScope 密钥可能已经泄露（取决于文件分发范围）。如果曾被分享或上传，建议立即在对应服务商后台生成新密钥。
2. **Codex CLI 协议稳定性**：Codex 的 Responses API 格式可能随版本更新而变化。需要持续关注上游协议变更。
3. **LiteLLM 版本兼容**：LiteLLM 更新频繁，`litellm_config.yaml` 中的字段名可能在版本升级后变化。建议固定版本号（`pip install litellm==x.x.x`）。
4. **DeepSeek API 速率限制**：`deepseek-v4` 设置了 500 RPM，但实际 API Key 可能有更严格的付费限制（如 QPS 上限）。需要根据实际购买套餐调整。
5. **推理模型的特殊性**：R1 不支持 function calling（已标注 `supports_function_calling: false`），但代理会在有 tools 时依然发送 tools 参数给 R1，导致报错。需要增加模型能力感知的路由。
6. **Windows 平台特有**：当前完全依赖 Windows Batch + `start /MIN`。迁移到 Linux 服务器或 CI 环境需要额外工作。

---

## 七、附录

### A. 推荐的 .gitignore 内容

```gitignore
# 敏感文件
.env.bat

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp

# 日志
*.log

# Docker
.docker/
```

### B. 推荐的目录结构（模块化后）

```
D:\maozhua\Codex\
├── .env.example
├── .gitignore
├── pyproject.toml              # 或 requirements.txt
├── litellm_config.yaml
├── config.yaml                 # 新增：代理自身配置
├── docker-compose.yml          # 新增
├── Dockerfile                  # 新增
├── start_proxy.bat
├── start_proxy.sh              # 新增
├── start_proxy.ps1             # 新增
├── test_proxy.bat
├── src/
│   ├── __init__.py
│   ├── config.py               # 配置（从 codex_proxy.py 拆分） ✓
│   ├── converter.py            # Responses → Chat 协议转换 ✓
│   ├── sse_builder.py          # SSE 事件构造（流式 + 非流式） ✓
│   └── server.py               # Flask 路由 + 启动入口 ✓
│   └── middleware.py            # 认证、日志、限流 (新增)
├── tests/
│   ├── __init__.py
│   ├── test_converter.py
│   ├── test_sse_builder.py
│   └── test_integration.py
└── logs/                       # 日志输出目录
```

### C. 关键环境变量参考

| 变量 | 用途 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | ✅ |
| `ZHIPU_API_KEY` | 智谱 GLM API 密钥 | 可选 |
| `MOONSHOT_API_KEY` | Moonshot Kimi API 密钥 | 可选 |
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API 密钥 | 可选 |
| `LITELLM_MASTER_KEY` | LiteLLM 管理密钥 | ✅ |
| `CODEX_PROXY_PORT` | 代理监听端口 (默认 1234) | 可选 |
| `LITELLM_PORT` | LiteLLM 后端端口 (默认 1235) | 可选 |
| `CODEX_SYSTEM_PROMPT` | 自定义系统提示词 | 可选 |
| `CODEX_API_KEY` | 代理认证密钥 | 可选 |
| `CODEX_LOG_LEVEL` | 日志级别 (DEBUG/INFO/WARN/ERROR) | 可选 |
