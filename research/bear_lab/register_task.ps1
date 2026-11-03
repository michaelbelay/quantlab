# Registers the daily scheduled task "Quantlab Bear Lab Daily" (09:30, hidden, catches up after sleep).
# Run once:  pwsh -File C:/quantlab/research/bear_lab/register_task.ps1
$a = New-ScheduledTaskAction -Execute 'C:\quantlab\.venv\Scripts\pythonw.exe' -Argument '"C:\quantlab\tools\hidden_run.pyw" cmd.exe /c "C:\quantlab\research\bear_lab\bear_daily.bat"' -WorkingDirectory 'C:\quantlab'
$t = New-ScheduledTaskTrigger -Daily -At '09:30'
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName 'Quantlab Bear Lab Daily' -Action $a -Trigger $t -Settings $s -Force -Description 'Bear lab: OI update, paper evaluation, discovery agent, report (research\bear_lab\BEAR_LAB.md)' | Out-Null
Get-ScheduledTask -TaskName 'Quantlab Bear Lab Daily' | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
