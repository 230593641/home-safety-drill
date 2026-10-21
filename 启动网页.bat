@echo off
chcp 65001 >nul
title Anti-Kidnapping Demo - Local Server
cd /d "%~dp0"

python --version >nul 2>nul
if not errorlevel 1 goto RUNPY

py -3 --version >nul 2>nul
if not errorlevel 1 goto RUNPY3

goto NOPY

:RUNPY
python app.py
goto END

:RUNPY3
py -3 app.py
goto END

:NOPY
echo.
echo   [X] Python not found on this computer.
echo.
echo   1. Install Python 3.9 or newer:
echo        https://www.python.org/downloads/
echo   2. IMPORTANT: check "Add Python to PATH" during installation.
echo   3. Then double-click this file again.
echo.
pause
exit /b 1

:END
echo.
pause
