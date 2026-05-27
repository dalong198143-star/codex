# 简单测试脚本 - 直接测试 DeepSeek API

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   DeepSeek API 测试" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 加载环境变量
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 从 .env.bat 加载 API Key
Write-Host "[1/3] 加载 API Key..." -ForegroundColor Yellow
if (Test-Path ".env.bat") {
    Get-Content ".env.bat" | ForEach-Object {
        if ($_ -match "^set\s+([A-Z0-9_]+)=(.*)$") {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value)
            if ($name -eq "DEEPSEEK_API_KEY") {
                Write-Host "  [OK] $name 已加载 ($($value.Substring(0,10))...)" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "[ERROR] 未找到 .env.bat" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

# 测试直接调用 DeepSeek API
Write-Host ""
Write-Host "[2/3] 测试 DeepSeek API..." -ForegroundColor Yellow
$APIKey = $env:DEEPSEEK_API_KEY

$Headers = @{
    "Authorization" = "Bearer $APIKey"
    "Content-Type"  = "application/json"
}

$Body = @{
    model    = "deepseek-v4"
    messages = @(
        @{ role = "user"; content = "你好，请介绍下自己" }
    )
    stream   = $false
} | ConvertTo-Json

try {
    $Response = Invoke-RestMethod -Uri "https://api.deepseek.com/v1/chat/completions" -Headers $Headers -Method Post -Body $Body -TimeoutSec 30
    Write-Host ""
    Write-Host "[OK] API 调用成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "模型回复:" -ForegroundColor Cyan
    Write-Host $Response.choices[0].message.content -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "[ERROR] API 调用失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    $_.ErrorDetails | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

Write-Host "[3/3] ================================" -ForegroundColor Cyan
Write-Host "[√] 测试完成！API 工作正常。" -ForegroundColor Green
Write-Host ""
Write-Host "如果这个测试成功，说明 DeepSeek API 是好的。" -ForegroundColor Yellow
Write-Host "问题在于 LiteLLM 没有正确加载环境变量。" -ForegroundColor Yellow
Write-Host ""
Read-Host "按任意键退出"
