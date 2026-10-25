@echo off
cd /d "%~dp0\.."
echo Starting Android Multi-Agent Farm REST API Server on http://127.0.0.1:8088 ...
python api\server.py 8088
pause
