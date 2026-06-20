@echo off
setlocal

REM ── Kill any process on port 8000 ────────────────────────────────────────────
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8000" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM ── Launch server from the backend directory ──────────────────────────────────
cd /d "%~dp0backend"
python -m uvicorn app:asgi_app --host 0.0.0.0 --port 8000 --log-level info
endlocal
