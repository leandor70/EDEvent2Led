@echo off
REM ============================================================================
REM ED:Event2Led - Start Dev Server (No Cache)
REM ============================================================================
REM Clears Python bytecode cache before starting the development server.
REM Use this after modifying Python source code to ensure fresh module loading.
REM ============================================================================

echo.
echo ========================================================================
echo   ED:Event2Led - Starting Dev Server (Cache Cleared)
echo ========================================================================
echo.

REM Clear Python bytecode cache
echo [1/3] Clearing Python bytecode cache...
echo.

REM Remove __pycache__ directories recursively in src/
if exist "src\__pycache__" (
    echo     Removing src\__pycache__\
    rmdir /s /q "src\__pycache__" 2>nul
)

for /d /r "src" %%d in (__pycache__) do (
    if exist "%%d" (
        echo     Removing %%d
        rmdir /s /q "%%d" 2>nul
    )
)

REM Remove individual .pyc files
del /s /q "src\*.pyc" >nul 2>&1

echo.
echo [2/3] Cache cleared successfully
echo.

REM Start the development server
echo [3/3] Starting development server...
echo.
echo ========================================================================
echo.

call venv\Scripts\python.exe src\main.py

pause
