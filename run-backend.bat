@echo off
setlocal
cd /d "%~dp0ai-backend"

set "PYTHON=%LOCALAPPDATA%\AI-Server\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Testing environment not found. Run setup-windows.bat first.
    exit /b 1
)

"%PYTHON%" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
