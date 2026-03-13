@echo off
setlocal enabledelayedexpansion

REM UltraBot one-go setup for Windows (offline-first)
REM Usage:
REM   setup.bat          -> setup + config alignment
REM   setup.bat --run    -> setup + config alignment + start gateway

echo.
echo ============================================================
echo   ^>^>^> ULTRABOT ONE-GO SETUP FOR WINDOWS ^<^<^<
echo ============================================================
echo.

echo [1/7] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from https://python.org
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo OK %%i
echo.

set "VENV_DIR=venv311"
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"
set "ULTRA_EXE=%VENV_DIR%\Scripts\ultrabot.exe"

echo [2/7] Creating or reusing %VENV_DIR%...
if not exist "%VENV_DIR%\Scripts\python.exe" (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create %VENV_DIR%
        exit /b 1
    )
)
echo OK venv ready at %VENV_DIR%
echo.

echo [3/7] Activating %VENV_DIR%...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate %VENV_DIR%
    exit /b 1
)
echo OK venv activated
echo.

echo [4/7] Installing UltraBot in editable mode...
for %%P in (18790 18791 18792) do (
    for /f "tokens=5" %%I in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
        if not "%%I"=="0" taskkill /PID %%I /F >nul 2>&1
    )
)
taskkill /IM ultrabot.exe /F >nul 2>&1
taskkill /IM nanobot.exe /F >nul 2>&1
"%PY_EXE%" -m pip install -U pip >nul 2>&1
"%PY_EXE%" -m pip install -e .
if errorlevel 1 (
    echo ERROR: pip install -e . failed
    exit /b 1
)
echo OK installation complete
echo.

echo [5/7] Ensuring global config exists...
set "CFG=%USERPROFILE%\.nanobot\config.json"
if not exist "%CFG%" (
    "%ULTRA_EXE%" onboard
    if errorlevel 1 (
        echo ERROR: ultrabot onboard failed
        exit /b 1
    )
)
echo OK config path: %CFG%
echo.

echo [6/7] Aligning config for offline-first startup...
"%PY_EXE%" "scripts\align_offline_config.py"
if errorlevel 1 (
    echo ERROR: config alignment failed
    exit /b 1
)
echo.

echo [7/7] Verifying CLI health...
set "NANOBOT_CONFIG_PATH=%CFG%"
"%ULTRA_EXE%" status
if errorlevel 1 (
    echo ERROR: ultrabot status failed
    exit /b 1
)
echo.

echo ============================================================
echo   SETUP COMPLETE
echo ============================================================
echo Config: %CFG%
echo.
echo Run now:
echo   set NANOBOT_CONFIG_PATH=%CFG%
echo   ultrabot gateway --verbose
echo.
echo Quick checks:
echo   ultrabot channels status
echo   ultrabot channels telegram-check
echo   ultrabot channels discord-check
echo.

if /I "%~1"=="--run" (
    echo Starting gateway now...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R ":18790 .*LISTENING :18791 .*LISTENING :18792 .*LISTENING"') do (
        if not "%%p"=="0" taskkill /PID %%p /F >nul 2>&1
    )
    "%ULTRA_EXE%" gateway --verbose
)
