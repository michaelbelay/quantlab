@echo off
rem Quantlab OI collector: daily update of data\market\oi (see research\oi\oi_collector.py)
cd /d "%~dp0..\.."
.venv\Scripts\python.exe research\oi\oi_collector.py update >> research\oi\logs\oi.log 2>&1
