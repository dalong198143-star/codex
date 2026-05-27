# Changelog

## 2026-05-27

### 知识库体系同步
- KB 架构整改：4 集合 → 1 集合（general），7 个标准 topic
- 常驻服务 kb_server.py 部署，查询从十几秒优化到 1 秒
- store_kb.py 重写，适配新版 API
- shared-kb.md 新建（Codex 专版手册）
- AGENTS.md 第6条引用共享 KB
- 给扣带思的本地KB指令.txt → 清空废弃
- 知识库审计：251 条，分布健康

### C盘清理（系统+软件）
- 软件层：Temp/Edge/pip/.cache/WinGet 清理，释放 4.8G
- .lingma 4.4G → D盘 + Junction 链接
- pagefile.sys 13.7G → D盘（重启后生效），预计 C 盘从 87% → 74%

### Codex 升级
- 0.133.0 → 0.134.0，npm 官方源不通，切 npmmirror 镜像
- 新旧双版本冲突（D:\OpenClaw vs D:\hermes-tools\npm），已统一到新版
- 代理链恢复：LiteLLM (1235) + SSE Proxy (1234)，Flask/flask-sock 补装

### 环境问题
- ChromaDB 1.5.9 Rust 后端 Windows 只读锁 → 子进程绕过
- 页面文件不足 + 代理阻塞 huggingface → 已修复

[2026-05-26 详情](codex/changelog/2026-05-27.md)
