#!/bin/bash

# Run the hardware test GUI
echo "Starting OHRBETS Hardware Test GUI..."
echo "Press Ctrl+C to stop"

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Streamlit is not installed. Installing required packages..."
    pip install -r requirements.txt
fi

# Run the hardware test app
streamlit run hardware_test.py --server.port 8505 