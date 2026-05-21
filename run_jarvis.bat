@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [JARVIS] Virtual environment not found at .venv
  echo [JARVIS] Run setup first:
  echo     python setup_jarvis.py
  pause
  exit /b 1
)

echo [JARVIS] Launching...
".venv\Scripts\python.exe" jarvis.py
endlocal
