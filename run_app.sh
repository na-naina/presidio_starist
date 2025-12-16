#!/bin/bash
# =============================================================================
# STARIST - Application Launcher
# =============================================================================
# This script starts the Presidio de-identification tool
# Run this file directly (double-click or ./run_app.sh)

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "presidio-venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run ./install_ubuntu.sh first to set up the application."
    echo ""
    read -p "Would you like to run the installation now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        bash install_ubuntu.sh
    else
        exit 1
    fi
fi

# Activate virtual environment
source presidio-venv/bin/activate

# Check if the main script exists
if [ ! -f "1_📂_Batch_Anonymization.py" ]; then
    echo "Error: 1_📂_Batch_Anonymization.py not found!"
    exit 1
fi

# Start the application
echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                         STARIST is Starting                            ║"
echo "║                  Stalking Threat AI Recognition &                      ║"
echo "║                     Identification Support Tool                         ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Opening application in your browser..."
echo "If the browser doesn't open, navigate to: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run 1_📂_Batch_Anonymization.py
