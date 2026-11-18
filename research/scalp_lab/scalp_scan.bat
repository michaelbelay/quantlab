@echo off
rem Quantlab scalp lab: 5m candles, live scalp alerts, paper, verdicts (see research\scalp_lab\SCALP_LAB.md)
cd /d "%~dp0..\.."
.venv\Scripts\python.exe research\scalp_lab\scalp_lab.py scan >> research\scalp_lab\logs\scan.log 2>&1
