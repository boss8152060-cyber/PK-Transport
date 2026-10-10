@echo off
rem Start PK Studio with the Python that has CUDA (3.12); the default Python only when 3.12 is not installed (a crash of 3.12 must not start a second copy).
cd /d "%~dp0"
py -3.12 -V >nul 2>&1
if %errorlevel%==0 (
    py -3.12 PKStudio.py
) else (
    py PKStudio.py
)
pause
