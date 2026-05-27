# Codex Agent 反思脚本
# 用法: 在每次任务完成后调用
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      Codex Agent 任务后反思          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. 检查错误模式库是否有新错误需要记录
Write-Host "步骤1: 回顾本次任务中遇到的错误" -ForegroundColor Yellow
Write-Host "  - 是否有未记录到错误模式库的新错误？" -ForegroundColor Gray
Write-Host "  - 现有修复方案是否有效？" -ForegroundColor Gray
Write-Host ""

# 2. 检查经验缓存是否需要更新
Write-Host "步骤2: 提取本次学到的经验" -ForegroundColor Yellow
Write-Host "  - 有什么新技能可以记录？" -ForegroundColor Gray
Write-Host "  - 有什么新模式可以复用？" -ForegroundColor Gray
Write-Host "  - 有什么新陷阱要避免？" -ForegroundColor Gray
Write-Host ""

# 3. 检查执行日志
Write-Host "步骤3: 写入执行日志" -ForegroundColor Yellow
Write-Host "  格式: [LOG-NNN] 任务描述" -ForegroundColor Gray
Write-Host "  记录: 触发方式/执行过程/成功模式/失败/经验" -ForegroundColor Gray
Write-Host ""

Write-Host "建议: 将反思结果写入 .agent-memory/ 目录" -ForegroundColor Green
