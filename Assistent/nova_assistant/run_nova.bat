@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Nova is not installed yet.
  echo Please follow README.md to create .venv and install requirements.txt.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
endlocal