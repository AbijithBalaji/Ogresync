@echo off
REM Ogresync Executable Builder for Windows
REM This batch file builds the Ogresync.exe executable

echo Building Ogresync Executable...
echo ================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Install/upgrade dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Run the build script
echo Starting build process...
python build_exe.py

REM Check if build was successful
if exist "dist\Ogresync.exe" (
    echo.
    echo SUCCESS: Ogresync.exe has been created in the dist folder
    echo You can now run dist\Ogresync.exe
    echo.
) else (
    echo.
    echo ERROR: Build failed - Ogresync.exe was not created
    echo Please check the error messages above
    echo.
)

pause
