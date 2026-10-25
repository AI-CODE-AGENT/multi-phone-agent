@echo off
title Android Multi-Agent Farm - Autonomous Agile Dev-QA Pipeline
cd /d "%~dp0\.."
python cli\farm_cli.py pipeline
pause
