@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ============================================================================
echo   iJeery V5.0 - Generation EXE (build_ijerry_exe.py)
echo ============================================================================
echo.

set "PYEXE="
set "PYTAG="

REM ---------------------------------------------------------------------------
REM 1) Surcharge manuelle (chemin complet vers python.exe)
REM    Exemple : set IJEERY_PYTHON=C:\Python312\python.exe
REM ---------------------------------------------------------------------------
if defined IJEERY_PYTHON (
    if exist "%IJEERY_PYTHON%" (
        set "PYEXE=%IJEERY_PYTHON%"
        set "PYTAG=IJEERY_PYTHON"
        goto :found_python
    )
    echo [AVERTISSEMENT] IJEERY_PYTHON introuvable : %IJEERY_PYTHON%
    echo.
)

REM ---------------------------------------------------------------------------
REM 2) Lanceur Windows "py" — versions conseillees en priorite
REM ---------------------------------------------------------------------------
where py >nul 2>&1
if not errorlevel 1 (
    call :resolve_py 3.12
    if defined PYEXE goto :found_python
    call :resolve_py 3.11
    if defined PYEXE goto :found_python
    call :resolve_py 3.13
    if defined PYEXE goto :found_python
    call :resolve_py 3
    if defined PYEXE goto :found_python
)

REM ---------------------------------------------------------------------------
REM 3) python.exe dans le PATH
REM ---------------------------------------------------------------------------
where python >nul 2>&1
if not errorlevel 1 (
    call :resolve_cmd python
    if defined PYEXE goto :found_python
)

REM ---------------------------------------------------------------------------
REM 4) Dernier recours : py sans version
REM ---------------------------------------------------------------------------
where py >nul 2>&1
if not errorlevel 1 (
    call :resolve_cmd py
    if defined PYEXE goto :found_python
)

echo [ERREUR] Aucun Python utilisable trouve.
echo.
echo   Installez Python 3.11 ou 3.12 (64 bits), par exemple :
echo     py install 3.12
echo.
echo   Ou definissez un chemin explicite avant de lancer ce script :
echo     set IJEERY_PYTHON=C:\chemin\vers\python.exe
echo.
pause
exit /b 1

REM ===========================================================================
:found_python
echo [INFO] Python selectionne : %PYTAG%
echo        Executable     : %PYEXE%
"%PYEXE%" -c "import sys; print(sys.version)"
echo.
echo   Ordre de recherche : py -3.12 ^> py -3.11 ^> py -3.13 ^> py -3 ^> python
echo   Forcer un Python   : set IJEERY_PYTHON=C:\chemin\vers\python.exe
echo.

"%PYEXE%" build_ijerry_exe.py %*
set ERR=%ERRORLEVEL%
if %ERR% NEQ 0 (
    echo.
    echo [ERREUR] Build echoue (code %ERR%).
    echo Astuce debug : "%PYEXE%" build_ijerry_exe.py --console
    pause
    exit /b %ERR%
)

echo.
pause
exit /b 0

REM ===========================================================================
REM Sous-routines
REM ===========================================================================

:resolve_py
set "PYEXE="
set "PYTAG="
for /f "delims=" %%P in ('py -%1 -c "import sys; print(sys.executable)" 2^>nul') do (
    if not defined PYEXE set "PYEXE=%%P"
)
if defined PYEXE set "PYTAG=py -%1"
exit /b 0

:resolve_cmd
set "PYEXE="
set "PYTAG="
for /f "delims=" %%P in ('%~1 -c "import sys; print(sys.executable)" 2^>nul') do (
    if not defined PYEXE set "PYEXE=%%P"
)
if defined PYEXE set "PYTAG=%~1"
exit /b 0
