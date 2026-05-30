# Codex 国产模型代理启动脚本 - PowerShell 版本
# 正确设置环境变量

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Codex 国产模型代理启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置工作目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 加载环境变量
Write-Host "[1/6] 加载配置..." -ForegroundColor Yellow
if (Test-Path ".env.bat") {
    # 解析 .env.bat
    Get-Content ".env.bat" | ForEach-Object {
        if ($_ -match "^set\s+([A-Z0-9_]+)=(.*)$") {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value)
            Write-Host "  [OK] $name 已加载" -ForegroundColor Green
        }
    }
} else {
    Write-Host "[ERROR] 未找到 .env.bat" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 停止现有进程
Write-Host ""
Write-Host "[2/6] 停止旧进程..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 1234 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Get-NetTCPConnection -LocalPort 1235 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Get-Process -Name python,litellm -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500
Write-Host "  [OK] 旧进程已停止" -ForegroundColor Green

# 启动 LiteLLM
Write-Host ""
Write-Host "[3/6] 启动 LiteLLM 后端 (端口 1235)..." -ForegroundColor Yellow
$LiteLLMProcess = Start-Process powershell -ArgumentList "-WindowStyle", "Hidden", "-Command", "cd '$ScriptDir'  # API keys loaded from env/.env.bat; & 'D:\hermes-tools\python\Python311\Scripts\litellm.exe' --config '$ScriptDir\litellm_config.yaml' --port 1235" -PassThru

# 等待 LiteLLM
Write-Host "[*] 等待 LiteLLM 就绪..." -ForegroundColor DarkGray
$RetryCount = 0
$LiteLLMReady = $false
while (-not $LiteLLMReady -and $RetryCount -lt 30) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:1235/health" -Headers @{"Authorization"="Bearer $env:LITELLM_MASTER_KEY"} -Method Get -TimeoutSec 2 | Out-Null
        $LiteLLMReady = $true
    } catch {
        $RetryCount++
        Start-Sleep -Milliseconds 500
    }
}
if (-not $LiteLLMReady) {
    Write-Host "[ERROR] LiteLLM 启动超时" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}
Write-Host "  [OK] LiteLLM 已就绪" -ForegroundColor Green

# 启动 Codex 代理
Write-Host ""
Write-Host "[4/6] 启动 Codex 协议转换代理 (端口 1234)..." -ForegroundColor Yellow
$ProxyProcess = Start-Process powershell -ArgumentList "-WindowStyle", "Hidden", "-Command", "cd '$ScriptDir'; python -m src.server" -PassThru

# 等待代理
Write-Host "[*] 等待代理就绪..." -ForegroundColor DarkGray
$RetryCount = 0
$ProxyReady = $false
while (-not $ProxyReady -and $RetryCount -lt 20) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:1234/health" -Method Get -TimeoutSec 2 | Out-Null
        $ProxyReady = $true
    } catch {
        $RetryCount++
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ProxyReady) {
    Write-Host "[ERROR] 代理启动超时" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}
Write-Host "  [OK] 代理已就绪" -ForegroundColor Green

# 测试连接
Write-Host ""
Write-Host "[5/6] 测试连接..." -ForegroundColor Yellow
try {
    $Models = Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -Headers @{"Authorization"="Bearer $env:LITELLM_MASTER_KEY"} -Method Get
    Write-Host "  [OK] 连接成功，可用模型: $($Models.data.Count) 个" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] 连接测试失败，但服务仍在运行" -ForegroundColor Yellow
}

# 完成
Write-Host ""
Write-Host "[6/6] ================================" -ForegroundColor Cyan
Write-Host "[√] 服务已完全启动！" -ForegroundColor Green
Write-Host ""
Write-Host "可用模型:" -ForegroundColor White
Write-Host "  [1] deepseek-v4      - DeepSeek Chat" -ForegroundColor Gray
Write-Host "  [2] qwen3-coder      - Qwen Coder" -ForegroundColor Gray
Write-Host "  [3] deepseek-v4-pro  - DeepSeek V4 Pro" -ForegroundColor Gray
Write-Host "  [4] deepseek-v4-flash- DeepSeek V4 Flash" -ForegroundColor Gray
Write-Host "  [5] glm-5.1          - GLM-5.1" -ForegroundColor Gray
Write-Host "  [6] glm-4-flash      - GLM-4 Flash" -ForegroundColor Gray
Write-Host ""
Write-Host "代理地址: http://localhost:1234" -ForegroundColor DarkCyan
Write-Host "后端地址: http://localhost:1235" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "现在可以运行 Codex 了！" -ForegroundColor Green
Write-Host "按 Ctrl+C 停止服务 (后台窗口会继续运行)" -ForegroundColor DarkGray
Write-Host ""

# 保持窗口打开
while ($true) {
    Start-Sleep -Seconds 10
}

