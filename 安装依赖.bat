@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "NO_PAUSE="
if /i "%~1"=="/nopause" set "NO_PAUSE=1"

if exist "python\python.exe" (
    set "CANVAS_PYTHON=%~dp0python\python.exe"
    goto install
)
if exist ".venv\Scripts\python.exe" goto venv_ready

where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
        if not errorlevel 1 goto venv_ready
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
    if not errorlevel 1 (
        python -m venv .venv
        if not errorlevel 1 goto venv_ready
    )
)

echo No usable Python 3.10+ was found. Downloading a private portable Python for this project...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\bootstrap_windows.ps1"
if errorlevel 1 goto failed
if not exist "python\python.exe" goto failed
set "CANVAS_PYTHON=%~dp0python\python.exe"
goto install

:venv_ready
set "CANVAS_PYTHON=%~dp0.venv\Scripts\python.exe"
:install
"%CANVAS_PYTHON%" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ is required'"
if errorlevel 1 goto failed
"%CANVAS_PYTHON%" -m pip install -r requirements-lock.txt
if errorlevel 1 goto failed
"%CANVAS_PYTHON%" -c "import fastapi, uvicorn, requests, httpx, PIL, pydantic, multipart, websockets; print('Dependencies OK. You can start the app now.')"
if errorlevel 1 goto failed
if not defined NO_PAUSE pause
exit /b 0
:failed
echo Installation failed. See the error above.
echo Make sure this computer can access python.org and pypi.org, then try again.
if not defined NO_PAUSE pause
exit /b 1
