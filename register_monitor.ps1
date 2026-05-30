# 注册情报系统 v2 定时扫描任务（Windows 计划任务）
# 以管理员身份运行: powershell -ExecutionPolicy Bypass -File register_monitor.ps1

$taskName = "GlobalNodeMonitor"
# $scriptPath 不再使用（用 -m monitor.main scan 代替）
$pythonPath = "C:\Program Files\Python311\python.exe"
$workDir = "D:\maozhua\Codex\codex\scripts"

# 删除旧任务（如果存在）
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "  已删除旧任务: $taskName" -ForegroundColor Yellow
}

# 构建执行命令
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "-m monitor.main scan" -WorkingDirectory $workDir

# 每 2 小时执行一次
$trigger = New-ScheduledTaskTrigger -Daily -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Days 365)

# 使用 SYSTEM 账户运行（不需要用户登录）
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

Write-Host ""
Write-Host "[OK] 计划任务已注册:" -ForegroundColor Green
Write-Host "  名称:    $taskName" -ForegroundColor Gray
Write-Host "  命令:    $pythonPath -m monitor.main scan" -ForegroundColor Gray
Write-Host "  工作目录: $workDir" -ForegroundColor Gray
Write-Host "  频率:    每 2 小时" -ForegroundColor Gray
Write-Host "  用户:    SYSTEM" -ForegroundColor Gray
Write-Host "  超时:    5 分钟" -ForegroundColor Gray
Write-Host ""
Write-Host "手动运行: Start-ScheduledTask -TaskName ""$taskName""" -ForegroundColor Yellow
Write-Host "查看状态: Get-ScheduledTask -TaskName ""$taskName"" | Get-ScheduledTaskInfo" -ForegroundColor Yellow
Write-Host "手动测试: cd D:\maozhua\Codex\codex\scripts && python -m monitor.main scan" -ForegroundColor Yellow
Write-Host ""
Write-Host "配置邮件 / SMTP 前确保已设置环境变量或 .monitor.env:" -ForegroundColor Yellow
Write-Host "  MAIL_TO / SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS" -ForegroundColor Gray


