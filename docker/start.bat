@echo off
REM =============================================================================
REM STARIST - Docker Startup Script (Windows)
REM =============================================================================
REM Simple script to start the STARIST anonymization tool
REM Double-click or run: docker\start.bat
REM =============================================================================

echo.
echo ==============================================
echo   STARIST - Police Data Anonymization Tool
echo ==============================================
echo.

REM Change to project directory
cd /d "%~dp0\.."

REM Check if Docker is installed
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker is not installed.
    echo Please install Docker Desktop: https://docs.docker.com/desktop/windows/install/
    pause
    exit /b 1
)

REM Check if Docker daemon is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker daemon is not running.
    echo Please start Docker Desktop.
    pause
    exit /b 1
)

echo Docker is running.

REM Check for NVIDIA GPU
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo NVIDIA GPU detected:
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
) else (
    echo Warning: NVIDIA GPU not detected. Running in CPU mode.
)

REM Check if image exists, build if needed
docker image inspect starist:gpu >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Docker image not found. Building (this may take 10-20 minutes)...
    docker compose build
)

REM Stop any existing container
echo Stopping any existing STARIST containers...
docker compose down 2>nul

REM Start the container
echo Starting STARIST...
docker compose up -d

REM Wait for service to be ready
echo Waiting for service to start...
timeout /t 10 /nobreak >nul

echo.
echo ==============================================
echo   STARIST is running!
echo ==============================================
echo.
echo Open your browser to: http://localhost:8501
echo.
echo Commands:
echo   Stop:    docker compose down
echo   Logs:    docker compose logs -f
echo   Status:  docker compose ps
echo.

REM Open browser
start http://localhost:8501

pause
