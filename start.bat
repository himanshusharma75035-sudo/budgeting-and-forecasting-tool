@echo off
setlocal
set "ROOT=%~dp0"

if not exist "%ROOT%backend\.venv\Scripts\python.exe" goto :nosetup
if not exist "%ROOT%frontend\node_modules" goto :nosetup

echo Starting backend  (http://127.0.0.1:8000  -  API docs at /docs) ...
start "OpenFPA Backend" /d "%ROOT%backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app"

echo Starting frontend (http://127.0.0.1:5173) ...
start "OpenFPA Frontend" /d "%ROOT%frontend" cmd /k "npm run dev"

echo.
echo Two terminal windows opened. Close them (or press Ctrl+C inside) to stop the servers.
timeout /t 6 >nul
goto :eof

:nosetup
echo.
echo Project is not set up yet.
echo Please run  setup_and_start.bat  first (it installs dependencies and seeds the database).
echo.
pause
exit /b 1
