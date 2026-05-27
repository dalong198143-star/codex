# Simple API Test

Write-Host "Testing DeepSeek API..." -ForegroundColor Cyan
Write-Host ""

# Load API key
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (Test-Path ".env.bat") {
    Get-Content ".env.bat" | ForEach-Object {
        if ($_ -match "^set\s+([A-Z0-9_]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
        }
    }
}

$APIKey = $env:DEEPSEEK_API_KEY

$Headers = @{
    "Authorization" = "Bearer $APIKey"
    "Content-Type"  = "application/json"
}

$Body = @{
    model    = "deepseek-v4"
    messages = @(@{ role = "user"; content = "Hello!" })
    stream   = $false
} | ConvertTo-Json

try {
    Write-Host "Calling DeepSeek API..." -ForegroundColor Yellow
    $Response = Invoke-RestMethod -Uri "https://api.deepseek.com/v1/chat/completions" -Headers $Headers -Method Post -Body $Body -TimeoutSec 30
    
    Write-Host ""
    Write-Host "OK!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    Write-Host $Response.choices[0].message.content
} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press any key to exit"
