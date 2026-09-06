@echo off
cd /d "%~dp0"

set "PYEXE=%~dp0python\python.exe"
if not exist "%PYEXE%" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
    set "PYEXE="
    where python >nul 2>nul
    if not errorlevel 1 set "PYEXE=python"
)

if not defined PYEXE goto prepare_python
"%PYEXE%" -c "import fastapi, uvicorn, requests, httpx, PIL, pydantic, multipart, websockets" >nul 2>nul
if errorlevel 1 goto prepare_python
goto python_ready

:prepare_python
echo First run: preparing Python and required packages. Internet access is required...
call "%~dp0安装依赖.bat" /nopause
if errorlevel 1 (
    echo.
    echo Automatic setup failed. See the error above.
    pause
    exit /b 1
)
set "PYEXE=%~dp0python\python.exe"
if not exist "%PYEXE%" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
    echo Python setup completed, but its executable could not be found.
    pause
    exit /b 1
)

:python_ready

rem Read the current Windows user proxy for Codex/GPT Image helpers.
set "SYSTEM_PROXY="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$cfg=Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue; if($cfg.ProxyEnable -eq 1 -and $cfg.ProxyServer){$raw=[string]$cfg.ProxyServer; $target=$raw; if($raw -match '(?:^|;)https=([^;]+)'){$target=$Matches[1]}elseif($raw -match '(?:^|;)http=([^;]+)'){$target=$Matches[1]}elseif($raw.Contains(';')){$target=$raw.Split(';')[0]}; if($target -notmatch '^[a-z]+://'){$target='http://'+$target}; $target}"`) do set "SYSTEM_PROXY=%%P"
if defined SYSTEM_PROXY (
    set "HTTP_PROXY=%SYSTEM_PROXY%"
    set "HTTPS_PROXY=%SYSTEM_PROXY%"
) else (
    set "HTTP_PROXY="
    set "HTTPS_PROXY="
)
set "LAN_IP=127.0.0.1"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ip=(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } | Select-Object -First 1 -ExpandProperty IPv4Address).IPAddress; if(-not $ip){$ip=(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Sort-Object InterfaceMetric | Select-Object -First 1 -ExpandProperty IPAddress)}; if($ip){$ip}else{'127.0.0.1'}"`) do set "LAN_IP=%%I"
set "NO_PROXY=127.0.0.1,localhost,%LAN_IP%"
set "APP_URL=http://127.0.0.1:3000/"
set "LAN_URL=http://%LAN_IP%:3000/"

rem Avoid launching a second copy when port 3000 is already in use.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; try{$r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:3000/api/app-info' -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0}}catch{}; $tcp=New-Object Net.Sockets.TcpClient; try{$pending=$tcp.BeginConnect('127.0.0.1',3000,$null,$null); if($pending.AsyncWaitHandle.WaitOne(700)){$tcp.EndConnect($pending); exit 2}}catch{}finally{$tcp.Close()}; exit 1"
set "PORT_STATE=%ERRORLEVEL%"
if "%PORT_STATE%"=="0" (
    echo ComfyUI-API-Modelscope is already running.
    echo Visit: %APP_URL%
    echo LAN: %LAN_URL%
    start "" "%APP_URL%"
    exit /b 0
)
if "%PORT_STATE%"=="2" (
    echo Port 3000 is occupied by another program.
    echo Please close that program, then run this script again.
    pause
    exit /b 2
)

echo Starting ComfyUI-API-Modelscope...
if defined SYSTEM_PROXY (echo Proxy: %SYSTEM_PROXY%) else (echo Proxy: disabled)
echo Visit: %APP_URL%
echo LAN: %LAN_URL%
echo Press Ctrl+C to stop.
echo.

start /b cmd /c "timeout /t 3 /nobreak >nul && start %APP_URL%"
"%PYEXE%" main.py

echo.
echo Server stopped.
pause
