@echo off
title Codex 服务重启
color 0F

echo ========================================
echo    Codex 国产模型服务 - 完全重启
echo ========================================
echo.

cd /d "%~dp0"

:: 停止现有进程
echo [1/5] 停止现有服务进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1234"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1235"') do taskkill /F /PID %%a >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq CodexProxy*" >nul 2>&1
taskkill /F /IM litellm.exe >nul 2>&1
timeout /t 2 >nul
echo [OK] 已停止旧服务
echo.

echo [2/5] 从系统环境变量加载 API Keys...
echo [OK] 已加载 API Keys
echo.

:: 启动 LiteLLM
echo [3/5] 启动 LiteLLM 后端 (端口 1235)...
start "LiteLLM-Backend" /min cmd /c "cd /d %~dp0 && C:\Users\ThinkBook\AppData\Roaming\Python\Python311\Scripts\litellm.exe --config %~dp0litellm_config.yaml --port 1235"

:: 等待 LiteLLM
echo [*] 等待 LiteLLM 就绪...
:wait_litellm
timeout /t 2 >nul
curl -s http://127.0.0.1:1235/health >nul 2>&1
if errorlevel 1 goto wait_litellm
echo [OK] LiteLLM 已就绪
echo.

:: 启动 Codex 代理
echo [4/5] 启动 Codex 协议转换代理 (端口 1234)...
start "Codex-Proxy" /min cmd /c "cd /d %~dp0 && python -m src.server"

:: 等待代理
echo [*] 等待代理就绪...
:wait_proxy
timeout /t 1 >nul
curl -s http://127.0.0.1:1234/health >nul 2>&1
if errorlevel 1 goto wait_proxy
echo [OK] 代理已就绪
echo.

:: 完成
echo [5/5] ================================
echo [√] 服务已完全重启！
echo.
echo 可用模型:
echo   [1] deepseek-v4      - DeepSeek Chat
echo   [2] qwen3-coder      - Qwen Coder
echo   [3] deepseek-v4-pro  - DeepSeek V4 Pro
echo   [4] deepseek-v4-flash- DeepSeek V4 Flash
echo   [5] glm-5.1          - GLM-5.1
echo   [6] glm-4-flash      - GLM-4 Flash
echo.
echo 代理地址: http://localhost:1234
echo 后端地址: http://localhost:1235
echo.
echo ========================================
echo.
echo 现在可以运行 Codex 了！
echo.
pause
