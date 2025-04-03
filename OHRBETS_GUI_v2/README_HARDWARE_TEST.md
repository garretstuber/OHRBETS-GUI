# OHRBETS Hardware Test System

This system provides a direct hardware testing interface for the OHRBETS (Olfactory Head-fixed Reward-Based Entrainment Training System) solenoids and lick sensor, bypassing the state machine for simplified troubleshooting.

## Components

1. **Arduino Sketch**: `arduino/hardware_test/hardware_test.ino`
   - Uses simple blocking delay() calls for precise timing
   - Directly controls solenoids without state machine complexity
   - Implements the exact timing requirements:
     - Odor: exactly 2 seconds on
     - Reward: 40ms on, 140ms off, 40ms on pattern
   - Tests MPR121 capacitive lick sensor

2. **Python Interface**: `hardware_test.py`
   - Command-line interface for testing
   - Streamlit web interface for easier interaction
   - Auto-detection of serial ports

## Setup Instructions

### 1. Upload the Arduino Sketch

1. Open the Arduino IDE
2. Install the Adafruit MPR121 library:
   ```
   Tools -> Manage Libraries -> Search for "Adafruit MPR121" -> Install
   ```
3. Open the file: `OHRBETS_GUI_v2/arduino/hardware_test/hardware_test.ino`
4. Select your Arduino board type and port
5. Click Upload
6. Wait for "Upload complete" message

### 2. Run the Hardware Test Application

#### Using Streamlit (recommended):

```bash
# Make the script executable (one-time)
chmod +x run_hardware_test.sh

# Run the application
./run_hardware_test.sh
```

This will open a browser window with the interface.

#### Using Command Line:

```bash
# Run directly
python hardware_test.py

# To see available ports
python hardware_test.py --list-ports

# To specify a port
python hardware_test.py --port /dev/ttyACM0  # Change to your port
```

## Available Commands

- `TEST_ODOR` - Run odor test (2s)
- `TEST_REWARD` - Run reward test (40ms-140ms-40ms)
- `TEST_LICK` - Start lick sensor monitoring
- `STOP_LICK_TEST` - Stop lick sensor monitoring
- `ODOR_ON` - Turn odor valve on
- `ODOR_OFF` - Turn odor valve off
- `REWARD_ON` - Turn reward valve on
- `REWARD_OFF` - Turn reward valve off
- `STATUS` - Get current status
- `RESET` - Reset all outputs

## Troubleshooting

1. **Cannot connect to Arduino**:
   - Check that the Arduino is connected via USB
   - Verify the correct port is selected
   - Try unplugging and reconnecting the Arduino
   - Restart the application

2. **Solenoids not responding**:
   - Verify wiring connections (ODOR_PIN = 17, REWARD_PIN = 4)
   - Ensure power supply is connected and on
   - Check serial monitor for debugging messages

3. **Lick sensor not working**:
   - Verify MPR121 is properly connected to I2C pins (SDA/SCL)
   - Check sensor sensitivity settings (default: 9, 4)
   - Ensure proper grounding of the lick spout
   - Use the lick test function to verify detection

4. **Timing issues**:
   - The hardware_test.ino uses direct blocking delay() calls
   - This ensures precise timing without state machine complications
   - If timing is still incorrect, verify your power supply can handle the load 