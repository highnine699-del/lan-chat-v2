@echo off
setlocal EnableDelayedExpansion
title LAN Chat + ngrok

echo.
echo =========================================
echo   LAN CHAT  +  ngrok  -  Starting...
echo =========================================
echo.

REM ── Find Python ───────────────────────────────────────────────────────────
set PYTHON=
py --version >nul 2>&1 && set PYTHON=py
if not "!PYTHON!"=="" goto :python_found

python --version >nul 2>&1 && set PYTHON=python
if not "!PYTHON!"=="" goto :python_found

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :python_found
)

echo ERROR: Python not found.
echo Please install Python from https://python.org
pause
exit /b 1

:python_found
echo [OK] Python: !PYTHON!

REM ── Find ngrok ────────────────────────────────────────────────────────────
set NGROK=
where ngrok >nul 2>&1 && set NGROK=ngrok
if not "!NGROK!"=="" goto :ngrok_found

REM Check common install locations
for %%P in (
    "%USERPROFILE%\Downloads\ngrok.exe"
    "%USERPROFILE%\ngrok.exe"
    "%USERPROFILE%\AppData\Local\ngrok\ngrok.exe"
    "C:\Program Files\ngrok\ngrok.exe"
    "C:\Program Files (x86)\ngrok\ngrok.exe"
    "C:\ngrok\ngrok.exe"
) do (
    if exist %%P (
        set NGROK=%%P
        goto :ngrok_found
    )
)

REM Check WindowsApps (Microsoft Store install)
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WindowsApps\ngrok*") do (
    if exist "%%D\ngrok.exe" (
        set NGROK="%%D\ngrok.exe"
        goto :ngrok_found
    )
)

echo.
echo ERROR: ngrok not found.
echo.
echo To fix this:
echo   1. Download ngrok from https://ngrok.com/download
echo   2. Extract ngrok.exe to one of these locations:
echo        %USERPROFILE%\Downloads\ngrok.exe
echo        %USERPROFILE%\ngrok.exe
echo      OR add it to your PATH
echo.
pause
exit /b 1

:ngrok_found
echo [OK] ngrok:  !NGROK!
echo.

REM ── Install Python dependencies ───────────────────────────────────────────
echo Installing required packages...
!PYTHON! -m pip install flask flask-socketio --quiet
echo.

REM ── Bundle offline emoji picker ───────────────────────────────────────────
echo Bundling offline assets...
!PYTHON! download_assets.py
echo.

REM ── Get local IP ─────────────────────────────────────────────────────────
for /f "delims=" %%A in ('powershell -NoProfile -Command ^
    "([System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) ^
    | Where-Object {$_.AddressFamily -eq 'InterNetwork'} ^
    | Select-Object -First 1).IPAddressToString"') do set LOCAL_IP=%%A

REM ── Start Flask server in a separate window ───────────────────────────────
echo Starting Flask server...
start "LAN Chat Server" cmd /k "!PYTHON! server.py"

REM Give the server a moment to bind the port before ngrok connects
timeout /t 2 /nobreak >nul

REM ── Start ngrok in a separate window ─────────────────────────────────────
echo Starting ngrok tunnel...
start "ngrok" cmd /k "!NGROK! http 5000"

REM ── Poll ngrok API for the public URL (up to 15 seconds) ─────────────────
echo Waiting for ngrok tunnel...
set PUBLIC_URL=
set /a TRIES=0

:poll_loop
timeout /t 1 /nobreak >nul
set /a TRIES+=1

REM Use PowerShell to query the ngrok local API
for /f "delims=" %%U in ('powershell -NoProfile -Command ^
    "try { (Invoke-RestMethod http://localhost:4040/api/tunnels).tunnels[0].public_url } catch { '' }"') do (
    set PUBLIC_URL=%%U
)

if not "!PUBLIC_URL!"=="" goto :got_url
if !TRIES! LSS 15 goto :poll_loop

REM Timed out — fall back to local URL
echo.
echo [WARN] Could not get ngrok URL. Check the ngrok window for the URL.
set PUBLIC_URL=http://!LOCAL_IP!:5000
goto :show_urls

:got_url
REM ── Copy public URL to clipboard ─────────────────────────────────────────
echo !PUBLIC_URL! | clip

:show_urls
echo.
echo =========================================
echo   LAN Chat is LIVE!
echo =========================================
echo.
echo   Local URL:   http://!LOCAL_IP!:5000
echo   Public URL:  !PUBLIC_URL!
echo.
echo   Public URL copied to clipboard.
echo   Share it with anyone — no WiFi needed!
echo.
echo =========================================
echo.

REM ── Open browser at the public URL ───────────────────────────────────────
start !PUBLIC_URL!

echo   Both server windows are running in the background.
echo   Close those windows (or press Ctrl+C in them) to stop.
echo.
pause
