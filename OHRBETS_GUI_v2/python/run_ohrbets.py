#!/usr/bin/env python3
"""
OHRBETS GUI Launcher Script

This script provides a simple command-line interface to launch different components
of the OHRBETS GUI system.

Usage:
    python run_ohrbets.py [component]

Components:
    app         - Run the main experiment application (default)
    dashboard   - Run the post-experiment analysis dashboard
    animated    - Run the animated visualization dashboard
    help        - Show this help message
"""

import os
import sys
import subprocess
import time
import webbrowser
import platform

# Default port assignments
APP_PORT = 8501
DASHBOARD_PORT = 8502
ANIMATED_PORT = 8503

def run_streamlit_app(script_name, port):
    """Run a Streamlit application on the specified port."""
    # Build the command
    cmd = ["streamlit", "run", script_name, "--server.port", str(port)]
    
    # Check if the script exists
    if not os.path.exists(script_name):
        print(f"Error: Script '{script_name}' not found.")
        return
    
    # Print startup message
    app_name = os.path.basename(script_name).replace(".py", "")
    print(f"Starting {app_name} on port {port}...")
    print(f"URL: http://localhost:{port}")
    
    # Automatically open browser after a short delay
    def open_browser():
        time.sleep(2)  # Wait for Streamlit to start
        webbrowser.open(f"http://localhost:{port}")
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start the Streamlit process
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print(f"\nStopping {app_name}...")
    except Exception as e:
        print(f"Error running {app_name}: {str(e)}")

def show_help():
    """Show help message."""
    print(__doc__)

def main():
    """Main function to parse arguments and launch the appropriate component."""
    # Determine the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        component = sys.argv[1].lower()
    else:
        component = "app"  # Default to main app
    
    # Launch the appropriate component
    if component == "app" or component == "experiment":
        run_streamlit_app("app.py", APP_PORT)
    elif component == "dashboard" or component == "analysis":
        run_streamlit_app("dashboard.py", DASHBOARD_PORT)
    elif component == "animated" or component == "animation":
        run_streamlit_app("animated_analysis.py", ANIMATED_PORT)
    elif component == "help" or component == "--help" or component == "-h":
        show_help()
    else:
        print(f"Unknown component: {component}")
        show_help()

if __name__ == "__main__":
    # Check if required packages are installed
    try:
        import streamlit
    except ImportError:
        print("Error: Streamlit package is not installed.")
        print("Please install required packages with: pip install -r requirements.txt")
        sys.exit(1)
    
    main() 