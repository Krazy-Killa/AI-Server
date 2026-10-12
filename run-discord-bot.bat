@echo off
setlocal
cd /d "%~dp0ai-discord-bot"

set "PYTHON=%LOCALAPPDATA%\AI-Server\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Testing environment not found. Run setup-windows.bat first.
    exit /b 1
)

"%PYTHON%" bot.py
