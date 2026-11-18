@echo off
REM quantlab watchdog: Windows runs tools\watchdog.py every 5 minutes (also on battery, also after a reboot once you
REM are logged in). It restarts the paper bots when they are not running. Remove: schtasks /Delete /TN "quantlab watchdog" /F
REM Switch off without removing: create data\watchdog_off.txt
cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "$a = New-ScheduledTaskAction -Execute '%~dp0.venv\Scripts\pythonw.exe' -Argument 'tools\watchdog.py' -WorkingDirectory '%~dp0.'; $t = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5); $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4); Register-ScheduledTask -TaskName 'quantlab watchdog' -Action $a -Trigger $t -Settings $s -Force | Out-Null; if ($?) { 'watchdog installed: every 5 minutes' } else { 'NOT installed - see the error above' }"
echo.
echo State right now:
.venv\Scripts\python.exe tools\watchdog.py --check
echo.
pause
