@echo off
REM =========================================================================
REM PK Transport - double-click this file once. It installs everything:
REM Python 3.12 (if missing), PKT Data / PKT Train / PKT Analyze, PyTorch (GPU or CPU),
REM ultralytics, opencv-python and the other libraries, then makes a Desktop shortcut and opens the app.
REM Needs an internet connection; the first run takes several minutes. No administrator rights needed.
REM After that, open PK Transport from the Desktop shortcut (or run_pk_transport.bat).
REM =========================================================================
title Installing PK Transport...
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
echo.
echo Press any key to close this window...
pause >nul
