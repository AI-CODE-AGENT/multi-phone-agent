@echo off
cd /d "%~dp0\.."
echo ===================================================
echo Starting All 4 Android Farm Instances (Headless)...
echo ===================================================
python cli\farm_cli.py start --device all
echo.
python cli\farm_cli.py status
pause
