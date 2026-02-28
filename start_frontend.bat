@echo off
echo =========================================
echo       JEXI - Personal AI Life OS
echo =========================================
echo.

echo Starting JEXI Frontend Only...
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Check if frontend directory exists
if exist "frontend" (
    echo ✅ Frontend directory found
    cd frontend
) else (
    echo ❌ Frontend directory not found
    echo Please ensure the frontend directory exists
    pause
    exit /b 1
)

echo 🚀 Starting frontend server on port 8080...
echo 📁 Serving files from: %CD%
echo 🌐 Open your browser and navigate to: http://localhost:8080
echo.
echo ⚠️  Note: This is a development server for testing
echo 🛑 Press Ctrl+C to stop the server
echo =========================================
echo.

python -m http.server 8080

echo.
echo Server stopped.
pause
