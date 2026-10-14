@echo off
setlocal
rem Starts SearXNG inside WSL. Install first with: wsl bash scripts/searxng/install-searxng.sh
wsl.exe --cd "%~dp0scripts\searxng" bash ./run-searxng.sh
endlocal
