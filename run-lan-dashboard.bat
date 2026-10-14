@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%LOCALAPPDATA%\AI-Server\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Testing environment not found. Run setup-windows.bat first.
    exit /b 1
)

"%PYTHON%" lan_dashboard_server.py
