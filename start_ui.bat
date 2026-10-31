@echo off
REM Quantlab terminal UI on http://localhost:8500 - server runs hidden, log in data\ui_server.log
cd /d %~dp0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8500 " ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
start "" .venv\Scripts\pythonw.exe ui\launch_hidden.pyw
timeout /t 3 /nobreak >nul
start "" http://localhost:8500
