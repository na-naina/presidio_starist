#!/bin/bash
# =============================================================================
# STARIST - Docker Startup Script (Linux/Mac)
# =============================================================================
# Simple script to start the STARIST anonymization tool
# Double-click or run: ./docker/start.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=============================================="
echo "  STARIST - Police Data Anonymization Tool"
echo "=============================================="
echo -e "${NC}"

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running.${NC}"
    echo "Please start Docker Desktop or the Docker service."
    exit 1
fi

echo -e "${GREEN}Docker is running.${NC}"

# Check for NVIDIA GPU support
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}NVIDIA GPU detected:${NC}"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    GPU_AVAILABLE=true
else
    echo -e "${YELLOW}Warning: NVIDIA GPU not detected. Running in CPU mode.${NC}"
    GPU_AVAILABLE=false
fi

# Check if image exists, if not build it
if ! docker image inspect starist:gpu &> /dev/null; then
    echo -e "${YELLOW}Docker image not found. Building (this may take 10-20 minutes)...${NC}"
    docker compose build
fi

# Stop any existing container
echo "Stopping any existing STARIST containers..."
docker compose down 2>/dev/null || true

# Start the container
echo -e "${GREEN}Starting STARIST...${NC}"
docker compose up -d

# Wait for the service to be ready
echo "Waiting for service to start..."
for i in {1..60}; do
    if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo -e "${GREEN}STARIST is ready!${NC}"
        break
    fi
    sleep 2
    echo -n "."
done

echo ""
echo -e "${BLUE}=============================================="
echo "  STARIST is running!"
echo "=============================================="
echo -e "${NC}"
echo -e "Open your browser to: ${GREEN}http://localhost:8501${NC}"
echo ""
echo "Commands:"
echo "  Stop:    docker compose down"
echo "  Logs:    docker compose logs -f"
echo "  Status:  docker compose ps"
echo ""

# Try to open browser (optional)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8501 2>/dev/null &
elif command -v open &> /dev/null; then
    open http://localhost:8501 2>/dev/null &
fi
