@echo off
title Codex Proxy Launcher
cd /d "D:\maozhua\Codex"

echo ========================================
echo   Codex 国产模型代理 - 简单版
echo ========================================
echo.

echo [1] 从系统环境变量加载... OK

:: 停止旧进程
echo.
echo [2] 停止旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1235"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":1234"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 >nul
echo   OK

:: 启动 LiteLLM
echo.
echo [3] 启动 LiteLLM...
start "LiteLLM" cmd /k "cd /d D:\maozhua\Codex && C:\Users\ThinkBook\AppData\Roaming\Python\Python311\Scripts\litellm.exe --config D:\maozhua\Codex\litellm_config.yaml --port 1235"
echo   OK

:: 等待
echo.
echo [4] 等待启动...
timeout /t 5 >nul

:: 启动代理
echo.
echo [5] 启动代理...
start "Codex-Proxy" cmd /k "cd /d D:\maozhua\Codex && python -m src.server"
echo   OK

:: 等待
echo.
echo [6] 等待就绪...
timeout /t 3 >nul

echo.
echo ========================================
echo   启动完成！
echo.
echo   代理地址: http://localhost:1234
echo   LiteLLM:   http://localhost:1235
echo.
echo   现在可以运行 Codex 了
echo ========================================
echo.
pause
