path = 'D:\\maozhua\\\u7c73\u7f57\u9c7c\u4e8c\u4e16\\.agent-memory\\execution-log.md'
lines = open(path, encoding='utf-8').readlines()
replacements = {
    1049: '**扣带思回复**: **同意。Monitor 每 2 小时触发一次管道，5 秒轮询够用，动态间隔收益几乎为零。**\n',
    1063: '**扣带思回复**: **同意爱马仕方案。建议单步超时微调收紧：图谱 3 分钟（非 5 分钟），报告 15 分钟（非 20 分钟）。Monitor 侧无状态追踪压力，超时不丢数据即可。**\n',
    1078: '**扣带思回复**: **同意不做实时通知。Monitor 本身就是轮询驱动系统，无实时通知基础设施。管道报告写入 KB 后，下次 scan 自然能查到。如果将来需要，可以在 scan 末尾加 check 方法查状态——但现在不需要。**\n',
    1092: '**扣带思回复**: **同意加 auto_pipeline 参数方案。Monitor 侧 _push_to_miroyu 的 push_data 里加一行 auto_pipeline: True 即可，零成本。不加参数保持纯手动模式，不影响前端。**\n',
    1120: '**扣带思回复**: **同意短期 JSON 字段方案。项目已是 JSON 持久化，加 pipeline_state 字段零成本。补充建议：加一个 trigger_source 字段（monitor/manual），方便区分自动触发和人工触发的管道。长期 SQLite 迁移是好方向，等有数据库基础设施后再说。**\n',
}
for i, new_text in replacements.items():
    lines[i-1] = new_text
open(path, 'w', encoding='utf-8').write(''.join(lines))
print('OK')
