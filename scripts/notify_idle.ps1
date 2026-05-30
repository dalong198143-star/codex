# Idle notification — called by Claude Code Notification hook (matcher: idle_prompt)
Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
$icon = [System.Drawing.SystemIcons]::Information
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = $icon
$balloon.BalloonTipTitle = "Claude Code 空闲"
$balloon.BalloonTipText = "等待你的输入中..."
$balloon.Visible = $true
$balloon.ShowBalloonTip(8000)
Start-Sleep -Seconds 10
$balloon.Dispose()
