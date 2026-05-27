@echo off
title Direct Test
cd /d "%~dp0"
echo ========================================
echo   Direct LiteLLM Test
echo ========================================
echo.

echo Environment loaded from system env vars
echo.

:: Create a test script
echo Testing with env vars...
echo.

:: Create and run a direct test
(
echo import os
echo import sys
echo from litellm import completion
echo.
echo print^("=== Environment Variables ==="^)
echo print^("DEEPSEEK_API_KEY set:", len(os.getenv^('DEEPSEEK_API_KEY',''^)^)^>0^)
echo print^("API key preview:", os.getenv^('DEEPSEEK_API_KEY',''^)^[:20]^)
echo print^()
echo.
echo try:
echo     response = completion^(
echo         model="deepseek/deepseek-v4",
echo         messages=[{"role": "user", "content": "Hello!"}],
echo         api_key=os.getenv^('DEEPSEEK_API_KEY'^),
echo         temperature=0.1
echo     ^)
echo     print^("=== Success! ==="^)
echo     print^(response.choices[0].message.content^)
echo except Exception as e:
echo     print^("=== Error ==="^)
echo     print^(f"Type: {type(e).__name__}"^)
echo     print^(f"Message: {str(e)}"^)
echo     import traceback
echo     traceback.print_exc^()
) > test_litellm.py

:: Run the test
echo Running test...
python test_litellm.py
echo.
echo Done.
pause
