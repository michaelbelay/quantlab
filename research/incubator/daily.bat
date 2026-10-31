@echo off
rem Quantlab incubator: daily forward evaluation + report (see research\incubator\INCUBATOR.md)
cd /d "%~dp0..\.."
echo ==== %date% %time% >> research\incubator\logs\daily.log
.venv\Scripts\python.exe research\incubator\incubator.py evaluate >> research\incubator\logs\daily.log 2>&1
.venv\Scripts\python.exe research\incubator\incubator.py report >> research\incubator\logs\daily.log 2>&1
