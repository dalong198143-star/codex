Write-Host "正在安装技能到 D 盘..." -ForegroundColor Green

# 清理错误复制的文件
Write-Host "清理错误文件..."
Remove-Item -Path "C:\Users\ThinkBook\gh-fix-ci" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Users\ThinkBook\playwright" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Users\ThinkBook\security-best-practices" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Users\ThinkBook\cloudflare-deploy" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Users\ThinkBook\notion-research-documentation" -Recurse -Force -ErrorAction SilentlyContinue

# 复制技能
Write-Host "复制技能到 D:\.codex\skills"
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\gh-fix-ci" -Destination "D:\.codex\skills\" -Recurse -Force
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\playwright" -Destination "D:\.codex\skills\" -Recurse -Force
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\security-best-practices" -Destination "D:\.codex\skills\" -Recurse -Force
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\cloudflare-deploy" -Destination "D:\.codex\skills\" -Recurse -Force
Copy-Item -Path "D:\.codex\vendor_imports\skills\skills\.curated\notion-research-documentation" -Destination "D:\.codex\skills\" -Recurse -Force

Write-Host "`n✓ 技能安装完成！" -ForegroundColor Green
Write-Host "`n当前技能列表："
Get-ChildItem -Path "D:\.codex\skills" -Directory | Select-Object Name

Write-Host "`n请重启 Codex 以使技能生效。" -ForegroundColor Yellow
