@echo off
REM quantlab trader, PAPER mode (no keys, no real orders). Log: data\trader\paper.log
cd /d %~dp0
start "" .venv\Scripts\pythonw.exe -m trader run paper
