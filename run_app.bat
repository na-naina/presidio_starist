@echo off
REM =============================================================================
REM STARIST - Application Launcher for Windows
REM =============================================================================
REM This batch file starts the Presidio de-identification tool on Windows
REM Run this file directly (double-click)

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "presidio-venv" (
    echo Virtual environment not found!
    echo Please run install_ubuntu.sh first to set up the application.
    echo.
    echo For Windows installation, see README.md for WSL2 setup instructions.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call presidio-venv\Scripts\activate.bat

REM Check if the main script exists
if not exist "1_📂_Batch_Anonymization.py" (
    echo Error: 1_📂_Batch_Anonymization.py not found!
    pause
    exit /b 1
)

REM Clear screen and display banner
cls
echo.
echo ════════════════════════════════════════════════════════════════════════
echo                         STARIST is Starting
echo                  Stalking Threat AI Recognition and
echo                     Identification Support Tool
echo ════════════════════════════════════════════════════════════════════════
echo.
echo Opening application in your browser...
echo If the browser doesn't open, navigate to: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the application
streamlit run "1_📂_Batch_Anonymization.py"

pause
