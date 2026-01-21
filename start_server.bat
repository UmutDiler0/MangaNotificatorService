@echo off
title Manga Notificator API - Production Server
cd /d "%~dp0"
echo ============================================================
echo MANGA NOTIFICATOR API - PRODUCTION SERVER
echo ============================================================
echo.
echo Bu production-ready server Waitress kullanir
echo API Adresi: http://localhost:5000
echo.
echo Durdurmak icin CTRL+C basin
echo ============================================================
echo.

venv\Scripts\python.exe run_server.py

pause
