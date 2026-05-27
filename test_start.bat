@echo off
cd /d "%~dp0"
echo ========================================
echo Testing LiteLLM with system env vars...
echo ========================================
echo.
echo Starting LiteLLM...
start "LiteLLM-Test" /min cmd /k "cd /d %~dp0 && C:\Users\ThinkBook\AppData\Roaming\Python\Python311\Scripts\litellm.exe --config %~dp0litellm_config.yaml --port 1235"
echo.
echo Waiting 5 seconds...
timeout /t 5
echo.
echo Testing API...
curl -s http://localhost:1235/v1/models -H "Authorization: Bearer sk-litellm-master-2026"
echo.
echo.
echo Done. Check the LiteLLM-Test window for logs.
pause
