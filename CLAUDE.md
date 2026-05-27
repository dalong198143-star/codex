# Codex 项目配置

## 本地知识库查询
需要技术经验、项目决策、方法论时查本地知识库:
```bash
python D:/hermes-tools/scripts/query_kb.py "查询内容" [集合名] [条数]
```
集合: say-it-well(话说清楚), general(通用), video-platform, competitors

## 代理配置
- 本地代理: LiteLLM (127.0.0.1:1234 → DeepSeek)
- 启动: 运行 启动代理.bat
- 健康检查: curl http://127.0.0.1:1234/health
- provider 名称: local-deepseek

## 模型
- 主力: deepseek-v4-pro
- 代理地址: http://127.0.0.1:1234/v1
