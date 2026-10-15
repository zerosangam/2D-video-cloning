@echo off
REM ==============================================================================
REM MR. PERFECT AI 2D ANIMATION MASTER CLONING RUNNER (PORTABLE & EMOJI-SAFE)
REM ==============================================================================
title MR. PERFECT AI 2D VIDEO CLONING AUTOMATION
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

set BASE_DIR=%~dp0
set RUNNER_PY=%BASE_DIR%start_cloning.py

if defined PYTHON_EXE if exist "%PYTHON_EXE%" goto :python_ready
if exist "%BASE_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%BASE_DIR%.venv\Scripts\python.exe"
    goto :python_ready
)
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
echo Please ensure Python is installed or set the PYTHON_EXE environment variable.
pause
exit /b 1

:python_ready
echo ======================================================================
echo     MR. PERFECT AI 2D GREASE PENCIL MASTER AUTOMATION SYSTEM
echo ======================================================================
echo Project Root: "%BASE_DIR%"
echo Python Path:  "%PYTHON_EXE%"
echo.

"%PYTHON_EXE%" "%RUNNER_PY%" %*
set SCRIPT_EXIT_CODE=%errorlevel%

echo.
if %SCRIPT_EXIT_CODE% equ 0 (
    echo ======================================================================
    echo [SUCCESS] 2D Recreation complete!
    echo - Video output:    output\videos\mr_perfect_lines.mp4
    echo - Full-color 2D:   output\videos\mr_perfect_color.mp4
    echo - Blender 5.2:     output\blender\project.blend
    echo - Previews:        output\previews\mr_perfect_grid.jpg
    echo ======================================================================
) else (
    echo [WARNING] Pipeline exited with code %SCRIPT_EXIT_CODE%.
)

pause
exit /b %SCRIPT_EXIT_CODE%
