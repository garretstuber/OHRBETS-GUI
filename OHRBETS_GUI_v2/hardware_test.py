#!/usr/bin/env python3
# hardware_test.py - Interface for testing OHRBETS hardware components
# Created: March 26, 2025
#
# This utility interfaces with the hardware_test.ino sketch located at:
# OHRBETS_GUI_v2/arduino/hardware_test/hardware_test.ino

import serial
import time
import argparse
import sys
import glob
import os
import streamlit as st
import threading
import queue

# Find available serial ports
def find_arduino_ports():
    """Find potential Arduino serial ports on the system."""
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(32)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
        # Add common macOS Arduino paths
        ports.extend(glob.glob('/dev/cu.usbmodem*'))
    else:
        raise EnvironmentError('Unsupported platform')
    
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    
    return result

# Arduino communication class
class ArduinoInterface:
    def __init__(self, port, baudrate=115200, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connected = False
        self.message_queue = queue.Queue()
        self.reader_thread = None
        self.running = False
        
    def connect(self):
        """Connect to the Arduino and initialize the serial connection."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # Wait for Arduino to reset after connection
            self.connected = True
            self.running = True
            self.reader_thread = threading.Thread(target=self._read_serial, daemon=True)
            self.reader_thread.start()
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the Arduino."""
        self.running = False
        if self.reader_thread:
            if self.reader_thread.is_alive():
                self.reader_thread.join(timeout=1.0)
            self.reader_thread = None
            
        if self.connected and self.ser:
            self.ser.close()
            self.connected = False
    
    def send_command(self, command):
        """Send a command to the Arduino."""
        if not self.connected or not self.ser:
            print("Not connected to Arduino")
            return False
            
        try:
            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'
            self.ser.write(command.encode('utf-8'))
            self.ser.flush()
            return True
        except serial.SerialException as e:
            print(f"Error sending command: {e}")
            return False
    
    def _read_serial(self):
        """Read from the serial port in a separate thread."""
        while self.running and self.connected:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').rstrip()
                    if line:
                        self.message_queue.put(line)
                else:
                    time.sleep(0.01)  # Small sleep to prevent CPU hogging
            except Exception as e:
                print(f"Error reading from serial: {e}")
                break
                
    def get_messages(self):
        """Get all messages from the queue."""
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages

# Command-line interface
def run_cli():
    parser = argparse.ArgumentParser(description='OHRBETS Hardware Test Utility')
    parser.add_argument('--port', help='Serial port for Arduino')
    parser.add_argument('--list-ports', action='store_true', help='List available serial ports')
    args = parser.parse_args()
    
    if args.list_ports:
        ports = find_arduino_ports()
        print("Available ports:")
        for port in ports:
            print(f"  {port}")
        return
        
    port = args.port
    if not port:
        ports = find_arduino_ports()
        if not ports:
            print("No serial ports found")
            return
        port = ports[0]
        print(f"Using first available port: {port}")
    
    arduino = ArduinoInterface(port)
    if not arduino.connect():
        print("Failed to connect to Arduino")
        return
        
    print("Connected to Arduino. Type 'help' for commands, 'exit' to quit.")
    
    try:
        while True:
            # Check for any messages
            messages = arduino.get_messages()
            for msg in messages:
                print(f"← {msg}")
                
            cmd = input("→ ").strip()
            if not cmd:
                continue
                
            if cmd.lower() == 'exit':
                break
                
            if cmd.lower() == 'help':
                print("Commands:")
                print("  TEST_ODOR    - Test odor solenoid (2s)")
                print("  TEST_REWARD  - Test reward solenoid (40ms-140ms-40ms)")
                print("  ODOR_ON      - Turn odor on")
                print("  ODOR_OFF     - Turn odor off")
                print("  REWARD_ON    - Turn reward on")
                print("  REWARD_OFF   - Turn reward off")
                print("  STATUS       - Get current status")
                print("  RESET        - Reset all outputs")
                print("  HELP         - Show this help")
                print("  EXIT         - Exit program")
                continue
                
            arduino.send_command(cmd)
            # Give a little time for the Arduino to respond
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        arduino.disconnect()
        print("Disconnected from Arduino")

# Streamlit web interface
def run_streamlit():
    st.set_page_config(
        page_title="OHRBETS Hardware Test",
        page_icon="🔬",
        layout="wide"
    )
    
    st.title("OHRBETS Hardware Test Interface")
    st.write("Test and control solenoids directly")
    
    # Sidebar for connection settings
    with st.sidebar:
        st.header("Connection Settings")
        ports = find_arduino_ports()
        selected_port = st.selectbox("Select Serial Port", ports, index=0 if ports else None)
        
        connect_button = st.button("Connect")
        disconnect_button = st.button("Disconnect")
    
    # Main area
    col1, col2 = st.columns(2)
    
    # Odor control column
    with col1:
        st.header("Odor Control")
        odor_test = st.button("🧪 Test Odor (2s)", key="odor_test")
        odor_col1, odor_col2 = st.columns(2)
        with odor_col1:
            odor_on = st.button("🟢 Odor ON", key="odor_on")
        with odor_col2:
            odor_off = st.button("🔴 Odor OFF", key="odor_off")
    
    # Reward control column
    with col2:
        st.header("Reward Control")
        reward_test = st.button("🧪 Test Reward (40-140-40ms)", key="reward_test")
        reward_col1, reward_col2 = st.columns(2)
        with reward_col1:
            reward_on = st.button("🟢 Reward ON", key="reward_on")
        with reward_col2:
            reward_off = st.button("🔴 Reward OFF", key="reward_off")
    
    # Status area
    st.header("Status")
    status_button = st.button("Refresh Status")
    reset_button = st.button("Reset All")
    
    # Log area
    st.header("Log")
    log_container = st.empty()
    
    # Initialize session state
    if 'arduino' not in st.session_state:
        st.session_state.arduino = None
        st.session_state.connected = False
        st.session_state.log = []
        st.session_state.status = {"ODOR": "OFF", "REWARD": "OFF"}
    
    # Handle connection/disconnection
    if connect_button and not st.session_state.connected and selected_port:
        arduino = ArduinoInterface(selected_port)
        if arduino.connect():
            st.session_state.arduino = arduino
            st.session_state.connected = True
            st.session_state.log.append(f"Connected to {selected_port}")
            st.experimental_rerun()
    
    if disconnect_button and st.session_state.connected:
        if st.session_state.arduino:
            st.session_state.arduino.disconnect()
        st.session_state.arduino = None
        st.session_state.connected = False
        st.session_state.log.append("Disconnected")
        st.experimental_rerun()
    
    # Process button actions
    if st.session_state.connected and st.session_state.arduino:
        arduino = st.session_state.arduino
        
        # Odor buttons
        if odor_test:
            arduino.send_command("TEST_ODOR")
            st.session_state.log.append("→ TEST_ODOR")
        
        if odor_on:
            arduino.send_command("ODOR_ON")
            st.session_state.log.append("→ ODOR_ON")
        
        if odor_off:
            arduino.send_command("ODOR_OFF")
            st.session_state.log.append("→ ODOR_OFF")
        
        # Reward buttons
        if reward_test:
            arduino.send_command("TEST_REWARD")
            st.session_state.log.append("→ TEST_REWARD")
        
        if reward_on:
            arduino.send_command("REWARD_ON")
            st.session_state.log.append("→ REWARD_ON")
        
        if reward_off:
            arduino.send_command("REWARD_OFF")
            st.session_state.log.append("→ REWARD_OFF")
        
        # Status button
        if status_button:
            arduino.send_command("STATUS")
            st.session_state.log.append("→ STATUS")
        
        # Reset button
        if reset_button:
            arduino.send_command("RESET")
            st.session_state.log.append("→ RESET")
        
        # Get messages from Arduino
        messages = arduino.get_messages()
        for msg in messages:
            st.session_state.log.append(f"← {msg}")
            
            # Parse status messages
            if msg.startswith("STATUS:"):
                parts = msg[7:].split(",")
                for part in parts:
                    key_val = part.split("=")
                    if len(key_val) == 2:
                        st.session_state.status[key_val[0]] = key_val[1]
    
    # Display log (most recent messages at the top)
    log_text = "\n".join(st.session_state.log[-100:][::-1])
    log_container.text_area("Serial Communication Log", log_text, height=300)
    
    # Update status periodically
    if st.session_state.connected and st.session_state.arduino:
        status_text = f"Odor: {st.session_state.status.get('ODOR', 'UNKNOWN')} | Reward: {st.session_state.status.get('REWARD', 'UNKNOWN')}"
        st.sidebar.write(f"**Current Status:** {status_text}")

# Script entry point
if __name__ == "__main__":
    # Check if running in Streamlit
    if os.environ.get('STREAMLIT_RUN_TARGET'):
        run_streamlit()
    else:
        run_cli() 