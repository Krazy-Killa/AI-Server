@echo off
setlocal

set "AI_SERVER_DIR=%LOCALAPPDATA%\AI-Server"
set "LLAMA_SERVER=%AI_SERVER_DIR%\build\llama.cpp-vulkan\bin\Release\llama-server.exe"
set "LLAMA_MODEL_NAME=%~1"
if not defined LLAMA_MODEL_NAME set "LLAMA_MODEL_NAME=%AI_SERVER_MODEL%"
if not defined LLAMA_MODEL_NAME set "LLAMA_MODEL_NAME=qwen2.5-1.5b-instruct-q4_k_m.gguf"
set "LLAMA_MODEL=%AI_SERVER_DIR%\models\%LLAMA_MODEL_NAME%"
set "LLAMA_TEMPLATE_ARGS="
if /I "%LLAMA_MODEL_NAME:~0,5%"=="Qwen3" set "LLAMA_TEMPLATE_ARGS=--no-jinja --chat-template chatml"
set "VULKAN_SDK=C:\VulkanSDK\1.4.363.0"
set "PATH=%VULKAN_SDK%\Bin;%PATH%"

if not exist "%LLAMA_SERVER%" (
    echo llama-server.exe was not found at "%LLAMA_SERVER%".
    echo Build llama.cpp with Vulkan support first.
    exit /b 1
)

if not exist "%LLAMA_MODEL%" (
    echo Test model was not found at "%LLAMA_MODEL%".
    echo Choose a GGUF installed in "%AI_SERVER_DIR%\models".
    echo Example: run-llama-server.bat Qwen3-8B-Q4_K_M.gguf
    exit /b 1
)

for %%I in ("%LLAMA_MODEL_NAME%") do set "LLAMA_MODEL_ALIAS=%%~nI"
"%LLAMA_SERVER%" --model "%LLAMA_MODEL%" --host 127.0.0.1 --port 8080 --device Vulkan0 --gpu-layers 99 --ctx-size 4096 %LLAMA_TEMPLATE_ARGS% --alias "%LLAMA_MODEL_ALIAS%"
