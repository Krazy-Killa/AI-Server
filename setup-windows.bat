@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "VENV_DIR=%LOCALAPPDATA%\AI-Server\venv"

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher was not found. Install Python 3.12 and try again.
    exit /b 1
)

py -3.12 -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo Python 3.12 was not found. Install Python 3.12 and try again.
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating isolated environment at "%VENV_DIR%"...
    py -3.12 -m venv "%VENV_DIR%"
    if errorlevel 1 exit /b 1
)

echo Installing backend and Windows DirectML dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%PROJECT_ROOT%ai-backend\requirements-windows.txt"
if errorlevel 1 exit /b 1

echo Installing Discord bot dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%PROJECT_ROOT%ai-discord-bot\requirements-windows.txt"
if errorlevel 1 exit /b 1

echo Checking that ONNX Runtime exposes DirectML...
"%VENV_DIR%\Scripts\python.exe" -c "import onnxruntime as ort; print('ONNX Runtime', ort.__version__); print('Execution providers:', ', '.join(ort.get_available_providers())); assert 'DmlExecutionProvider' in ort.get_available_providers(), 'DirectML execution provider is unavailable'"
if errorlevel 1 (
    echo DirectML provider check failed. Review the GPU driver and ONNX Runtime installation.
    exit /b 1
)

echo Running a DirectML inference smoke test...
"%VENV_DIR%\Scripts\python.exe" "%PROJECT_ROOT%ai-backend\gpu\directml_smoke_test.py"
if errorlevel 1 (
    echo DirectML inference test failed. Review the GPU driver and DirectML compatibility.
    exit /b 1
)

echo.
echo Setup complete. Run run-backend.bat to start the local API.
