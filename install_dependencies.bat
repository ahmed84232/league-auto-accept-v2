@echo off
title Python Dependencies Installer
echo ================================
echo   Installing Python Packages
echo ================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python is NOT installed or not added to PATH.
    echo     Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

echo [OK] Python detected
echo.

echo [..] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [X] Failed to upgrade pip
    pause
    exit /b 1
)

echo.
echo [..] Installing dependencies...
echo.

python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [X] Dependency installation failed
    pause
    exit /b 1
)

echo.
echo [OK] All dependencies installed successfully!
echo.
pause
