@echo off
title NEXORA Student Hub
cd /d "%~dp0"
echo Starting NEXORA Student Hub...
start http://127.0.0.1:5000
.\.venv\Scripts\python.exe app.py
pause
