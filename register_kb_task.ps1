# 注册 KB 定时维护任务（每天凌晨 3:00）
# 以管理员身份运行

$taskName = "CodexKB-Maintenance"
$scriptPath = "D:\maozhua\Codex\kb_maintain.py"
$pythonPath = "python"
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At 03:00
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

Write-Host "[OK] Scheduled task '$taskName' created (daily 03:00)" -ForegroundColor Green
Write-Host ""
Write-Host "Test run:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
Write-Host "  Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo" -ForegroundColor Gray
