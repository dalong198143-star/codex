@echo off
title Codex Local Proxy [DEPRECATED - use qidongdaili.bat instead]

echo.
echo +==========================================+
echo |  WARNING: This script is DEPRECATED      |
echo |  Please use: qidongdaili.bat             |
echo +==========================================+
echo.
echo Press Ctrl+C to cancel, or
pause

cd /d "%~dp0"

echo [OK] API Keys loaded from system environment variables

echo.
echo +==========================================+
echo |  Codex Local LLM Proxy [DEPRECATED]       |
echo |  Proxy layer: http://localhost:1234       |
echo |  Backend:     http://localhost:1235       |
echo +==========================================+
echo.
echo Registered models: deepseek-v4 / deepseek-r1 / glm-5.1 / kimi-k2.6 / qwen3-coder
echo.
echo Press Ctrl+C to stop
echo -------------------------------------------

:: Ensure Python Scripts in PATH
set "PATH=%APPDATA%\Python\Python311\Scripts;%PATH%"

:: Start LiteLLM backend (1235)
echo [1/2] Starting LiteLLM backend (port 1235)...
start "LiteLLM-Backend" /MIN litellm --config "%~dp0litellm_config.yaml" --port 1235

:: Wait for LiteLLM
echo [*] Waiting for LiteLLM...
:wait_litellm
timeout /t 1 >nul
curl -s http://127.0.0.1:1235/health >nul 2>&1
if errorlevel 1 goto wait_litellm

:: Start Codex proxy (1234)
echo [2/2] Starting Codex proxy (port 1234)...
start "Codex-Proxy" /MIN python "%~dp0src\server.py"

echo.
echo [OK] Proxy ready! Run Codex with:
echo     codex --oss --local-provider local-deepseek -m deepseek-v4
echo.

pause
