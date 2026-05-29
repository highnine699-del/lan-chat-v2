@echo off
REM Kill any Python process on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8000"') do (
    taskkill /F /PID %%a
)

REM Start the server
cd /d "C:\Users\AY ADVANCE TECH\Documents\lan-chat-v2\backend"
python main.py
