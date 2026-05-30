# Codex 国产模型代理项目

## 项目概述
本地协议转换代理，让 Codex CLI 能用国产模型替代 OpenAI/Anthropic API。
核心原理: Anthropic Responses API ↔ OpenAI Chat Completions API 双向转换。

## 本地知识库（宪法级 — 详见 D:/hermes-tools/KB_AGENTS.md）

**先搜再做，做完必写。** 所有 Agent 强制遵守。

```bash
# 查（开工前必查）
python D:/hermes-tools/scripts/query_kb.py "关键词"
python D:/hermes-tools/scripts/query_kb.py "关键词" --topic ai-coding
python D:/hermes-tools/scripts/query_kb.py --list-topics

# 写（完工后必写，topic 8选1）
python D:/hermes-tools/scripts/add_to_kb.py "内容" ai-coding "标题"
```

8 个 topic: ai-coding / ai-models / prompt-engineering / methodology / kb-system / knowledge-management / 行业百态 / global-infra

三层路由: 本地 KB (:8765) → IMA OpenAPI → 推理+搜索

## 目录结构
```
D:\maozhua\Codex\
├── src/                    # 核心源码（模块化后）
│   ├── server.py           # Waitress WSGI + Flask 路由（2026-05-28 升级，4线程）
│   ├── converter.py        # 协议转换
│   ├── sse_builder.py      # SSE 事件构造
│   └── config.py           # 配置
├── CLAUDE.md               # 克劳德专用配置
├── codex_proxy.py          # 旧版单文件代理（已归档）
├── litellm_config.yaml     # LiteLLM 模型路由配置
├── *.bat / *.ps1           # 启动/测试脚本
└── *.log                   # 运行日志
```

## 启动方式
```powershell
.\启动代理.bat          # 双窗口后台启动 LiteLLM + Proxy (Waitress)
curl http://127.0.0.1:1234/health  # 健康检查
```

## 关键配置
- 全局知识库: D:/hermes-tools/KB_AGENTS.md（宪法级）
- 全局记忆: D:\.codex\memories\user-profile.md
- 执行日志: .agent-memory\execution-log.md
  **【仅当操作米罗鱼二世项目的日志时】** 禁止直接用 write_file / echo 覆盖。
  原因：米罗鱼没开 git，2026-05-29 曾因裸写覆盖丢失 1334 行历史。
  必须用: python D:/hermes-tools/scripts/safe_log_write.py <file> --append "<内容>"
  脚本自动备份(版本号+时间)、写入验证、异常回滚。这是米罗鱼特例，不是你自己的项目规则。
- 项目计划: PLAN.md
- 工作日志规范: D:\maozhua\克劳德\工作日志规范.md（三项目通用，审计累计/署名/自检等格式要求）

## 编码规范
- Python 3.11+
- 修改后验证: 启动代理测试完整链路
- 每次完成修改后更新执行日志

## 全局约束
- ⛔ 禁止写入 C 盘任何路径
- ✅ 所有文件只能写入 D 盘及当前工作区目录
