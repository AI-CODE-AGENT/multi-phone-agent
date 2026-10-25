@echo off
title Android Multi-Agent Farm - Control Center
cd /d "%~dp0\.."

set "PY_EXE=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
if exist "%PY_EXE%" (
    start "" "%PY_EXE%" gui\farm_dashboard.py
) else (
    start "" pythonw gui\farm_dashboard.py
)
