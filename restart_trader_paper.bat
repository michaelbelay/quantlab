@echo off
REM Stop the paper trader (if it runs) and start it again - needed after a code change in trader\.
REM Open trades are kept: they live in data\trader\paper.sqlite and are picked up at the start.
cd /d %~dp0
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match '-m trader run paper' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; 'stopped pid ' + $_.ProcessId }"
timeout /t 2 /nobreak >nul
start "" .venv\Scripts\pythonw.exe -m trader run paper
echo started - waiting 30 s for the first checks ...
timeout /t 30 /nobreak >nul
.venv\Scripts\python.exe -m trader status paper
echo.
echo Last lines of data\trader\paper.log:
powershell -NoProfile -Command "Get-Content data\trader\paper.log -Tail 6"
pause
