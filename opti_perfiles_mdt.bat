@echo off
setlocal

if "%~1"=="" (
    echo Arrastra un archivo HTML sobre este archivo .bat para ejecutarlo.
    pause
    exit /b 1
)

set "HTML_FILE=%~f1"
if not exist "%HTML_FILE%" (
    echo No se encuentra el archivo "%HTML_FILE%".
    pause
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
call :find_python
if not defined PYTHON_CMD (
    echo No se encontro una instalacion de Python accesible.
    echo Instale Python 3 e intente nuevamente.
    pause
    exit /b 1
)

for %%I in ("%HTML_FILE%") do set "OUTPUT_DIR=%%~dpI" && set "OUTPUT_NAME=%%~nI"
set "CSV_FILE=%OUTPUT_DIR%%OUTPUT_NAME%.csv"

pushd "%SCRIPT_DIR%"
"%PYTHON_CMD%" "%SCRIPT_DIR%opti_perfiles_mdt.py" "%HTML_FILE%" "%CSV_FILE%"
popd

if errorlevel 1 (
    echo Hubo un error al ejecutar el script.
) else (
    echo Archivo generado: "%CSV_FILE%"
)

pause
exit /b 0

:find_python
for %%P in (py python python3) do (
    where %%P >nul 2>nul && set "PYTHON_CMD=%%P" && goto :eof
)
exit /b 0
