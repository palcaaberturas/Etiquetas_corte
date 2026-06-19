@echo off
cd /d "%~dp0"
title Procesador de Cortes MaxCut
echo Ejecutando optimizador de perfiles...
echo.

python opti_perfiles_mdt.py

echo.
echo Proceso finalizado.
pause