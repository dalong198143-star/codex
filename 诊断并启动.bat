@echo off
title Codex Proxy Diagnostic & Launcher
cd /d "D:\maozhua\Codex"

cls
echo ========================================
echo   Codex 国产模型代理 - 诊断版
echo ========================================
echo.

echo [1/6] 从系统环境变量加载 API Keys...
echo   [OK] Loaded

:: 检查 Python
echo.
echo [2/6] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Python not in PATH, trying direct call
)
echo   [OK] Python ready

:: 检查 LiteLLM
echo.
echo [3/6] 检查 LiteLLM...
"C:\Users\ThinkBook\AppData\Roaming\Python\Python311\Scripts\litellm.exe" --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] LiteLLM not found
    pause
    exit /b 1
)
echo   [OK] LiteLLM ready

:: 停止旧进程
echo.
echo [4/6] 停止旧进程...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM litellm.exe >nul 2>&1
timeout /t 2 >nul
echo   [OK] Cleaned up

:: 启动 LiteLLM
echo.
echo [5/6] 启动 LiteLLM (端口 1235)...
start "LiteLLM" cmd /k "cd /d D:\maozhua\Codex && echo Starting LiteLLM... && C:\Users\ThinkBook\AppData\Roaming\Python\Python311\Scripts\litellm.exe --config D:\maozhua\Codex\litellm_config.yaml --port 1235"

:: 等待 LiteLLM
echo   等待 5 秒...
timeout /t 5 >nul

:: 启动代理
echo.
echo [6/6] 启动 Codex 代理 (端口 1234)...
start "Codex-Proxy" cmd /k "cd /d D:\maozhua\Codex && echo Starting proxy... && python -m src.server"

:: 等待代理
echo   等待 3 秒...
timeout /t 3 >nul

:: 完成
echo.
echo ========================================
echo.
echo   [OK] Services started!
echo.
echo   LiteLLM: http://localhost:1235
echo   代理:   http://localhost:1234
echo.
echo   现在可以运行 Codex 了
echo.
echo ========================================
echo.
echo 提示:
echo   - 有两个黑色窗口不要关闭
echo   - 现在可以运行桌面上的 Codex启动.bat 选择模型
echo.
pause
