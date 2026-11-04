@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%LOCALAPPDATA%\AI-Server\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Testing environment not found. Run setup-windows.bat first.
    exit /b 1
)

"%PYTHON%" ai-backend\dashboard_server.py --bind 127.0.0.1 --port 8001 --directory "%~dp0."
