@echo off
rem Quantlab discovery agent: headless Claude Code, weekly (see research\incubator\DISCOVERY_PROMPT.md).
rem Tools are limited: read anything, write only ideas\ and discovery_log.md, run only incubator.py.
cd /d "%~dp0..\.."
echo ==== %date% %time% >> research\incubator\logs\discovery.log
type research\incubator\DISCOVERY_PROMPT.md | "%USERPROFILE%\.local\bin\claude.exe" -p ^
  --allowedTools "Read" "Glob" "Grep" ^
  "Edit(./research/incubator/ideas/**)" "Edit(//c/quantlab/research/incubator/ideas/**)" ^
  "Edit(./research/incubator/discovery_log.md)" "Edit(//c/quantlab/research/incubator/discovery_log.md)" ^
  "Bash(.venv/Scripts/python.exe research/incubator/incubator.py:*)" "PowerShell(.venv\Scripts\python.exe research\incubator\incubator.py:*)" ^
  --disallowedTools "WebFetch" "WebSearch" "Agent" ^
  >> research\incubator\logs\discovery.log 2>&1
.venv\Scripts\python.exe research\incubator\incubator.py report >> research\incubator\logs\discovery.log 2>&1
