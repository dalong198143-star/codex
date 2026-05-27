@echo off
title Codex Local Proxy
cd /d "%~dp0"

echo API Keys loaded from system environment variables
echo.
echo +==========================================+
echo |  Codex Local LLM Proxy                   |
echo |  Proxy layer: http://localhost:1234       |
echo |  Backend:     http://localhost:1235       |
echo +==========================================+
echo.
echo Registered models: deepseek-v4 / deepseek-v4-pro / deepseek-v4-flash / qwen3-coder / glm-5.1
echo.
echo Press Ctrl+C to stop
echo -------------------------------------------

:: Ensure Python Scripts in PATH
set "PATH=%APPDATA%\Python\Python311\Scripts;%PATH%"

:: Stop existing processes
echo.
echo [1/4] Stopping old processes...
netstat -ano | findstr ":1235" >nul 2>&1 && (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1235"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
)
netstat -ano | findstr ":1234" >nul 2>&1 && (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1234"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
)
timeout /t 2 >nul

:: Start LiteLLM backend (1235)
echo.
echo [2/4] Starting LiteLLM backend (port 1235)...
start "LiteLLM-Backend" /MIN cmd /c "cd /d %~dp0 && litellm --config %~dp0litellm_config.yaml --port 1235"

:: Wait for LiteLLM
echo [*] Waiting for LiteLLM...
:wait_litellm
timeout /t 2 >nul
curl -s http://127.0.0.1:1235/health >nul 2>&1
if errorlevel 1 goto wait_litellm
echo [OK] LiteLLM ready

:: Start Codex translation proxy (1234)
echo.
echo [3/4] Starting Codex proxy (port 1234)...
start "Codex-Proxy" /MIN cmd /c "cd /d %~dp0 && python -m src.server"

:: Wait for proxy
echo [*] Waiting for proxy...
:wait_proxy
timeout /t 1 >nul
curl -s http://127.0.0.1:1234/health >nul 2>&1
if errorlevel 1 goto wait_proxy
echo [OK] Proxy ready

:: Test connection
echo.
echo [4/4] Verifying connection...
curl -s -H "Authorization: Bearer ***" http://127.0.0.1:1234/v1/models >nul 2>&1
if errorlevel 1 (
    echo [WARN] Connection test warning, but services may still be starting
) else (
    echo [OK] Connection verified
)

echo.
echo ===========================================
echo [OK] All services started!
echo.
echo Now run Codex:
echo   codex --oss --local-provider local-deepseek -m deepseek-v4
echo.
echo Or use the desktop shortcut to select a model
echo ===========================================
echo.

pause
