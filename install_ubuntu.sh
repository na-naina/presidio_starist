#!/bin/bash
# =============================================================================
# STARIST Installation Script for Ubuntu 24.04
# Stalking Threat AI Recognition (and) Identification Support Tool
# =============================================================================

set -e  # Exit on any error

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                    STARIST Installation Script                         ║"
echo "║              For Ubuntu 24.04 LTS (and compatible)                     ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running on Ubuntu
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        print_warning "This script is designed for Ubuntu. Detected: $ID"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo "Step 1/6: Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    build-essential \
    gcc \
    g++ \
    git \
    curl

print_status "System dependencies installed"

echo ""
echo "Step 2/6: Creating Python virtual environment..."
# Remove existing venv if present
if [ -d "presidio-venv" ]; then
    print_warning "Removing existing virtual environment..."
    rm -rf presidio-venv
fi

python3.10 -m venv presidio-venv
source presidio-venv/bin/activate
print_status "Virtual environment created and activated"

echo ""
echo "Step 3/6: Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel
print_status "Pip and setuptools upgraded"

echo ""
echo "Step 4/6: Installing Python dependencies (this may take several minutes)..."
pip install -r requirements.txt
print_status "Python dependencies installed"

echo ""
echo "Step 5/6: Downloading spaCy language models..."
python -m spacy download en_core_web_lg
python -m spacy download en_core_web_sm
print_status "Language models downloaded"

echo ""
echo "Step 6/6: Verifying installation..."
python -c "import presidio_analyzer; import presidio_anonymizer; import streamlit; print('All core packages imported successfully')"
print_status "Installation verified"

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                    Installation Complete!                              ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "To start the application, run:"
echo ""
echo "    source presidio-venv/bin/activate"
echo "    streamlit run 1_📂_Batch_Anonymization.py"
echo ""
echo "The application will open in your browser at http://localhost:8501"
echo ""
print_warning "Note: First run will download NER models (~1.5GB). This is normal."
echo ""
