@echo off
cd /d "%~dp0"
start "" "http://localhost:5000/health"
echo API aciliyor...
timeout /t 2 /nobreak > nul
start cmd /k "venv\Scripts\python.exe test_api.py"
