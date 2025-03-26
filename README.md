# OHRBETS GUI: Pavlovian Odor Conditioning System

## Overview

OHRBETS GUI (Operant Hardware for Rodent Behavioral Experiments & Tracking System) is a comprehensive platform for conducting Pavlovian odor conditioning experiments. Developed by the Stuber Lab at the University of Washington, this system integrates Arduino-based hardware control with a Streamlit-powered Python dashboard for experiment configuration, real-time monitoring, and data analysis.

## Features

### Hardware Control
- Arduino-based finite state machine for precise timing control
- Automated trial sequencing with CS+ (rewarded) and CS- (unrewarded) odor cues
- Solenoid control for water/reward delivery
- Lick detection and timestamping
- Real-time data transmission to GUI

### Streamlit Dashboard
- Real-time visualization of licking behavior
- Experiment configuration interface
- Comprehensive data analysis tools:
  - Lick raster plots by trial type
  - Mean lick rate timecourse
  - Statistical comparison of CS+ vs CS- trials
  - Learning curves across session
  - Focused comparison of cue period (0-2s) vs reward period (2-5s)
- Data simulation capabilities for testing and demonstration

## System Requirements

### Hardware
- Arduino Uno/Mega microcontroller
- Solenoid valves for odor delivery (2+)
- Reward solenoid
- Infrared beam break sensor for lick detection
- Appropriate power supply

### Software
- Python 3.9+
- Arduino IDE
- Required Python packages (see `OHRBETS_GUI_v2/python/requirements.txt`)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/stuberlab/ohrbets-gui.git
cd ohrbets-gui
```

2. Install Python dependencies:
```bash
pip install -r OHRBETS_GUI_v2/python/requirements.txt
```

3. Upload Arduino sketch:
   - Open `OHRBETS_GUI_v2/arduino/fsm_pavlovian_odor/fsm_pavlovian_odor.ino` in the Arduino IDE
   - Connect your Arduino board
   - Upload the sketch

## Usage

### Starting the Dashboard

Run the dashboard using the provided script:
```bash
cd OHRBETS_GUI_v2/python
./run_dashboard.sh
```

The dashboard will be available at http://localhost:8503

### Experiment Workflow

1. **Configure the Experiment**
   - Set animal ID and session parameters
   - Configure trial sequence (balanced 50% CS+, 50% CS-)
   - Set timing parameters (ITI, odor duration, reward duration)

2. **Connect Hardware**
   - Select the appropriate serial port
   - Connect to the Arduino

3. **Run the Experiment**
   - Send trial sequence to Arduino
   - Start the session
   - Monitor licking behavior in real-time

4. **Analyze Results**
   - View summary statistics (total licks, CS+ vs CS- comparison)
   - Examine lick rasters and heatmaps
   - Analyze learning curve over session
   - Export data for further analysis

## File Structure

```
OHRBETS_GUI/
├── OHRBETS_GUI_v2/
│   ├── arduino/
│   │   └── fsm_pavlovian_odor/
│   │       └── fsm_pavlovian_odor.ino  # Arduino finite state machine
│   └── python/
│       ├── analysis.py          # Data analysis functions
│       ├── dashboard.py         # Streamlit dashboard interface
│       ├── generate_test_data.py # Data simulation for testing
│       ├── requirements.txt     # Python dependencies
│       └── run_dashboard.sh     # Startup script
└── README.md                    # This file
```

## Data Format

### Event Codes
- 1: Trial Start
- 2: Trial End
- 3: Odor On
- 4: Odor Off
- 5: Reward On
- 6: Reward Off
- 7: Lick

### Output Files
- `pavlovian_[animal-id]_[timestamp].csv`: Contains all event timestamps and codes

## Simulated Data Profiles

For testing and demonstration, the system can generate simulated data with different licking patterns:
- **normal**: Standard conditioned response
- **robust**: Strong discrimination between CS+ and CS-
- **anticipatory**: Increased licking during cue before reward
- **nonlearner**: Poor discrimination between CS+ and CS-

## Troubleshooting

- **Serial Connection Issues**: Ensure the Arduino is connected and no other program is using the serial port
- **Missing Data**: Check that the Arduino is properly powered and the sketch is running
- **Visualization Issues**: Clear browser cache and restart the Streamlit application
- **Port Access Denied**: You may need to run with sudo/administrator permissions to access certain serial ports

## Contributing

We welcome contributions to the OHRBETS GUI project. Please feel free to submit issues or pull requests through our GitHub repository.

## Acknowledgments

This project was developed by the Stuber Lab at the University of Washington for studying the neural mechanisms of reward learning and motivated behavior.

## License

MIT License

## Contact

For questions or support, please contact the Stuber Lab at the University of Washington. 