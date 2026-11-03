@echo off
rem Quantlab bear lab: daily OI update, paper evaluation, discovery agent, report (see research\bear_lab\BEAR_LAB.md)
cd /d "%~dp0..\.."
echo ==== %date% %time% >> research\bear_lab\logs\daily.log
.venv\Scripts\python.exe research\oi\oi_collector.py update >> research\oi\logs\oi.log 2>&1
.venv\Scripts\python.exe research\bear_lab\bear_lab.py evaluate >> research\bear_lab\logs\daily.log 2>&1
rem queued 2026-11-02: passed its screen when the day's 3 slots were full; a no-op once it is in the lab
.venv\Scripts\python.exe research\bear_lab\bear_lab.py add research\bear_lab\ideas\cdeep_funding_persist.py --source "main session 2026-11-02 round 6 (queued)" >> research\bear_lab\logs\daily.log 2>&1
type research\bear_lab\BEAR_DISCOVERY_PROMPT.md | "%USERPROFILE%\.local\bin\claude.exe" -p ^
  --allowedTools "Read" "Glob" "Grep" ^
  "Edit(./research/bear_lab/ideas/**)" "Edit(//c/quantlab/research/bear_lab/ideas/**)" ^
  "Edit(./research/bear_lab/discovery_log.md)" "Edit(//c/quantlab/research/bear_lab/discovery_log.md)" ^
  "Bash(.venv/Scripts/python.exe research/bear_lab/bear_lab.py:*)" "PowerShell(.venv\Scripts\python.exe research\bear_lab\bear_lab.py:*)" ^
  --disallowedTools "WebFetch" "WebSearch" "Agent" ^
  >> research\bear_lab\logs\daily.log 2>&1
.venv\Scripts\python.exe research\bear_lab\bear_lab.py report >> research\bear_lab\logs\daily.log 2>&1
