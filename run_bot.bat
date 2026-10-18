@echo off
REM ==============================================================================
REM TELEGRAM AI 2D VIDEO CLONING BOT RUNNER
REM ==============================================================================
title TELEGRAM AI 2D VIDEO CLONING BOT
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

set BASE_DIR=%~dp0
set BOT_PY=%BASE_DIR%telegram_bot.py

if exist "%BASE_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%BASE_DIR%.venv\Scripts\python.exe"
    goto :run_bot
)
set "PYTHON_EXE=python"

:run_bot
echo ======================================================================
echo           TELEGRAM AI 2D VIDEO CLONING BOT (@ai2Dcloningbot)
echo ======================================================================
echo Starting bot service...
"%PYTHON_EXE%" "%BOT_PY%"
pause
