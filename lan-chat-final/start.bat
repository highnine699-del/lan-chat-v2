@echo off
echo.
echo =========================================
echo   LAN CHAT - Starting...
echo =========================================
echo.

REM Try common Python locations
set PYTHON=
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else (
    python --version >nul 2>&1 && set PYTHON=python
)

if "%PYTHON%"=="" (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

echo Python found: %PYTHON%
echo.
echo Installing required packages...
%PYTHON% -m pip install flask flask-socketio --quiet
echo.
echo Starting LAN Chat server...
echo.
echo =========================================
echo   Share your IP with classmates!
echo   They open it in their browser.
echo =========================================
echo.

%PYTHON% server.py
pause
