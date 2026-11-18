# Registers "Quantlab Scalp Scan" (every 5 min at +40 s after the candle close, hidden, catches up after sleep).
# Run once:  pwsh -File C:/quantlab/research/scalp_lab/register_task.ps1
$a = New-ScheduledTaskAction -Execute 'C:\quantlab\.venv\Scripts\pythonw.exe' -Argument '"C:\quantlab\tools\hidden_run.pyw" cmd.exe /c "C:\quantlab\research\scalp_lab\scalp_scan.bat"' -WorkingDirectory 'C:\quantlab'
$t = New-ScheduledTaskTrigger -Once -At ((Get-Date).Date.AddSeconds(40)) -RepetitionInterval (New-TimeSpan -Minutes 5)
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4)
Register-ScheduledTask -TaskName 'Quantlab Scalp Scan' -Action $a -Trigger $t -Settings $s -Force -Description 'Scalp lab: 5m bear-day scalp alerts + paper (research\scalp_lab\SCALP_LAB.md)' | Out-Null
Get-ScheduledTask -TaskName 'Quantlab Scalp Scan' | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
