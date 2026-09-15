@echo off
title PANCHO - Sistema de Bebidas y Cobros
cd /d "%~dp0"
echo ======================================================
echo   Iniciando PANCHO - Sistema de Bebidas y Cobros...
echo ======================================================
start http://localhost:5000
python app.py
pause
