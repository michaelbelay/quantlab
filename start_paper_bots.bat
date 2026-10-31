@echo off
REM quantlab paper bots (no keys, no orders): FlowTrend trader, Switcher, Delisting-short
cd /d %~dp0
start "" .venv\Scripts\pythonw.exe -m trader run paper
start "" .venv\Scripts\pythonw.exe -u research\fresh\switcher_paper\paper.py
start "" .venv\Scripts\pythonw.exe -u research\fresh\delist\paper.py
