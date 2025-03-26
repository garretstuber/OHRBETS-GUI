# Pavlovian Odor Conditioning System

A complete system for running Pavlovian conditioning experiments with odor stimuli, including Arduino firmware for hardware control and a Python-based GUI for experiment control and data visualization.

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
- Solenoids for odor delivery (2x)
- Solenoid for reward delivery (1x)
- Lick sensor (optional)
- Relays or MOSFET drivers for solenoids

### Wiring

Connect the hardware to the Arduino with the following pin configuration:

- **LED_PIN (13)**: Built-in LED for status indication
- **ODOR1_PIN (2)**: Solenoid for CS+ odor
- **ODOR2_PIN (3)**: Solenoid for CS- odor
- **REWARD_PIN (4)**: Solenoid for reward delivery
- **LICK_PIN (5)**: Optional lick detector input

## Software Installation

### Arduino

1. Open the Arduino IDE
2. Load the `fsm_pavlovian_odor.ino` sketch
3. Select your Arduino board type and port
4. Upload the sketch to your Arduino

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

## Troubleshooting

### Common Issues

1. **No serial port found**: Check USB connection and driver installation
2. **No data received**: Verify Arduino is properly connected and running the correct sketch
3. **Valves not activating**: Check wiring and power supply for solenoids

### Debugging

- Monitor the Arduino serial output (115200 baud rate)
- Check the Streamlit console for error messages
- Verify timing parameters are appropriate for your experiment 