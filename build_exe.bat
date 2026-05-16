@echo off
setlocal
cd /d "%~dp0"
echo.
echo ============================================================================
echo   iJeery V5.0 - Generation EXE (build_ijerry_exe.py)
echo ============================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable dans le PATH.
    echo Installez Python 3.11 ou 3.12 64 bits puis relancez.
    pause
    exit /b 1
)

python build_ijerry_exe.py %*
set ERR=%ERRORLEVEL%
if %ERR% NEQ 0 (
    echo.
    echo [ERREUR] Build echoue (code %ERR%).
    pause
    exit /b %ERR%
)

echo.
pause
exit /b 0
