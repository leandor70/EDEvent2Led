@echo off
setlocal

cd /d "%~dp0..\.."

:: Attiva il venv del progetto se esiste
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [Ambilight POC] Nessun venv trovato - uso Python di sistema
)

:: Dipendenze
echo [Ambilight POC] Verifica dipendenze...
python -c "import mss"             2>nul || python -m pip install mss             -q
python -c "import numpy"           2>nul || python -m pip install numpy           -q
python -c "import cv2"             2>nul || python -m pip install opencv-python   -q
python -c "import dxcam"           2>nul || python -m pip install dxcam           -q
python -c "import eel"             2>nul || python -m pip install eel             -q
python -c "import windows_capture" 2>nul || python -m pip install windows-capture -q
echo [Ambilight POC] Dipendenze OK

:: Se sono stati passati argomenti, avvia direttamente (uso da CLI)
if not "%~1"=="" (
    echo [Ambilight POC] Avvio con: %*
    python tools/poc_ambilight/ambilight_poc.py %*
    goto :fine
)

:: Menu rapido
echo.
echo ============================================
echo   ED:Event2Led - Ambilight POC  (UI web)
echo ============================================
echo.
echo   Capturer: scegli in base all'uso
echo.
echo   1. Avvia  (auto: WGC/DXGI automatico)
echo   2. Avvia  (auto + autostart loop)
echo.
echo   [Forzati - solo se l'auto non funziona bene]
echo   3. Avvia  (forza WGC - Chrome/browser)
echo   4. Avvia  (forza DXGI - exclusive fullscreen)
echo.
echo   5. Avvia  (preview only, nessun LED)
echo   6. Esci
echo.
set /p "SCELTA=Scelta [1-6]: "

if "%SCELTA%"=="1" set "ARGS=--capturer auto"
if "%SCELTA%"=="2" set "ARGS=--capturer auto --autostart"
if "%SCELTA%"=="3" set "ARGS=--capturer wgc"
if "%SCELTA%"=="4" set "ARGS=--capturer dxcam"
if "%SCELTA%"=="5" set "ARGS=--preview"
if "%SCELTA%"=="6" goto :fine

echo.
echo [Ambilight POC] Apri http://localhost:8765 nel browser
echo   Ctrl+C per uscire
echo.
python tools/poc_ambilight/ambilight_poc.py %ARGS%

:fine
echo.
pause
