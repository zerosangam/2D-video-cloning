@echo off
REM ==============================================================================
REM MR. PERFECT AI 2D MASTER CLONING RUNNER (PORTABLE & EMOJI-SAFE)
REM ==============================================================================
title MR. PERFECT AI 2D VIDEO CLONING PIPELINE
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

set BASE_DIR=%~dp0..
set SCRIPT_PATH=%~dp0mr_perfect_master_engine.py
set RUNNER_PY=%BASE_DIR%\start_cloning.py

if defined PYTHON_EXE if exist "%PYTHON_EXE%" goto :python_ready
if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"
    goto :python_ready
)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :python_ready
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :python_ready
)

echo [ERROR] Python executable not found!
echo Please ensure Python 3.10+ is installed or set the PYTHON_EXE variable.
pause
exit /b 1

:python_ready
echo ======================================================================
echo    STARTING MR. PERFECT AI 2D VIDEO CLONING PIPELINE
echo ======================================================================
echo Python:    "%PYTHON_EXE%"
echo Engine:    "%SCRIPT_PATH%"
echo.

if exist "%RUNNER_PY%" (
    "%PYTHON_EXE%" "%RUNNER_PY%" %*
) else (
    "%PYTHON_EXE%" "%SCRIPT_PATH%" %*
)

echo.
echo ======================================================================
echo    MR. PERFECT AI CLONING COMPLETE! CHECK output\ DIRECTORY
echo ======================================================================
pause
