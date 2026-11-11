@echo off
REM ============================================================
REM  ED:Event2Led - Eel Web UI Dev Server
REM  Avvia il backend Python + apre il browser automaticamente.
REM  L'app e' accessibile su: http://localhost:8000
REM ============================================================
cd /d "%~dp0"

echo.
echo  ============================================================
echo   ED:Event2Led - Eel Web UI
echo  ============================================================
echo.

REM --- Verifica virtual environment ---
if not exist "venv\Scripts\python.exe" (
    echo  [ERRORE] Virtual environment non trovato in venv\
    echo.
    echo  Prima installazione - esegui:
    echo    python -m venv venv
    echo    venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM --- Verifica porta 8000 ---
set PORT_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>NUL') do (
    set PORT_PID=%%a
)

if defined PORT_PID (
    echo  [WARN] Porta 8000 gia' occupata da processo PID: %PORT_PID%
    echo.
    choice /C SN /M "Vuoi terminare il processo esistente e continuare? (S=Si, N=No)"
    if errorlevel 2 (
        echo.
        echo  [INFO] Avvio annullato dall'utente
        echo.
        pause
        exit /b 0
    )
    echo.
    echo  [INFO] Terminazione processo PID %PORT_PID%...
    taskkill /F /PID %PORT_PID% >NUL 2>&1
    if %errorlevel%==0 (
        echo  [OK] Processo terminato con successo
        echo  [INFO] Attendo 2 secondi prima di riavviare...
        timeout /t 2 /nobreak >NUL
    ) else (
        echo  [ERRORE] Impossibile terminare il processo (richiede privilegi admin?)
        echo.
        pause
        exit /b 1
    )
    echo.
)

REM --- Verifica OpenRGB (opzionale) ---
tasklist /FI "IMAGENAME eq OpenRGB.exe" 2>NUL | find /I "OpenRGB.exe" >NUL 2>&1
if %errorlevel%==0 (
    echo  [OK] OpenRGB in esecuzione
) else (
    echo  [WARN] OpenRGB non rilevato - hardware RGB disabilitato
)

echo.
echo  [INFO] Avvio server su http://localhost:8000
echo  [INFO] Il browser si aprira' appena il server e' pronto...
echo  [INFO] Premi Ctrl+C per fermare il server
echo  --------------------------------------------------------
echo.

REM Avvia il server Eel (bloccante - l'output rimane visibile in questa console)
REM Il browser viene aperto da Python con webbrowser.open() appena eel.start() ritorna,
REM cosi' e' garantito che il server sia gia' in ascolto quando il browser si connette.
"venv\Scripts\python.exe" src\main.py

REM --- Gestione uscita ---
set EXIT_CODE=%errorlevel%
echo.
echo  --------------------------------------------------------
if %EXIT_CODE% neq 0 (
    echo  [ERRORE] Server terminato con codice: %EXIT_CODE%
    echo.
    pause
) else (
    echo  [OK] Server chiuso correttamente.
)
