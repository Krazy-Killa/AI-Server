@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%LOCALAPPDATA%\AI-Server\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Testing environment not found. Run setup-windows.bat first.
    exit /b 1
)

"%PYTHON%" -m http.server 8001 --bind 127.0.0.1
