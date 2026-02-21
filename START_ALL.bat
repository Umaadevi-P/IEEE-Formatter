@echo off
echo ========================================
echo IEEE Paper Formatter - Complete System
echo ========================================
echo.
echo Starting backend and frontend...
echo.

REM Start backend in a new window
start "IEEE Backend Server" cmd /k "python -m uvicorn app.main:app --reload"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Open frontend in default browser
echo Opening frontend in browser...
start index.html

echo.
echo ========================================
echo System Started!
echo ========================================
echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: Opened in your browser
echo.
echo To stop: Close the "IEEE Backend Server" window
echo.
pause
