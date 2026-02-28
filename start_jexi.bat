@echo off
echo =========================================
echo       JEXI - Personal AI Life OS
echo =========================================
echo.

echo Starting JEXI Backend Server...
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Check if frontend directory exists
if exist "..\frontend" (
    echo ✅ Frontend directory found
) else (
    echo ❌ Frontend directory not found
    echo Please ensure the frontend directory exists
    pause
    exit /b 1
)

REM Start the development server
echo 🚀 Starting development server on port 8080...
echo 📁 Serving frontend from: ..\frontend
echo 🌐 Open your browser and navigate to: http://localhost:8080
echo.
echo ⚠️  Note: This is a development server for testing
echo 🛑 Press Ctrl+C to stop the server
echo =========================================
echo.

python dev_server.py

echo.
echo Server stopped.
pause
