@echo off
title PANCHO - Sistema Local Offline (Sin Internet)
cd /d "%~dp0"
echo ======================================================
echo   🍹 INICIANDO PANCHO EN MODO LOCAL (OFFLINE)...
echo ======================================================
set PORT=5050
start "" "http://localhost:5050/?v=%RANDOM%"
python app.py
pause
