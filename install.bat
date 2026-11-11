@echo off
title ED:Event2Led - Installazione
cd /d "%~dp0"
echo.
echo  ============================================================
echo   ED:Event2Led - Installazione dipendenze
echo  ============================================================
echo.

REM ── Verifica Python embedded ─────────────────────────────────────────────────
if not exist "python\python.exe" (
    echo [ERRORE] Cartella python\ non trovata.
    echo Assicurati di aver estratto correttamente il pacchetto.
    echo.
    pause
    exit /b 1
)

echo [OK] Python embedded trovato.

REM ── Abilita import site nel ._pth (richiesto da pip) ────────────────────────
echo [..] Configurazione Python embedded...
powershell -NoProfile -Command ^
    "$f = Get-ChildItem 'python' -Filter '*.pth' | Select-Object -First 1; ^
     if ($f) { ^
         $c = Get-Content $f.FullName; ^
         $c = $c -replace '^#import site', 'import site'; ^
         Set-Content $f.FullName $c; ^
         Write-Host '[OK] File .pth aggiornato:' $f.Name ^
     } else { Write-Host '[WARN] File .pth non trovato' }"

REM ── Bootstrap pip ────────────────────────────────────────────────────────────
if not exist "python\Lib\site-packages\pip" (
    echo [..] Installazione pip...
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' ^
         -OutFile 'python\get-pip.py' -UseBasicParsing"
    if %errorlevel% neq 0 (
        echo [ERRORE] Download get-pip.py fallito. Verifica la connessione internet.
        pause
        exit /b 1
    )
    python\python.exe python\get-pip.py --no-warn-script-location
    del /q python\get-pip.py
) else (
    echo [OK] pip gia' presente.
)

REM ── Installazione dipendenze ─────────────────────────────────────────────────
echo [..] Installazione dipendenze (watchdog, eel)...
python\python.exe -m pip install -r requirements.txt ^
    --no-warn-script-location --quiet

if %errorlevel% neq 0 (
    echo [ERRORE] Installazione dipendenze fallita.
    echo Verifica la connessione internet e riprova.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   [OK] Installazione completata!
echo.
echo   Avvia l'applicazione con:  start.bat
echo   (Assicurati che OpenRGB sia in esecuzione con SDK abilitato)
echo  ============================================================
echo.
pause
