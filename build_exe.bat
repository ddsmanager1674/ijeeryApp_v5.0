@echo off
setlocal EnableExtensions
chcp 65001 >nul

REM ============================================================================
REM Build iJeery V5.0 (EXE) - PyInstaller
REM - Cree/Utilise .venv
REM - Installe dependances (requirements.txt) + PyInstaller
REM - Build via iJeery_V5.0.spec
REM - Copie les fichiers de config utiles dans le dossier final
REM - Copie le dossier icons\ (iconeIjeery.ico) dans le dossier final
REM
REM Usage:
REM   build_exe.bat
REM   build_exe.bat clean
REM   build_exe.bat run
REM   build_exe.bat pack
REM   build_exe.bat build
REM   build_exe.bat quick
REM ============================================================================

cd /d "%~dp0"

set SPEC=iJeery_V5.0.spec
set DIST=dist_final
set WORK=build_final
set APP=iJeery_V5.0
set OUTDIR=%DIST%\%APP%
set EXE=%OUTDIR%\%APP%.exe
set VENV=.venv
set PYTHON=%VENV%\Scripts\python.exe
set ICONS_DIR=icons

if /i "%~1"=="clean" goto :clean
if /i "%~1"=="run"   goto :run
if /i "%~1"=="pack"  goto :pack
if /i "%~1"=="build" goto :build_only
if /i "%~1"=="quick" goto :build_only

echo.
echo ============================================================================
echo   COMPILATION IJEERY V5.0 - PYINSTALLER
echo ============================================================================
echo   Dist : %DIST%
echo   Work : %WORK%
echo.

if not exist "%SPEC%" (
  echo [ERREUR] Fichier spec introuvable: %SPEC%
  goto :fail
)

call :ensure_venv
if errorlevel 1 goto :fail

echo [INFO] Mise a jour pip / setuptools / wheel...
"%PYTHON%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail

if exist "requirements.txt" (
  echo [INFO] Installation des dependances...
  "%PYTHON%" -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
) else (
  echo [WARN] requirements.txt introuvable, on continue.
)

echo [INFO] Installation/MAJ de PyInstaller...
"%PYTHON%" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail

echo [INFO] Build en cours...
"%PYTHON%" -m PyInstaller "%SPEC%" --noconfirm --clean --distpath "%DIST%" --workpath "%WORK%"
if errorlevel 1 goto :fail

if not exist "%EXE%" (
  echo [ERREUR] EXE non trouve apres build: %EXE%
  goto :fail
)

echo [INFO] Copie des fichiers de config...
call :copy_if_exists "config.json"   "%OUTDIR%\config.json"
call :copy_if_exists "config.ini"    "%OUTDIR%\config.ini"
call :copy_if_exists "settings.json" "%OUTDIR%\settings.json"
call :copy_if_exists "session.json"  "%OUTDIR%\session.json"
call :copy_if_exists "remember.json" "%OUTDIR%\remember.json"

echo [INFO] Copie du dossier icons...
call :copy_dir_if_exists "%ICONS_DIR%" "%OUTDIR%\%ICONS_DIR%"

echo.
echo ============================================================================
echo [OK] Build termine !
echo ============================================================================
echo   EXE     : %EXE%
echo   Dossier : %OUTDIR%
echo.
goto :end

REM ----------------------------------------------------------------------------
:build_only
echo.
echo ============================================================================
echo   BUILD RAPIDE (sans installation pip)
echo ============================================================================
echo.
if not exist "%SPEC%" (
  echo [ERREUR] Fichier spec introuvable: %SPEC%
  goto :fail
)
call :ensure_venv
if errorlevel 1 goto :fail

echo [INFO] Build en cours...
"%PYTHON%" -m PyInstaller "%SPEC%" --noconfirm --clean --distpath "%DIST%" --workpath "%WORK%"
if errorlevel 1 goto :fail

if not exist "%EXE%" (
  echo [ERREUR] EXE non trouve apres build: %EXE%
  goto :fail
)

call :copy_dir_if_exists "%ICONS_DIR%" "%OUTDIR%\%ICONS_DIR%"

echo [OK] EXE: %EXE%
goto :end

REM ----------------------------------------------------------------------------
:ensure_venv
if exist "%PYTHON%" exit /b 0
echo [INFO] Creation du venv Python 3.12...
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -m venv "%VENV%"
  if errorlevel 1 exit /b 1
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERREUR] Python introuvable.
    exit /b 1
  )
  python -m venv "%VENV%"
  if errorlevel 1 exit /b 1
)
exit /b 0

REM ----------------------------------------------------------------------------
:copy_if_exists
if exist "%~1" (
  copy /Y "%~1" "%~2" >nul
  echo   - %~1 -^> %~2
)
exit /b 0

REM ----------------------------------------------------------------------------
:copy_dir_if_exists
if exist "%~1\" (
  if not exist "%~2\" mkdir "%~2"
  xcopy /E /I /Y /Q "%~1\*" "%~2\" >nul
  echo   - %~1\ -^> %~2\
) else (
  echo   [WARN] Dossier %~1 introuvable, ignore.
)
exit /b 0

REM ----------------------------------------------------------------------------
:run
if exist "%EXE%" (
  echo [INFO] Lancement: %EXE%
  start "" "%EXE%"
  goto :end
)
echo [ERREUR] EXE introuvable. Lancez d'abord: build_exe.bat
goto :fail

REM ----------------------------------------------------------------------------
:pack
if not exist "%OUTDIR%" (
  echo [ERREUR] Dossier introuvable: %OUTDIR%
  goto :fail
)
set ZIP=%DIST%\%APP%_Portable.zip
if exist "%ZIP%" del /Q "%ZIP%"
echo [INFO] Creation du zip: %ZIP%
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%OUTDIR%\*' -DestinationPath '%ZIP%'"
if errorlevel 1 goto :fail
echo [OK] Zip cree: %ZIP%
goto :end

REM ----------------------------------------------------------------------------
:clean
echo [INFO] Nettoyage: %DIST% et %WORK%
if exist "%DIST%" rmdir /S /Q "%DIST%"
if exist "%WORK%" rmdir /S /Q "%WORK%"
echo [OK] Nettoyage termine.
goto :end

REM ----------------------------------------------------------------------------
:fail
echo.
echo [ECHEC] La compilation a echoue.
echo.
pause
exit /b 1

:end
pause
exit /b 0
