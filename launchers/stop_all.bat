@echo off
cd /d "%~dp0\.."
echo ===================================================
echo Stopping All Android Farm Instances...
echo ===================================================
python cli\farm_cli.py stop --device all
echo.
python cli\farm_cli.py status
pause
