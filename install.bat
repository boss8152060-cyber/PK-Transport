@echo off
REM =========================================================================
REM PK Transport - double-click this file once. It installs the app: Python 3.12 (if missing), a private
REM environment (.venv), a Desktop shortcut, and opens the app. It is quick (the app needs no big libraries).
REM The modules (PKT Data, PKT Train, PKT Analyze) are chosen and installed inside the app, on its Modules page.
REM To install modules right now:   install.bat -Modules all        (or  -Modules data,train)
REM Needs an internet connection. No administrator rights needed.
REM =========================================================================
title Installing PK Transport...
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
echo.
echo Press any key to close this window...
pause >nul
