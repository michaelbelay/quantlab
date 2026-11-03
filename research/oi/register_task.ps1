# Registers the daily scheduled task "Quantlab OI Collector" (09:00, runs hidden, catches up after sleep).
# Run once:  pwsh -File C:\quantlab\research\oi\register_task.ps1
$a = New-ScheduledTaskAction -Execute 'C:\quantlab\.venv\Scripts\pythonw.exe' -Argument '"C:\quantlab\tools\hidden_run.pyw" cmd.exe /c "C:\quantlab\research\oi\oi_daily.bat"' -WorkingDirectory 'C:\quantlab'
$t = New-ScheduledTaskTrigger -Daily -At '09:00'
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName 'Quantlab OI Collector' -Action $a -Trigger $t -Settings $s -Force -Description 'Daily open interest update: data\market\oi (research\oi\oi_collector.py)' | Out-Null
Get-ScheduledTask -TaskName 'Quantlab OI Collector' | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
