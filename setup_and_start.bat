@echo off
echo =========================================
echo       JEXI - Setup & Start
echo =========================================
echo.

echo 📋 JEXI Setup and Launch Script
echo.

REM Check if we're in the backend directory
if not exist "dev_server.py" (
    echo ❌ Please run this script from the backend directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo ✅ Backend directory confirmed
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Check frontend directory
if exist "..\frontend" (
    echo ✅ Frontend directory found
) else (
    echo ❌ Frontend directory not found
    echo Please ensure the frontend directory exists
    pause
    exit /b 1
)

echo.
echo 🚀 Starting JEXI Development Server...
echo 📁 Frontend: ..\frontend
echo 🌐 URL: http://localhost:8080
echo.
echo ⚠️  Make sure you have:
echo    1. Set up your Supabase project
echo    2. Run the SQL setup script in Supabase dashboard
echo    3. Configured environment variables
echo.
echo 🛑 Press Ctrl+C to stop the server
echo =========================================
echo.

python dev_server.py

echo.
echo 🎉 JEXI server stopped!
echo.
echo 📝 Next Steps:
echo    1. Open http://localhost:8080 in your browser
echo    2. Test the Supabase authentication
echo    3. Explore all the features
echo.
pause
