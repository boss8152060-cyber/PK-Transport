@echo off
rem PK Transport: opens the app. Uses the private environment made by install.bat (.venv) when it exists,
rem else Python 3.12, else the default Python.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
    exit /b 0
)
py -3.12 -V >nul 2>&1
if %errorlevel%==0 (
    py -3.12 main.py
) else (
    py main.py
)
if errorlevel 1 pause
