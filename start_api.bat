@echo off
title Manga Notificator API
cd /d "%~dp0"
echo ============================================================
echo MANGA NOTIFICATOR API SERVISI BASLATILIYOR...
echo ============================================================
echo.
echo API Adresi: http://localhost:5000
echo.
echo Durdurmak icin CTRL+C basin
echo ============================================================
echo.

venv\Scripts\python.exe api.py

pause
