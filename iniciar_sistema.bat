@echo off
title PANCHO - Sistema de Bebidas y Cobros
cd /d "%~dp0"
echo ======================================================
echo   🍹 INICIANDO PANCHO - SISTEMA DE BEBIDAS Y COBROS...
echo ======================================================
set PORT=5050
start "" "http://localhost:5050/?v=%RANDOM%"
python app.py
pause
