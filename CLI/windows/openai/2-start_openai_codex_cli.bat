@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\..\.."

set "CODEX_CMD="
for /f "usebackq delims=" %%P in (`npm.cmd config get prefix 2^>nul`) do if exist "%%P\codex.cmd" set "CODEX_CMD=%%P\codex.cmd"
if not defined CODEX_CMD if exist "%LOCALAPPDATA%\Programs\OpenAI\Codex\bin\codex.exe" set "CODEX_CMD=%LOCALAPPDATA%\Programs\OpenAI\Codex\bin\codex.exe"
if not defined CODEX_CMD for /f "usebackq delims=" %%P in (`where codex.exe 2^>nul`) do if not defined CODEX_CMD set "CODEX_CMD=%%P"

if not defined CODEX_CMD (
    echo Codex CLI was not found in PATH.
    echo Please run CLI\windows\openai\1-install_openai_codex_cli.bat first.
    echo.
    pause
    exit /b 1
)

"%CODEX_CMD%"
