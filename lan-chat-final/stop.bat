@echo off
title Stop LAN Chat Server
setlocal enabledelayedexpansion
echo.
echo =========================================
echo   LAN CHAT - Stopping...
echo =========================================
echo.

REM ── Method 1: PID file (instant, no password needed) ─────────────────────
if exist server.pid (
    set /p _PID=<server.pid
    echo Found PID: !_PID!

    REM Verify the process is actually running before killing
    tasklist /FI "PID eq !_PID!" 2>nul | find "!_PID!" >nul
    if !ERRORLEVEL! EQU 0 (
        echo Stopping server...
        taskkill /PID !_PID! /F >nul 2>&1
        del server.pid >nul 2>&1
        echo.
        echo [OK] Server stopped.
        goto :done
    ) else (
        echo [!] PID !_PID! is not running. Cleaning up stale PID file.
        del server.pid >nul 2>&1
    )
)

REM ── Method 2: Graceful HTTP shutdown (uses admin password if available) ───
set _KEY=%ADMIN_PASSWORD%
if "!_KEY!"=="" (
    echo No PID file found. Enter admin password for graceful shutdown,
    echo or press Enter to force-kill by process name.
    echo.
    set /p _KEY="Admin password (Enter to skip): "
)

if not "!_KEY!"=="" (
    echo Sending HTTP shutdown signal...
    curl -s -o nul -X POST http://localhost:5000/shutdown -H "X-Admin-Key: !_KEY!" 2>nul
    if !ERRORLEVEL! EQU 0 (
        echo [OK] Graceful shutdown sent. Waiting 3s...
        timeout /t 3 /nobreak >nul
        REM Verify port is free
        netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>&1
        if !ERRORLEVEL! NEQ 0 goto :done
        echo [!] Port still in use — force-killing...
    )
)

REM ── Method 3: Kill by commandline match — targets only our server.py ────────
REM Uses WMIC to read each python process's full commandline and only kills
REM the one running server.py. Safe — will NOT kill VS Code, other scripts, etc.
echo Searching for LAN Chat server process...
set _KILLED=0

for /f "tokens=2 delims=," %%p in ('tasklist /fi "imagename eq python.exe" /fo csv /nh 2^>nul') do (
    set _RAW=%%~p
    set _PID2=!_RAW:"=!
    wmic process !_PID2! get commandline 2>nul | findstr /i "server\.py" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        taskkill /F /PID !_PID2! >nul 2>&1
        echo [OK] Stopped LAN Chat server (python.exe PID !_PID2!)
        set _KILLED=1
    )
)
for /f "tokens=2 delims=," %%p in ('tasklist /fi "imagename eq py.exe" /fo csv /nh 2^>nul') do (
    set _RAW=%%~p
    set _PID2=!_RAW:"=!
    wmic process !_PID2! get commandline 2>nul | findstr /i "server\.py" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        taskkill /F /PID !_PID2! >nul 2>&1
        echo [OK] Stopped LAN Chat server (py.exe PID !_PID2!)
        set _KILLED=1
    )
)

if "!_KILLED!"=="0" (
    echo [!] No LAN Chat server process found. Already stopped?
)
del server.pid >nul 2>&1

:done
echo.
echo =========================================
echo   LAN Chat stopped.
echo =========================================
echo.
pause
