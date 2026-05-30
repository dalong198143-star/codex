@echo off

:: GitHub token for gh CLI
:: set "GITHUB_TOKEN=your_token_here"  # ?????? gh auth login

title Codex Quick Start

cd /d "D:\maozhua\Codex"

echo API Keys loaded from system environment variables

set "PATH=%APPDATA%\Python\Python311\Scripts;%PATH%"

:: Load API keys from .env.bat (if exists)
if exist ".env.bat" call .env.bat
:: Timeout control
set "CODEX_TIMEOUT_TOTAL=300"

:: ---- Start proxy chain if not running ----
netstat -ano | findstr ":1235" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [1/2] Starting LiteLLM...
    start "LiteLLM" /min cmd /c "cd /d D:\maozhua\Codex &&  D:\hermes-tools\python\Python311\Scripts\litellm.exe --config litellm_config.yaml --port 1235 > litellm_stdout.log 2> litellm_stderr.log"
    echo [*] Waiting...
    :wait_llm
    timeout /t 2 >nul
    curl -s -H "Authorization: Bearer %LITELLM_MASTER_KEY%" http://127.0.0.1:1235/health >nul 2>&1
    if errorlevel 1 goto wait_llm
    echo [OK] LiteLLM ready
)

netstat -ano | findstr ":1234" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [2/2] Starting SSE Proxy...
    start "CodexProxy" /min cmd /c "cd /d D:\maozhua\Codex && python -m src.server > nul 2>>proxy_stderr.log"
    :wait_proxy
    timeout /t 1 >nul
    curl -s http://127.0.0.1:1234/health >nul 2>&1
    if errorlevel 1 goto wait_proxy
    echo [OK] Proxy ready
)

:: Ensure Codex uses D:\.codex for data (not C:\.claude)
set "CLAUDE_CODE_HOME=D:\.codex"

echo.
echo Launching Codex...
codex -C D:\maozhua\Codex -c model="deepseek-v4" -c model_provider="local-deepseek"
pause



