Write-Host "正在安装学习和记忆类技能到 D 盘..." -ForegroundColor Green

# 复制学习和记忆类技能
Write-Host "复制技能到 D:\.codex\skills"

# Jupyter 笔记本（学习和实验）
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\jupyter-notebook" -Destination "D:\.codex\skills\" -Recurse -Force
Write-Host "✓ jupyter-notebook" -ForegroundColor Cyan

# Notion 知识捕获（记忆和知识库）
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\notion-knowledge-capture" -Destination "D:\.codex\skills\" -Recurse -Force
Write-Host "✓ notion-knowledge-capture" -ForegroundColor Cyan

# Notion 会议智能（会议记录和材料）
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\notion-meeting-intelligence" -Destination "D:\.codex\skills\" -Recurse -Force
Write-Host "✓ notion-meeting-intelligence" -ForegroundColor Cyan

# Notion 规范到实施（规划和任务）
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\notion-spec-to-implementation" -Destination "D:\.codex\skills\" -Recurse -Force
Write-Host "✓ notion-spec-to-implementation" -ForegroundColor Cyan

Write-Host "`n✓ 学习和记忆类技能安装完成！" -ForegroundColor Green
Write-Host "`n当前技能列表："
Get-ChildItem -Path "D:\.codex\skills" -Directory | Select-Object Name

Write-Host "`n请重启 Codex 以使技能生效。" -ForegroundColor Yellow
