@echo off
title Subir PANCHO a GitHub
cd /d "%~dp0"
echo ======================================================
echo   Subiendo actualizaciones a GitHub...
echo ======================================================
git rm -r --cached .idea 2>nul
git add .
git commit -m "Soporte completo WSGI para PythonAnywhere"
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/hugotechvilla-lgtm/INVENTARIO-PANCHO.git
echo.
echo Conectando con GitHub y subiendo cambios...
git push -u origin main
echo.
echo ======================================================
echo   Todo subido exitosamente a GitHub!
echo ======================================================
pause
