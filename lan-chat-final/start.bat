@echo off
echo.
echo =========================================
echo   LAN CHAT - Starting...
echo =========================================
echo.

REM Try Python launcher first (most reliable on Windows)
set PYTHON=
py --version >nul 2>&1 && set PYTHON=py
if not "%PYTHON%"=="" goto :found

REM Try python in PATH
python --version >nul 2>&1 && set PYTHON=python
if not "%PYTHON%"=="" goto :found

REM Try common install locations
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set PYTHON="%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :found
)

echo ERROR: Python not found. Please install Python from https://python.org
pause
exit /b 1

:found
echo Python found: %PYTHON%
echo.
echo Installing required packages...
%PYTHON% -m pip install flask flask-socketio --quiet
echo.
echo Bundling offline assets (emoji picker)...
%PYTHON% download_assets.py
echo.
echo Starting LAN Chat server...
echo.

REM Get local IP
for /f "delims=" %%a in ('powershell -NoProfile -Command "([System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) | Where-Object {$_.AddressFamily -eq 'InterNetwork'} | Select-Object -First 1).IPAddressToString"') do set LOCAL_IP=%%a

echo =========================================
echo   LAN Chat is running!
echo =========================================
echo.
if not "%LOCAL_IP%"=="" (
    echo Your IP: http://%LOCAL_IP%:5000
    echo.
    echo Share this link with others on your network:
    echo http://%LOCAL_IP%:5000
) else (
    echo Access at: http://localhost:5000
    echo.
)
echo =========================================
echo.

REM Open browser automatically
if not "%LOCAL_IP%"=="" (
    start http://%LOCAL_IP%:5000
) else (
    start http://localhost:5000
)

%PYTHON% server.py
pause
