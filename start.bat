@echo off
title ED:Event2Led
cd /d "%~dp0"

REM ── Scelta interprete ───────────────────────────────────────────────────────
REM Pacchetto di rilascio: python\ embedded. Repo di sviluppo: venv\.
set "PYEXE="
if exist "python\python.exe" set "PYEXE=python\python.exe"
if not defined PYEXE if exist "venv\Scripts\python.exe" set "PYEXE=venv\Scripts\python.exe"
if not defined PYEXE (
    echo [ERRORE] Python non trovato: ne' python\ ^(embedded^) ne' venv\.
    echo Pacchetto: esegui prima install.bat
    echo Sviluppo:  python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM ── Avvio applicazione ──────────────────────────────────────────────────────
echo  Avvio ED:Event2Led con %PYEXE% ...
echo  (chiudi questa finestra per terminare)
echo.
"%PYEXE%" src\main.py

REM ── Gestione uscita ─────────────────────────────────────────────────────────
if %errorlevel% neq 0 (
    echo.
    echo [ERRORE] L'applicazione e' terminata con codice: %errorlevel%
    echo Controlla il log sopra per dettagli.
    echo.
    pause
)
