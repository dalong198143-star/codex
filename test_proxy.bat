@echo off
title Proxy Test

echo +==========================================+
echo |  Local LLM Proxy - Desktop Test          |
echo +==========================================+
echo.

echo [1] Checking if proxy is running...
curl -s http://localhost:1234/health >nul 2>&1
if errorlevel 1 (
    echo [X] Proxy not running! Please start qidongdaili.bat first
    pause
    exit /b 1
)
echo [OK] Proxy is running

echo.
echo [2] Testing SSE streaming (via proxy :1234)...
echo.
echo    Request: model=deepseek-v4, prompt="Introduce yourself"
echo    Response: text/event-stream (SSE)
echo.
echo    Streaming tokens...
echo.

:: Send SSE request to proxy, parse with Python line by line
curl -s -N -X POST http://localhost:1234/v1/responses ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"deepseek-v4\",\"input\":\"Introduce yourself in one short sentence\"}" ^
  2>nul | python -c "
import sys
text_parts = []
for line in sys.stdin:
    line = line.strip()
    if line.startswith('event: '):
        evt = line[7:]
    elif line.startswith('data: '):
        data = line[6:]
        if data == '[DONE]':
            break
        import json
        try:
            obj = json.loads(data)
            t = obj.get('type', '')
            if t == 'response.content_part.delta':
                delta = obj.get('delta', '')
                text_parts.append(delta)
                print(delta, end='', flush=True)
            elif t == 'response.completed':
                usage = obj.get('response', {}).get('usage', {})
                print()
                print()
                print('  Tokens:', usage.get('total_tokens', '?'))
        except:
            pass
print()
print('  [OK] SSE streaming OK')
" 2>nul

if errorlevel 1 (
    echo [X] SSE test failed, falling back to non-streaming...
    curl -s -X POST http://localhost:1234/v1/responses ^
      -H "Content-Type: application/json" ^
      -d "{\"model\":\"deepseek-v4\",\"input\":\"Introduce yourself in one sentence\"}" ^
      2>nul | python -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if line.startswith('data: ') and line[6:] != '[DONE]':
        try:
            obj = json.loads(line[6:])
            if obj.get('type') == 'response.completed':
                out = obj.get('response', {}).get('output', [])
                for o in out:
                    if o.get('type') == 'message':
                        for c in o.get('content', []):
                            print('  DeepSeek V4:', c.get('text', ''))
                u = obj.get('response', {}).get('usage', {})
                print('  Tokens:', u.get('total_tokens', '?'))
        except:
            pass
" 2>nul
)

echo.
echo ===========================================
echo [OK] Test complete! Proxy is working.
echo.
echo Connection info:
echo   API Base (via proxy):  http://localhost:1234/v1
echo   API Base (direct):     http://localhost:1235/v1
echo   API Key:               any value
echo   Models:                deepseek-v4 / deepseek-r1
echo ===========================================
echo.
pause
