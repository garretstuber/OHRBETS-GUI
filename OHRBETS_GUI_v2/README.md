# Pavlovian Odor Conditioning System

A complete system for running Pavlovian conditioning experiments with odor stimuli, including Arduino firmware for hardware control and a Python-based GUI for experiment control and data visualization. This system is part of the [OHRBETS (Open-Source Head-fixed Rodent Behavioral Experimental Training System)](https://github.com/agordonfennell/OHRBETS) platform, an open-source ecosystem of hardware and software for head-fixed behavior.

This implementation is based on the work described in:
> Gordon-Fennell, A., Barbakh, J. M., Utley, M. T., Singh, S., Bazzino, P., Gowrishankar, R., Bruchas, M. R., Roitman, M. F., & Stuber, G. D. (2023). An open-source platform for head-fixed operant and consummatory behavior. *eLife*, 12, e86183. [https://doi.org/10.7554/eLife.86183](https://elifesciences.org/articles/86183)

## Project Structure

```
OHRBETS_GUI_v2/
│
├── arduino/
│   └── fsm_pavlovian_odor/
│       └── fsm_pavlovian_odor.ino  # Arduino sketch for hardware control
│
└── python/
    ├── app.py            # Main Streamlit application for real-time experiment control
    ├── analysis.py       # Offline data analysis tool
    └── requirements.txt  # Python dependencies
```

## Hardware Setup

### Required Components

- Arduino board (Uno, Nano, or Mega recommended)
- Solenoid for odor delivery
- Solenoid for reward delivery
- MPR121 Capacitive Touch Sensor for lick detection
- Relays or MOSFET drivers for solenoids

### Wiring

Connect the hardware to the Arduino with the following pin configuration:

- **LED_PIN (13)**: Built-in LED for status indication
- **ODOR_PIN (17)**: Solenoid for odor delivery
- **REWARD_PIN (4)**: Solenoid for reward delivery
- **MPR121 (I2C)**: Capacitive touch sensor for lick detection (SDA/SCL pins)

### Capacitive Lickometer Setup

The system uses an MPR121 capacitive touch sensor for precise lick detection. This provides several advantages over traditional contact-based lick sensors:

- No physical contact required
- Higher sensitivity and reliability
- Reduced noise and false positives
- Configurable sensitivity thresholds

To set up the lickometer:
1. Connect the MPR121 to the Arduino's I2C pins (SDA/SCL)
2. The sensor is configured with medium sensitivity (thresholds: 9, 4)
3. Minimum inter-lick interval is set to 67ms to prevent double-counting
4. The lick sensor is monitored continuously during trials

## Software Installation

### Arduino

1. Open the Arduino IDE
2. Install the Adafruit MPR121 library:
   ```
   Tools -> Manage Libraries -> Search for "Adafruit MPR121" -> Install
   ```
3. Load the `fsm_pavlovian_odor.ino` sketch
4. Select your Arduino board type and port
5. Upload the sketch to your Arduino

### Python

1. Install Python 3.8 or higher
2. Navigate to the project directory
3. Install dependencies:
   ```
   pip install -r python/requirements.txt
   ```

## Usage

### Running the Experiment Control GUI

1. Navigate to the project directory
2. Start the Streamlit app:
   ```
   streamlit run python/app.py
   ```
3. Open your web browser to the provided URL (usually http://localhost:8501)

### Experiment Workflow

1. Connect to Arduino by selecting the correct serial port
2. Set experiment parameters (timing, trial sequence)
3. Send the sequence to Arduino
4. Start the session
5. Monitor real-time data visualization
6. Export data when finished

### Data Analysis

1. Start the analysis tool:
   ```
   streamlit run python/analysis.py
   ```
2. Upload exported CSV data
3. View statistics and visualizations

## Event Codes

The system uses the following event codes for data logging:

- **EVENT_TRIAL_START (1)**: Beginning of a trial
- **EVENT_TRIAL_END (2)**: End of a trial
- **EVENT_ODOR_ON (3)**: Odor valve opened
- **EVENT_ODOR_OFF (4)**: Odor valve closed
- **EVENT_REWARD_ON (5)**: Reward valve opened
- **EVENT_REWARD_OFF (6)**: Reward valve closed
- **EVENT_LICK (7)**: Lick detected
- **EVENT_SESSION_START (8)**: Session start event

## Troubleshooting

### Common Issues

1. **No serial port found**: Check USB connection and driver installation
2. **No data received**: Verify Arduino is properly connected and running the correct sketch
3. **Valves not activating**: Check wiring and power supply for solenoids
4. **Lick detection issues**: 
   - Verify MPR121 is properly connected to I2C pins
   - Check sensor sensitivity settings
   - Ensure proper grounding of the lick spout

### Debugging

- Monitor the Arduino serial output (115200 baud rate)
- Check the Streamlit console for error messages
- Verify timing parameters are appropriate for your experiment
- Use the lick test function to verify lick detection 