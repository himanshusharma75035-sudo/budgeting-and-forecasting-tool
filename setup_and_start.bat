@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
title OpenFPA - Setup ^& Start

echo ============================================================
echo   OpenFPA  -  one-time setup, then start backend + frontend
echo ============================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

echo [1/4] Backend virtual environment
cd /d "%ROOT%backend"
if not exist ".venv\Scripts\python.exe" (
    echo       creating .venv ...
    %PY% -m venv .venv
    if errorlevel 1 goto :fail
)

echo [2/4] Backend dependencies
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -e ".[dev]"
if errorlevel 1 goto :fail

echo [3/4] Demo database
if not exist "data\openfpa.db" (
    echo       seeding demo data ...
    ".venv\Scripts\python.exe" scripts\seed.py
    if errorlevel 1 goto :fail
)

echo [4/4] Frontend dependencies
cd /d "%ROOT%frontend"
if not exist "node_modules" (
    echo       npm install ...
    call npm install
    if errorlevel 1 goto :fail
)

cd /d "%ROOT%"
echo.
echo Setup complete - launching servers...
echo.
call "%ROOT%start.bat"
goto :eof

:fail
echo.
echo *** Setup failed - see the messages above. ***
echo     Make sure Python 3.11+ and Node.js 20+ are installed and on PATH.
echo.
pause
exit /b 1
