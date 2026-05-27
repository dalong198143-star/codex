@echo off

:: GitHub token for gh CLI
set "GITHUB_TOKEN=YOUR_GITHUB_TOKEN_HERE"

title Codex Quick Start

cd /d "D:\maozhua\Codex"

echo API Keys loaded from system environment variables

set "PATH=%APPDATA%\Python\Python311\Scripts;%PATH%"

:: ---- Start proxy chain if not running ----
netstat -ano | findstr ":1235" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [1/2] Starting LiteLLM...
    start "LiteLLM" /min cmd /c "cd /d D:\maozhua\Codex && litellm --config litellm_config.yaml --port 1235"
    echo [*] Waiting...
    :wait_llm
    timeout /t 2 >nul
    curl -s http://127.0.0.1:1235/health >nul 2>&1
    if errorlevel 1 goto wait_llm
    echo [OK] LiteLLM ready
)

netstat -ano | findstr ":1234" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [2/2] Starting SSE Proxy...
    start "CodexProxy" /min cmd /c "cd /d D:\maozhua\Codex && python -m src.server"
    :wait_proxy
    timeout /t 1 >nul
    curl -s http://127.0.0.1:1234/health >nul 2>&1
    if errorlevel 1 goto wait_proxy
    echo [OK] Proxy ready
)

echo.
echo Launching Codex...
codex -C D:\maozhua\Codex -c model="deepseek-v4" -c model_provider="local-deepseek"
pause


