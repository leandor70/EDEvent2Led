@echo off
REM ============================================================
REM  ED:Event2Led - Full Build Script
REM  Produces: dist\EDEvent2Led-Setup-x.y.z.exe
REM
REM  Prerequisites (must be in PATH or installed):
REM    - Python 3.11+  with pip
REM    - PyInstaller   (pip install pyinstaller)
REM    - Inno Setup 6  (https://jrsoftware.org/isinfo.php)
REM    - UPX (optional, for smaller .exe)  (https://upx.github.io/)
REM ============================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0.."
set ROOT=%CD%

echo.
echo ============================================================
echo   ED:Event2Led - Build System
echo ============================================================
echo   Root: %ROOT%
echo.

REM ── Step 1: Check Python ─────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python not found. Install Python 3.11+ and add to PATH.
    exit /b 1
)
echo [OK] Python found

REM ── Step 2: Install/upgrade build dependencies ───────────────────────────
echo.
echo [1/4] Installing build dependencies...
pip install --quiet --upgrade pyinstaller eel watchdog
if errorlevel 1 (
    echo [FAIL] pip install failed.
    exit /b 1
)
echo [OK] Dependencies ready

REM ── Step 3: Clean previous build ─────────────────────────────────────────
echo.
echo [2/4] Cleaning previous build...
if exist dist\EDEvent2Led (
    rmdir /s /q dist\EDEvent2Led
    echo      Removed dist\EDEvent2Led\
)
if exist build\__pycache__ (
    rmdir /s /q build\__pycache__
)

REM ── Step 4: PyInstaller ───────────────────────────────────────────────────
echo.
echo [3/4] Running PyInstaller...
pyinstaller build\EDEvent2Led.spec --noconfirm
if errorlevel 1 (
    echo [FAIL] PyInstaller failed. Check output above.
    exit /b 1
)
echo [OK] PyInstaller build complete: dist\EDEvent2Led\

REM ── Step 5: Inno Setup ───────────────────────────────────────────────────
echo.
echo [4/4] Building installer with Inno Setup...

REM Try common Inno Setup install locations
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
)

if "!ISCC!"=="" (
    echo [WARN] Inno Setup not found. Skipping installer creation.
    echo        Install from: https://jrsoftware.org/isinfo.php
    echo        Then run manually: iscc build\installer.iss
    goto :done
)

"!ISCC!" build\installer.iss
if errorlevel 1 (
    echo [FAIL] Inno Setup failed. Check output above.
    exit /b 1
)
echo [OK] Installer created: dist\EDEvent2Led-Setup-*.exe

:done
echo.
echo ============================================================
echo   Build complete!
echo ============================================================
echo   App bundle : dist\EDEvent2Led\
if not "!ISCC!"=="" (
echo   Installer  : dist\EDEvent2Led-Setup-*.exe
)
echo ============================================================
echo.
