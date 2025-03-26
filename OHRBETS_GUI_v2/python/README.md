# OHRBETS GUI: Python Interface

## Overview

This Python interface provides a user-friendly graphical interface for controlling the OHRBETS (Olfactory Head-fixed Reward-Based Entrainment Training System) using an Arduino-based state machine. The system is designed for Pavlovian odor conditioning experiments where precise timing of odor delivery and reward is critical.

## Features

- Real-time control of the Arduino-based Pavlovian conditioning system
- Live monitoring of experimental events (trial starts, odor delivery, rewards, licks)
- Dynamic visualization of behavioral data
- Hardware testing interface for ensuring all components work properly
- Data export for offline analysis

## New Visualization Features

The system now includes three distinct visualization interfaces:

1. **Main Experiment Interface (app.py)**
   - Real-time trial timeline visualization
   - Enhanced raster plots with trial-by-trial response visualization
   - Lick rate analysis during the experiment

2. **Post-Experiment Dashboard (dashboard.py)**
   - Comprehensive analysis of experimental data
   - Statistical comparisons between CS+ and CS- trials
   - Multiple visualization types (raster, heatmap, learning curves)
   - Report generation

3. **Animated Analysis Dashboard (animated_analysis.py)**
   - Trial-by-trial animated heatmaps showing learning progression
   - Animated learning curves demonstrating behavioral acquisition
   - Dynamic visualization of response profiles
   - Interactive animations with playback controls

## Installation

1. Install required packages:

```bash
pip install -r requirements.txt
```

2. Connect Arduino to USB port
3. Upload the `fsm_pavlovian_odor.ino` sketch to the Arduino

## Running the Application

You can use the convenient `run_ohrbets.py` script to launch different components:

```bash
# Run the main experiment interface (default)
python run_ohrbets.py app

# Run the post-experiment analysis dashboard
python run_ohrbets.py dashboard

# Run the animated visualization dashboard
python run_ohrbets.py animated

# Show help
python run_ohrbets.py help
```

Alternatively, you can run each component directly with Streamlit:

```bash
# Main experiment interface
streamlit run app.py

# Post-experiment analysis dashboard
streamlit run dashboard.py

# Animated visualization dashboard
streamlit run animated_analysis.py
```

## Hardware Connections

The software expects the Arduino to have the following connections:

- Pin 2: Odor 1 solenoid (CS+)
- Pin 3: Odor 2 solenoid (CS-)
- Pin 4: Reward solenoid
- Pin 5: Lick sensor

## Usage Guide

### Experiment Setup

1. Connect to Arduino using the dropdown menu
2. Test hardware components to ensure proper function
3. Configure experiment parameters:
   - Inter-trial interval (ITI)
   - Odor presentation duration
   - Reward parameters
4. Set trial sequence (or generate a random balanced sequence)
5. Start the session

### During Experiment

- Monitor lick behavior in real-time
- Track progress through trial sequence
- Visualize response patterns as they develop
- Abort session if necessary

### After Experiment

- Download data as CSV
- Use the dashboard for detailed analysis
- Use the animated analysis for engaging visualizations of learning

## Contributing

Contributions to improve the OHRBETS GUI are welcome! Please feel free to submit pull requests or open issues on GitHub.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 