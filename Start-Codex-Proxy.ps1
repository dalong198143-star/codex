# Codex Proxy Starter (English only - no encoding issues)
# PowerShell Version

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Codex China Models Proxy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Load environment variables
Write-Host "[1/6] Loading config..." -ForegroundColor Yellow
if (Test-Path ".env.bat") {
    Get-Content ".env.bat" | ForEach-Object {
        if ($_ -match "^set\s+([A-Z0-9_]+)=(.*)$") {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value)
            Write-Host "  [OK] Loaded $name" -ForegroundColor Green
        }
    }
} else {
    Write-Host "[ERROR] .env.bat not found" -ForegroundColor Red
    Read-Host "Press any key to exit"
    exit 1
}

# Stop existing processes
Write-Host ""
Write-Host "[2/6] Stopping old processes..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 1234 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Get-NetTCPConnection -LocalPort 1235 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Get-Process -Name python,litellm -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Write-Host "  [OK] Old processes stopped" -ForegroundColor Green

# Start LiteLLM
Write-Host ""
Write-Host "[3/6] Starting LiteLLM (port 1235)..." -ForegroundColor Yellow
$LiteLLMProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; . .env.bat; & 'C:\Users\ThinkBook\AppData\Roaming\Python\Python311\Scripts\litellm.exe' --config '$ScriptDir\litellm_config.yaml' --port 1235" -WindowStyle Minimized -PassThru

# Wait for LiteLLM
Write-Host "[*] Waiting for LiteLLM..." -ForegroundColor DarkGray
$RetryCount = 0
$LiteLLMReady = $false
while (-not $LiteLLMReady -and $RetryCount -lt 30) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:1235/health" -Method Get -TimeoutSec 2 | Out-Null
        $LiteLLMReady = $true
    } catch {
        $RetryCount++
        Start-Sleep -Seconds 1
    }
}
if (-not $LiteLLMReady) {
    Write-Host "[ERROR] LiteLLM timeout" -ForegroundColor Red
    Read-Host "Press any key to exit"
    exit 1
}
Write-Host "  [OK] LiteLLM ready" -ForegroundColor Green

# Start Codex proxy
Write-Host ""
Write-Host "[4/6] Starting Codex Proxy (port 1234)..." -ForegroundColor Yellow
$ProxyProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; . .env.bat; python -m src.server" -WindowStyle Minimized -PassThru

# Wait for proxy
Write-Host "[*] Waiting for proxy..." -ForegroundColor DarkGray
$RetryCount = 0
$ProxyReady = $false
while (-not $ProxyReady -and $RetryCount -lt 20) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:1234/health" -Method Get -TimeoutSec 2 | Out-Null
        $ProxyReady = $true
    } catch {
        $RetryCount++
        Start-Sleep -Seconds 1
    }
}
if (-not $ProxyReady) {
    Write-Host "[ERROR] Proxy timeout" -ForegroundColor Red
    Read-Host "Press any key to exit"
    exit 1
}
Write-Host "  [OK] Proxy ready" -ForegroundColor Green

# Test connection
Write-Host ""
Write-Host "[5/6] Testing connection..." -ForegroundColor Yellow
try {
    $Models = Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -Headers @{"Authorization"="Bearer sk-litellm-master-2026"} -Method Get
    Write-Host "  [OK] Connected, $($Models.data.Count) models available" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Connection test failed, but services may still run" -ForegroundColor Yellow
}

# Complete
Write-Host ""
Write-Host "[6/6] ================================" -ForegroundColor Cyan
Write-Host "[OK] Services are fully started!" -ForegroundColor Green
Write-Host ""
Write-Host "Available models:" -ForegroundColor White
Write-Host "  [1] deepseek-v4      - DeepSeek Chat" -ForegroundColor Gray
Write-Host "  [2] qwen3-coder      - Qwen Coder" -ForegroundColor Gray
Write-Host "  [3] deepseek-v4-pro  - DeepSeek V4 Pro" -ForegroundColor Gray
Write-Host "  [4] deepseek-v4-flash- DeepSeek V4 Flash" -ForegroundColor Gray
Write-Host "  [5] glm-5.1          - GLM-5.1" -ForegroundColor Gray
Write-Host "  [6] glm-4-flash      - GLM-4 Flash" -ForegroundColor Gray
Write-Host ""
Write-Host "Proxy: http://localhost:1234" -ForegroundColor DarkCyan
Write-Host "Backend: http://localhost:1235" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now you can run Codex!" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop (background windows keep running)" -ForegroundColor DarkGray
Write-Host ""

# Keep window open
while ($true) {
    Start-Sleep -Seconds 10
}
