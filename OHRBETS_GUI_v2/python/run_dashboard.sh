#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    exit 1
fi

# Check if streamlit is installed
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "Installing required dependencies..."
    python3 -m pip install streamlit pandas numpy plotly scipy
fi

# Run the dashboard
echo "Starting Pavlovian Conditioning Analysis Dashboard..."
streamlit run dashboard.py 