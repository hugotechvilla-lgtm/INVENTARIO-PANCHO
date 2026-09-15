@echo off
title Subir PANCHO a GitHub
cd /d "%~dp0"
echo ======================================================
echo   Subiendo sistema PANCHO a GitHub...
echo ======================================================
git rm -r --cached .idea 2>nul
git add .
git commit -m "Sistema PANCHO v1.0 - Inventario y Cobros"
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/hugotechvilla-lgtm/INVENTARIO-PANCHO.git
echo.
echo Conectando con GitHub y subiendo archivos...
git push -u origin main
echo.
echo ======================================================
echo   Todo subido exitosamente a GitHub!
echo ======================================================
pause
