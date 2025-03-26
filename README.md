# OHRBETS GUI: Olfactory Head-fixed Reward-Based Entrainment Training System

A comprehensive system for Pavlovian odor conditioning experiments, featuring precise Arduino-based hardware control and advanced Python visualization.

![OHRBETS System](docs/system_overview.png)

## Overview

OHRBETS GUI is a complete solution for conducting Pavlovian conditioning experiments using odor cues and reward delivery. The system consists of:

1. **Arduino Controller**: A finite state machine that precisely controls hardware timing and event logging
2. **Python Interface**: An intuitive GUI for experiment control and data visualization
3. **Analysis Dashboard**: Tools for post-experiment analysis and visualization

## Key Features

- **Precise Timing Control**: Microsecond-precision for all experimental events
- **Real-time Visualization**: Monitor behavior as it happens
- **Hardware Testing**: Built-in tools for validating all system components
- **Data Analysis**: Comprehensive tools for understanding behavioral responses
- **Animated Visualizations**: Dynamic representations of learning progression
- **Safety Features**: Prevents hardware failures and experimental errors

## New Visualization Features

The system now includes enhanced visualization capabilities:

### Real-time Experiment Visualization
- Trial timeline showing events with precise timing
- Dynamic raster plots that update during the experiment
- Real-time lick rate analysis
- CS+ vs CS- response comparison

### Animated Analysis Dashboard
- Trial-by-trial animated heatmaps showing learning progression
- Animated learning curves demonstrating behavioral acquisition
- Dynamic visualization of response profiles
- Interactive animations with playback controls

### Post-Experiment Dashboard
- Comprehensive statistical analysis
- Multiple visualization types
- Report generation

## Hardware Requirements

- Arduino Uno or compatible board
- Solenoid valves for odor delivery (2)
- Solenoid valve for water reward
- Lick sensor (capacitive or optical)
- Appropriate tubing and connectors
- Power supply for solenoids (12V recommended)

## Software Requirements

- Arduino IDE (for uploading firmware)
- Python 3.7 or higher
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/OHRBETS_GUI.git
cd OHRBETS_GUI
```

2. Install required Python packages:
```bash
pip install -r OHRBETS_GUI_v2/python/requirements.txt
```

3. Upload the Arduino firmware:
   - Open `OHRBETS_GUI_v2/arduino/fsm_pavlovian_odor/fsm_pavlovian_odor.ino` in the Arduino IDE
   - Connect your Arduino board via USB
   - Click Upload

## Usage

### Running the System

You can use the convenient `run_ohrbets.py` script to launch different components:

```bash
# Navigate to the Python directory
cd OHRBETS_GUI_v2/python

# Run the main experiment interface (default)
python run_ohrbets.py app

# Run the post-experiment analysis dashboard
python run_ohrbets.py dashboard

# Run the animated visualization dashboard
python run_ohrbets.py animated

# Show help
python run_ohrbets.py help
```

### Hardware Setup

1. Connect hardware components to Arduino pins:
   - Pin 2: Odor 1 solenoid (CS+)
   - Pin 3: Odor 2 solenoid (CS-)
   - Pin 4: Reward solenoid
   - Pin 5: Lick sensor

2. Connect Arduino to computer via USB

### Running an Experiment

1. Launch the main app: `python run_ohrbets.py app`
2. Connect to Arduino using the dropdown menu
3. Test hardware components using the Testing section
4. Configure experiment parameters:
   - Timing (ITI, odor duration, etc.)
   - Trial sequence
5. Start session and monitor results in real-time

### Data Analysis

1. After the experiment, download the data as CSV
2. Launch the analysis dashboard: `python run_ohrbets.py dashboard`
3. Upload the CSV file to analyze results
4. For animated visualizations: `python run_ohrbets.py animated`

## Folder Structure

- `OHRBETS_GUI_v2/` - Main project directory
  - `arduino/` - Arduino firmware
    - `fsm_pavlovian_odor/` - Finite state machine implementation
  - `python/` - Python GUI and analysis tools
    - `app.py` - Main experiment interface
    - `dashboard.py` - Post-experiment analysis dashboard
    - `animated_analysis.py` - Animated visualization dashboard
    - `real_time_viz.py` - Real-time visualization components
    - `run_ohrbets.py` - Launcher script

## Contributing

Contributions to improve OHRBETS GUI are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Stuber Lab at UNC Chapel Hill for inspiration and testing
- The open-source community for the libraries that made this project possible

## Contact

For questions or support, please contact the Stuber Lab at the University of Washington. 