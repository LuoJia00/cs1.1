@echo off
setlocal
cd /d "%~dp0"
if exist "python\python.exe" (
    set "CANVAS_PYTHON=%~dp0python\python.exe"
    goto install
)
if exist ".venv\Scripts\python.exe" goto venv_ready
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m venv .venv
) else (
    python -m venv .venv
)
if errorlevel 1 goto failed
:venv_ready
set "CANVAS_PYTHON=%~dp0.venv\Scripts\python.exe"
:install
"%CANVAS_PYTHON%" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ is required'"
if errorlevel 1 goto failed
"%CANVAS_PYTHON%" -m pip install -r requirements-lock.txt
if errorlevel 1 goto failed
"%CANVAS_PYTHON%" -c "import fastapi, uvicorn, requests, httpx, PIL, pydantic, multipart, websockets; print('Dependencies OK. You can start the app now.')"
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo Installation failed. See the error above.
echo Install Python 3.10+ from https://www.python.org/downloads/windows/
echo Or copy the working python folder from your other Windows computer.
pause
exit /b 1
