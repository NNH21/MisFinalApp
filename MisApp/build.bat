@echo off
echo ================================================================
echo MIS Smart Assistant - Quick Build Script
echo ================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

echo Python found. Starting build process...
echo.

REM Install required dependencies
echo Installing build dependencies...
pip install pyinstaller pillow

REM Run the build script
echo.
echo Running build script...
python build_exe.py

echo.
echo Build process completed.
pause
