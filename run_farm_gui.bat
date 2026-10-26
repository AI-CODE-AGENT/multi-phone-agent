@echo off
title AMAF v19.0 Studio (125 Subagents - 70 MCP Tools - 25 OS - Dual-Theme - 8 Website UI Presets - 7-FW Codegen)
cd /d "D:\Project\multi-phone-agent"

set "PY_EXE=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
if exist "%PY_EXE%" (
    start "" "%PY_EXE%" gui\farm_dashboard.py
) else (
    start "" pythonw gui\farm_dashboard.py
)
