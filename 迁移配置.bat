@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "CANVAS_PYTHON=%~dp0python\python.exe"
if not exist "%CANVAS_PYTHON%" set "CANVAS_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%CANVAS_PYTHON%" set "CANVAS_PYTHON=python"
set "PYTHONIOENCODING=utf-8"
"%CANVAS_PYTHON%" tools\config_transfer.py
pause
