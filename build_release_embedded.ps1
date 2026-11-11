#Requires -Version 5.1
<#
.SYNOPSIS
    Crea il pacchetto di distribuzione ED:Event2Led (Python Embedded).

.DESCRIPTION
    1. Scarica Python 3.12 embeddable per Windows x64
    2. Copia src/, web/, config/ puliti
    3. Genera lo zip finale pronto per la distribuzione ai tester

.USAGE
    .\build_release_embedded.ps1
    .\build_release_embedded.ps1 -Version "1.2.4"
    .\build_release_embedded.ps1 -SkipDownload   # riusa python gia' scaricato
    .\build_release_embedded.ps1 -Zip
#>

param(
    [string]$Version        = "",
    [switch]$SkipDownload,
    [switch]$Zip
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Costanti ──────────────────────────────────────────────────────────────────

$PythonVersion  = "3.12.10"
$PythonUrl      = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$ProjectRoot    = $PSScriptRoot

# Versione (default da git)
if (-not $Version) {
    $Version = (git describe --tags --always 2>$null) -replace '^v', ''
    if (-not $Version) { $Version = "dev" }
}

$ReleaseName    = "ED-Event2Led-v$Version-win64-embedded"
$OutDir         = Join-Path $ProjectRoot "dist\$ReleaseName"
$ZipOut         = Join-Path $ProjectRoot "dist\$ReleaseName.zip"

# Cartelle/file da NON includere nella release
$Exclude = @(
    '.git', '.claude', 'venv', '__pycache__',
    'dist', 'testimages', 'da_cancellare',
    'log', 'docs', 'support_files', 'tools',
    'build_release_embedded.ps1', 'build_pyinstaller.ps1',
    '*.pyc', '.obsidian',
    # File extra nella root non necessari per gli utenti
    'node_modules', 'package.json', 'package-lock.json',
    'tailwind.config.js', 'tests', '.pytest_cache',
    'INSTALLATION_PACKAGE', 'INSTALLATION_PACKAGE.zip',
    'build', '.playwright-mcp', '.interface-design',
    '*.md', 'nul', '*.bat',  # i .bat specifici vengono ricreati dallo script
    'test_navigation.html', 'test-tour.js',
    'TODO_NEXT_SESSION.md', 'SESSION_RESUME_*.md', 'QUICK_RESUME_*.md'
)

# ── Helper ────────────────────────────────────────────────────────────────────

function Write-Step([string]$msg) {
    Write-Host "`n[..] $msg" -ForegroundColor Cyan
}
function Write-Ok([string]$msg) {
    Write-Host "[OK] $msg" -ForegroundColor Green
}
function Write-Warn([string]$msg) {
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

# ── Pulizia cartella dist ─────────────────────────────────────────────────────

Write-Step "Pulizia cartella dist/$ReleaseName..."
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item $OutDir -ItemType Directory | Out-Null
if ($Zip -and (Test-Path $ZipOut)) { Remove-Item $ZipOut -Force }
Write-Ok "Pronta: dist/$ReleaseName/"

# ── Download Python embeddable ─────────────────────────────────────────────────

$PythonZip    = Join-Path $ProjectRoot "dist\python-embed.zip"
$PythonOutDir = Join-Path $OutDir "python"

if (-not $SkipDownload) {
    Write-Step "Download Python $PythonVersion embeddable..."
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonZip -UseBasicParsing
    Write-Ok "Scaricato: $PythonUrl"
} else {
    Write-Warn "SkipDownload: reusing existing $PythonZip"
}

Write-Step "Estrazione Python embeddable..."
Expand-Archive $PythonZip $PythonOutDir -Force
Write-Ok "Estratto in python/"

# Abilita import site nel ._pth (necessario per pip)
$pthFile = Get-ChildItem $PythonOutDir -Filter "*._pth" | Select-Object -First 1
if ($pthFile) {
    $content = Get-Content $pthFile.FullName
    $content = $content -replace '^#import site', 'import site'
    Set-Content $pthFile.FullName $content
    Write-Ok "Patchato $($pthFile.Name): import site abilitato"
} else {
    Write-Warn "File .pth non trovato - pip potrebbe non funzionare"
}

# ── Copia sorgenti progetto ────────────────────────────────────────────────────

Write-Step "Copia file progetto..."

# Funzione copia con esclusioni
function Copy-WithExclusions([string]$src, [string]$dst) {
    $items = Get-ChildItem $src | Where-Object {
        $name = $_.Name
        -not ($Exclude | Where-Object { $name -like $_ })
    }
    foreach ($item in $items) {
        $dest = Join-Path $dst $item.Name
        if ($item.PSIsContainer) {
            Copy-Item $item.FullName $dest -Recurse -Force
            # Rimuovi __pycache__ annidati
            Get-ChildItem $dest -Recurse -Directory -Filter "__pycache__" |
                Remove-Item -Recurse -Force
        } else {
            Copy-Item $item.FullName $dest -Force
        }
    }
}

Copy-WithExclusions $ProjectRoot $OutDir

# Rimuovi cartelle dev-only che Copy-Item -Recurse ha copiato in sottodirectory
$devOnlySubdirs = @(
    "web\node_modules",       # Tailwind build tools (non servono a runtime: si usa css/tailwind.min.css)
    "web\.playwright-mcp",    # Playwright test artifacts
    "src\__pycache__"         # Per sicurezza, anche se già filtrati da Copy-WithExclusions
)
foreach ($sub in $devOnlySubdirs) {
    $path = Join-Path $OutDir $sub
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
        Write-Ok "Rimosso (dev-only): $sub"
    }
}

Write-Ok "Sorgenti copiati"

# ── Config pulita per la distribuzione ────────────────────────────────────────

Write-Step "Preparazione config/ per distribuzione..."

$ConfigDist = Join-Path $OutDir "config"

# settings.json: rimuovi journal_directory personale
$settingsPath = Join-Path $ConfigDist "settings.json"
if (Test-Path $settingsPath) {
    $s = Get-Content $settingsPath | ConvertFrom-Json
    $clean = @{
        openrgb_host = if ($s.openrgb_host) { $s.openrgb_host } else { "localhost" }
        openrgb_port = if ($s.openrgb_port) { $s.openrgb_port } else { 6742 }
        language     = if ($s.language)     { $s.language }     else { "en" }
        theme        = if ($s.theme)        { $s.theme }        else { "elite" }
    }
    $clean | ConvertTo-Json | Set-Content $settingsPath
    Write-Ok "settings.json sanificato (rimosso journal_directory)"
}

# keyboard_presets.json: svuota i led_colors
$presetsPath = Join-Path $ConfigDist "keyboard_presets.json"
if (Test-Path $presetsPath) {
    $p = Get-Content $presetsPath | ConvertFrom-Json
    foreach ($presetId in @("1","2","3")) {
        if ($p.presets.$presetId) {
            $p.presets.$presetId.led_colors = @{}
        }
    }
    $p.active_preset = "1"
    $p.lock_keyboard  = $false
    $p | ConvertTo-Json -Depth 10 | Set-Content $presetsPath
    Write-Ok "keyboard_presets.json sanificato (led_colors svuotati)"
}

# event_mappings.json e status_mappings.json: lascia vuoti
@{ version = 2; mappings = @{} } | ConvertTo-Json |
    Set-Content (Join-Path $ConfigDist "event_mappings.json")
@{ version = 1; mappings = @{} } | ConvertTo-Json |
    Set-Content (Join-Path $ConfigDist "status_mappings.json")
Write-Ok "event_mappings e status_mappings azzerati"

# ── Batch files ────────────────────────────────────────────────────────────────

Write-Step "Creazione file batch..."

# install.bat  (single-quoted here-string = letterale, nessuna interpolazione PS)
$installBat = @'
@echo off
title ED:Event2Led - Installazione
cd /d "%~dp0"
echo.
echo  ============================================================
echo   ED:Event2Led - Installazione dipendenze
echo  ============================================================
echo.

REM Verifica Python embedded
if not exist "python\python.exe" (
    echo [ERRORE] Cartella python\ non trovata.
    echo Assicurati di aver estratto correttamente il pacchetto.
    pause
    exit /b 1
)
echo [OK] Python embedded trovato.

REM Crea Lib\site-packages se non esiste
if not exist "python\Lib\site-packages" mkdir "python\Lib\site-packages"
echo [OK] Cartella site-packages pronta.

REM Configura il ._pth
echo [..] Configurazione Python embedded...
powershell -NoProfile -Command "$f = Get-ChildItem 'python' -Filter '*._pth' | Select-Object -First 1; if ($f) { $c = Get-Content $f.FullName; $c = $c -replace '^#import site', 'import site'; if ($c -notcontains 'Lib\site-packages') { $c += 'Lib\site-packages' }; Set-Content $f.FullName $c; Write-Host '[OK] File ._pth aggiornato:' $f.Name } else { Write-Host '[WARN] File ._pth non trovato' }"

REM Installa pip
echo [..] Installazione pip...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'python\get-pip.py' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo [ERRORE] Download get-pip.py fallito.
    pause
    exit /b 1
)
python\python.exe python\get-pip.py --no-warn-script-location --quiet
del /q python\get-pip.py

REM Pre-installa setuptools e wheel
echo [..] Installazione setuptools e wheel...
python\python.exe -m pip install setuptools wheel --no-warn-script-location --quiet
if %errorlevel% neq 0 (
    echo [ERRORE] Installazione setuptools fallita.
    pause
    exit /b 1
)

REM Installa dipendenze
echo [..] Installazione dipendenze...
python\python.exe -m pip install -r requirements.txt --no-warn-script-location --quiet --prefer-binary
if %errorlevel% neq 0 (
    echo [ERRORE] Installazione dipendenze fallita.
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
'@

$installBat | Set-Content (Join-Path $OutDir "install.bat") -Encoding ASCII

# start.bat  (single-quoted here-string = letterale)
$startBat = @'
@echo off
title ED:Event2Led
cd /d "%~dp0"

if not exist "python\python.exe" (
    echo [ERRORE] Python embedded non trovato.
    echo Esegui prima install.bat
    pause
    exit /b 1
)

echo  Avvio ED:Event2Led...
echo  (chiudi questa finestra per terminare)
echo.
python\python.exe src\main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRORE] L'applicazione e' terminata con codice: %errorlevel%
    pause
)
'@

$startBat | Set-Content (Join-Path $OutDir "start.bat") -Encoding ASCII

Write-Ok "File batch creati"

# ── README per i tester ───────────────────────────────────────────────────────

Write-Step "Scrittura README.txt..."
$readme = @"
ED:Event2Led v$Version — Guida rapida per i tester
====================================================

PREREQUISITI
------------
1. Windows 10/11 x64
2. OpenRGB installato e in esecuzione
   - Apri OpenRGB > Settings > Enable SDK Server > Start
   - (default: porta 6742)
3. Elite Dangerous installato (per monitoraggio live)
4. Connessione internet (solo alla prima installazione)

PRIMA INSTALLAZIONE (una sola volta, ~2 minuti)
------------------------------------------------
Doppio click su  install.bat
  - Configura Python e installa le dipendenze automaticamente
  - Non richiede Python installato sul sistema

AVVIO NORMALE
--------------
Doppio click su  start.bat
  -> L'app apre il browser su http://localhost:8000

NOTE
----
- Se la porta 8000 e' occupata: modifica config\settings.json
  aggiungendo  "web_port": 8081  (o altra porta libera)
- I tuoi effetti e mappature vengono salvati in config\
- Per segnalare un bug: includi il contenuto della console

VERSIONE: $Version
DATA BUILD: $(Get-Date -Format "yyyy-MM-dd")
"@

$readme | Set-Content (Join-Path $OutDir "README.txt") -Encoding UTF8
Write-Ok "README.txt creato"

# ── Creazione zip ──────────────────────────────────────────────────────────────

if ($Zip) {
    Write-Step "Creazione zip: $ReleaseName.zip ..."
    Compress-Archive -Path $OutDir -DestinationPath $ZipOut -Force
    $sizeMB = [math]::Round((Get-Item $ZipOut).Length / 1MB, 1)
    Write-Ok "Zip creato: dist\$ReleaseName.zip ($sizeMB MB)"
}

# ── Riepilogo ──────────────────────────────────────────────────────────────────

$sizeMB = [math]::Round((Get-ChildItem $OutDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)

Write-Host "`n============================================================" -ForegroundColor White
Write-Host "  Build completata: ED-Event2Led v$Version" -ForegroundColor Green
Write-Host "  Tipo: Python Embedded" -ForegroundColor White
Write-Host "  Output: dist\$ReleaseName\ ($sizeMB MB)" -ForegroundColor Green
if ($Zip) {
    Write-Host "  ZIP: dist\$ReleaseName.zip" -ForegroundColor Green
}
Write-Host "============================================================`n" -ForegroundColor White
