#Requires -Version 5.1
<#
.SYNOPSIS
    Release automation: build dell'artefatto + (opzionale) pubblicazione su GitHub Releases.

.DESCRIPTION
    Modello di distribuzione: SORGENTE PRIVATO + ARTEFATTO PUBBLICO.
      - Il codice resta nel repo privato (origin = leandor70/ED-event2led).
      - L'artefatto (zip PyInstaller, senza sorgenti) viene distribuito come
        ASSET di una GitHub Release sul repo pubblico (leandor70/EDEvent2Led),
        NON committato dentro git.

    Passi:
      1. Commit delle modifiche sorgente pendenti (se presenti) — solo locale
      2. Build Python Embedded  (dist/ED-Event2Led-v*-win64-embedded.zip)   [opzionale]
      3. Build PyInstaller       (dist/ED-Event2Led-v*-win64-PyInstaller.zip)
      4. Aggiorna INSTALLATION_PACKAGE/ e INSTALLATION_PACKAGE.zip (artefatto locale, gitignored)
      5. Genera checksum SHA256 -> INSTALLATION_PACKAGE.zip.sha256
      6. Push dei SOLI commit sorgente su origin/master (lo zip e' gitignored, non viene incluso)
      7. [-Publish] Crea la GitHub Release sul repo pubblico con zip + checksum come asset

    NOTA: lo zip NON viene piu' committato in nessun repo. Vive solo come
    asset di release e come file locale ignorato da git.

.USAGE
    .\release.ps1                       # build artefatto + checksum, push sorgenti (NIENTE release pubblica)
    .\release.ps1 -Message "fix: ..."   # messaggio commit sorgenti
    .\release.ps1 -SkipDownload         # riusa python-embed.zip gia' scaricato
    .\release.ps1 -SkipEmbedded         # salta build embedded (artefatto release = PyInstaller)
    .\release.ps1 -Publish              # crea anche la GitHub Release sul repo pubblico
    .\release.ps1 -DryRun               # mostra cosa farebbe senza eseguire

.PARAMETER Message
    Messaggio per il commit dei sorgenti. Default: autogenerato.

.PARAMETER SkipDownload
    Riusa dist/python-embed.zip esistente invece di scaricarlo.

.PARAMETER SkipEmbedded
    Salta il build Python Embedded (l'artefatto di release e' la build PyInstaller).

.PARAMETER SkipPyInstaller
    Salta il build PyInstaller. ATTENZIONE: senza PyInstaller non si puo'
    rigenerare INSTALLATION_PACKAGE.zip.

.PARAMETER Publish
    Crea la GitHub Release sul repo pubblico (gh release create).
    SPENTO di default: senza questo flag lo script si ferma dopo build + checksum.

.PARAMETER DryRun
    Mostra i passi senza eseguire commit, build, push o release.
#>

param(
    [string]$Message         = "",
    [switch]$SkipDownload,
    [switch]$SkipEmbedded,
    [switch]$SkipPyInstaller,
    [switch]$Publish,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot

# Repo pubblico di distribuzione (solo Releases, niente sorgenti)
$PublicRepo = "leandor70/EDEvent2Led"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step([string]$msg) {
    Write-Host "`n======================================" -ForegroundColor DarkCyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor DarkCyan
}
function Write-Ok([string]$msg)   { Write-Host "[OK] $msg"   -ForegroundColor Green  }
function Write-Warn([string]$msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red   }
function Write-Dry([string]$msg)  { Write-Host "[DRY] $msg"  -ForegroundColor Magenta}

function Invoke-Step([string]$label, [scriptblock]$block) {
    if ($DryRun) {
        Write-Dry $label
    } else {
        & $block
    }
}

# ── Preflight checks ──────────────────────────────────────────────────────────

Write-Step "Preflight checks"

Push-Location $ProjectRoot

$gitStatus      = @(git status --porcelain 2>$null)
$trackedChanges = @($gitStatus | Where-Object { $_ -match '^ M|^M |^MM|^MD|^AM|^AD' })

Write-Ok "Git remoto (privato): $(git remote get-url origin 2>$null)"
Write-Ok "Repo pubblico (release): $PublicRepo"
Write-Ok "Branch corrente: $(git branch --show-current)"

$gitVersion = (git describe --tags --always 2>$null) -replace '^v', ''
Write-Ok "Versione rilevata: v$gitVersion"

if ($trackedChanges) {
    Write-Warn "Modifiche sorgente da committare:"
    $trackedChanges | ForEach-Object { Write-Host "   $_" -ForegroundColor Yellow }
} else {
    Write-Ok "Nessuna modifica sorgente pendente"
}

if ($DryRun) {
    Write-Host "`n  [DRY RUN] Nessuna operazione verra' eseguita.`n" -ForegroundColor Magenta
}

# ── Step 1: Commit sorgenti (se ci sono modifiche) ───────────────────────────

if ($trackedChanges) {
    Write-Step "1/7  Commit sorgenti"

    if (-not $Message) {
        $fileCount = ($trackedChanges).Count
        $Message = "chore: release build — $fileCount file(s) modificati"
        Write-Warn "Messaggio auto-generato: '$Message'"
        Write-Host "  (usa -Message 'tuo messaggio' per personalizzarlo)" -ForegroundColor DarkGray
    }

    Invoke-Step "git add -u && git commit '$Message'" {
        git add -u
        $fullMsg = "$Message`n`nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
        git commit -m $fullMsg
        Write-Ok "Sorgenti committati (lo zip NON viene committato — e' gitignored)"
    }

    $gitVersion = (git describe --tags --always 2>$null) -replace '^v', ''
    Write-Ok "Versione aggiornata: v$gitVersion"
} else {
    Write-Step "1/7  Commit sorgenti — nessuna modifica, skip"
}

# ── Step 2: Build Python Embedded ────────────────────────────────────────────

if ($SkipEmbedded) {
    Write-Step "2/7  Build Python Embedded — SKIP (flag -SkipEmbedded)"
    $embeddedZip = $null
} else {
    Write-Step "2/7  Build Python Embedded"

    $doSkipDownload = $SkipDownload -or (Test-Path "$ProjectRoot\dist\python-embed.zip")
    if ($doSkipDownload) { Write-Ok "python-embed.zip trovato, SkipDownload attivo" }

    $embeddedSplat = @{ Zip = $true; SkipDownload = $doSkipDownload }

    Invoke-Step "build_release_embedded.ps1 -Zip$(if($doSkipDownload){' -SkipDownload'})" {
        & "$ProjectRoot\build_release_embedded.ps1" @embeddedSplat
        if ($LASTEXITCODE -ne 0) { throw "Build embedded fallita (exit $LASTEXITCODE)" }
    }

    $embeddedZip = Get-ChildItem "$ProjectRoot\dist" -Filter "ED-Event2Led-v*-win64-embedded.zip" -ErrorAction SilentlyContinue |
                   Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($embeddedZip) { Write-Ok "Embedded ZIP: $($embeddedZip.Name) ($([math]::Round($embeddedZip.Length/1MB,1)) MB)" }
}

# ── Step 3: Build PyInstaller ─────────────────────────────────────────────────

if ($SkipPyInstaller) {
    Write-Step "3/7  Build PyInstaller — SKIP (flag -SkipPyInstaller)"
} else {
    Write-Step "3/7  Build PyInstaller"

    Invoke-Step "build_pyinstaller.ps1 -Zip" {
        & "$ProjectRoot\build_pyinstaller.ps1" -Zip
        if ($LASTEXITCODE -ne 0) { throw "Build PyInstaller fallita (exit $LASTEXITCODE)" }
    }

    $pyiZip = Get-ChildItem "$ProjectRoot\dist" -Filter "ED-Event2Led-v*-win64-PyInstaller.zip" -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($pyiZip) {
        Write-Ok "PyInstaller ZIP: $($pyiZip.Name) ($([math]::Round($pyiZip.Length/1MB,1)) MB)"
    }
}

$pyiOutDir = Join-Path $ProjectRoot "dist\EDEvent2Led"

# ── Step 4: Aggiorna INSTALLATION_PACKAGE (artefatto locale, gitignored) ─────

Write-Step "4/7  Aggiorna INSTALLATION_PACKAGE (artefatto locale)"

if ($SkipPyInstaller) {
    throw "Impossibile aggiornare INSTALLATION_PACKAGE: -SkipPyInstaller e' attivo ma l'artefatto richiede la build PyInstaller. Esegui senza -SkipPyInstaller."
}
if (-not (Test-Path $pyiOutDir)) {
    throw "Cartella PyInstaller non trovata: $pyiOutDir. Verifica che il build PyInstaller sia riuscito."
}

$zipPath = "$ProjectRoot\INSTALLATION_PACKAGE.zip"

Invoke-Step "Aggiorna INSTALLATION_PACKAGE/ e .zip (da PyInstaller)" {
    if (Test-Path "$ProjectRoot\INSTALLATION_PACKAGE") {
        Remove-Item "$ProjectRoot\INSTALLATION_PACKAGE" -Recurse -Force
    }
    Copy-Item $pyiOutDir "$ProjectRoot\INSTALLATION_PACKAGE" -Recurse -Force
    Write-Ok "INSTALLATION_PACKAGE/ aggiornato (da PyInstaller — nessun sorgente .py)"

    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Compress-Archive -Path "$ProjectRoot\INSTALLATION_PACKAGE" -DestinationPath $zipPath -Force
    $sz = [math]::Round((Get-Item $zipPath).Length/1MB,1)
    Write-Ok "INSTALLATION_PACKAGE.zip aggiornato ($sz MB) — gitignored, NON committato"
}

# ── Step 5: Checksum SHA256 ──────────────────────────────────────────────────

Write-Step "5/7  Checksum SHA256"

$sha256Path = "$zipPath.sha256"

Invoke-Step "Get-FileHash SHA256 -> INSTALLATION_PACKAGE.zip.sha256" {
    $hash = (Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLower()
    # Formato compatibile con `sha256sum -c`: "<hash>  <nomefile>"
    "$hash  ED-Event2Led-v$gitVersion-win64.zip" | Set-Content $sha256Path -Encoding ascii -NoNewline
    Write-Ok "SHA256: $hash"
    Write-Ok "Scritto in: INSTALLATION_PACKAGE.zip.sha256"
}

# ── Step 6: Push commit sorgente sul repo privato ────────────────────────────

Write-Step "6/7  Push sorgenti su origin/master (repo privato)"

if ($trackedChanges) {
    Invoke-Step "git push origin master" {
        git push origin master
        Write-Ok "Push sorgenti completato (lo zip e' gitignored, non incluso)"
    }
} else {
    Write-Ok "Nessun commit sorgente nuovo, niente da pushare"
}

Pop-Location

# ── Step 7: Pubblicazione GitHub Release (repo pubblico) ─────────────────────

# Nome "parlante" dell'asset di release. NB: la sintassi gh "file#label" NON
# applica l'etichetta in modo affidabile -> rinominiamo fisicamente il file e
# carichiamo quello, cosi' il nome dell'asset = nome del file.
$assetName = "ED-Event2Led-v$gitVersion-win64.zip"
$assetZip  = "$ProjectRoot\dist\$assetName"
$assetSha  = "$assetZip.sha256"

if (-not $Publish) {
    Write-Step "7/7  GitHub Release — SKIP (usa -Publish per pubblicare)"
    Write-Host @"

  Artefatto pronto ma NON pubblicato. Per pubblicare a mano:

    Copy-Item INSTALLATION_PACKAGE.zip "dist\$assetName"
    # genera "dist\$assetName.sha256" con l'hash + il nome asset
    gh release create "v$gitVersion" ``
        "dist\$assetName" "dist\$assetName.sha256" ``
        --repo $PublicRepo ``
        --title "ED:Event2Led v$gitVersion" ``
        --notes "Release v$gitVersion"

  Oppure rilancia:  .\release.ps1 -Publish
"@ -ForegroundColor DarkGray
} else {
    Write-Step "7/7  GitHub Release su $PublicRepo"

    Invoke-Step "gh release create v$gitVersion (repo $PublicRepo)" {
        # Verifica gh disponibile e autenticato
        $null = gh auth status 2>&1
        if ($LASTEXITCODE -ne 0) { throw "gh non autenticato. Esegui: gh auth login" }

        # Crea copie con nome di release + checksum coerente col nome asset
        Copy-Item $zipPath $assetZip -Force
        $hash = (Get-FileHash $assetZip -Algorithm SHA256).Hash.ToLower()
        "$hash  $assetName" | Set-Content $assetSha -Encoding ascii -NoNewline

        gh release create "v$gitVersion" `
            "$assetZip" `
            "$assetSha" `
            --repo $PublicRepo `
            --title "ED:Event2Led v$gitVersion" `
            --notes "Release automatica v$gitVersion. Artefatto: build PyInstaller (senza sorgenti). Verifica integrita' con il file .sha256 allegato.`n`nSHA256: $hash"
        if ($LASTEXITCODE -ne 0) { throw "gh release create fallita (exit $LASTEXITCODE)" }
        Write-Ok "Release v$gitVersion pubblicata su $PublicRepo (asset: $assetName)"
    }
}

# ── Riepilogo ──────────────────────────────────────────────────────────────────

$border = "=" * 58
Write-Host "`n$border" -ForegroundColor White
Write-Host "  Release build completata: ED:Event2Led v$gitVersion" -ForegroundColor Green
Write-Host $border -ForegroundColor White

if (-not $DryRun) {
    Write-Host "  Privato:  origin/master (solo sorgenti)" -ForegroundColor White
    if ($Publish) {
        Write-Host "  Pubblico: GitHub Release v$gitVersion su $PublicRepo" -ForegroundColor White
    } else {
        Write-Host "  Pubblico: NON pubblicato (rilancia con -Publish)" -ForegroundColor White
    }
    Write-Host "  Artefatto: INSTALLATION_PACKAGE.zip (+ .sha256) — locale, gitignored" -ForegroundColor White
    if ($embeddedZip) { Write-Host "  Embedded:  dist\$($embeddedZip.Name)" -ForegroundColor White }
}

Write-Host "$border`n" -ForegroundColor White
