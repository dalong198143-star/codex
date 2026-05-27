# Codex 国产模型代理项目

## 项目概述
本地协议转换代理，让 Codex CLI 能用国产模型替代 OpenAI/Anthropic API。
核心原理: Anthropic Responses API ↔ OpenAI Chat Completions API 双向转换。

## 目录结构
```
D:\maozhua\Codex\
├── src/                    # 核心源码（模块化后）
│   ├── server.py           # Flask 路由 + 入口
│   ├── converter.py        # 协议转换
│   ├── sse_builder.py      # SSE 事件构造
│   └── config.py           # 配置
├── codex/                  # Codex 工具脚本
│   ├── knowledge/          # 知识库配置
│   ├── rules/              # 编码规范
│   └── changelog/          # 变更日志
├── codex_proxy.py          # 旧版单文件代理（已归档）
├── litellm_config.yaml     # LiteLLM 模型路由配置
├── *.bat / *.ps1           # 启动/测试脚本
└── *.log                   # 运行日志
```

## 启动方式
```powershell
.\启动代理.bat          # 双窗口后台启动 LiteLLM + Proxy
.\test_proxy.bat        # 诊断测试
curl http://127.0.0.1:1234/health  # 健康检查
```

## 关键配置
- 全局记忆: D:\.codex\memories\codex-project-log.md
- 全局记忆: D:\.codex\memories\user-profile.md
- 执行日志: .agent-memory\execution-log.md
- 项目计划: PLAN.md

## 编码规范
- Python 3.11+
- 修改后验证: 启动代理测试完整链路
- 每次完成修改后更新执行日志

## 全局约束
- ⛔ 禁止写入 C 盘任何路径
- ✅ 所有文件只能写入 D 盘及当前工作区目录
- 🔒 此规则已记入全局记忆 user-profile.md，每次新对话生效
- 知识库回写: 在对话结束前检查有无可入库的知识，优先写入 ai-coding / methodology 等主题
  工具: python D:/hermes-tools/scripts/add_to_kb.py
