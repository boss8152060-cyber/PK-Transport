@echo off
rem PK Transport: starts the launcher (uses Python 3.12 when installed, else the default Python). Needs only the standard library.
cd /d "%~dp0"
py -3.12 -V >nul 2>&1
if %errorlevel%==0 (
    py -3.12 main.py
) else (
    py main.py
)
if errorlevel 1 pause
