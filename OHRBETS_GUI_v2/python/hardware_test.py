import streamlit as st
import serial
import serial.tools.list_ports
import time
import threading
import pandas as pd
from datetime import datetime

# Simple Arduino interface for direct hardware testing
class ArduinoTester:
    def __init__(self):
        self.serial = None
        self.connected = False
        self.running = False
        self.thread = None
        self.lick_count = 0
        self.last_lick_time = None
        self.status_messages = []
        self.reward_active = False
        self.odor_active = False
        self.error_state = False
        
    def get_ports(self):
        """Get available serial ports"""
        return [p.device for p in serial.tools.list_ports.comports()]
    
    def connect(self, port, baudrate=115200):
        """Connect to Arduino"""
        try:
            self.serial = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            
            # Clear buffers
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            self.connected = True
            self.running = True
            
            # Start reading thread
            self.thread = threading.Thread(target=self._read_loop)
            self.thread.daemon = True
            self.thread.start()
            
            return True
        except Exception as e:
            self.status_messages.append(f"Connection error: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from Arduino"""
        # First make sure everything is off
        self.send_command("MANUAL_REWARD_OFF")
        self.send_command("MANUAL_ODOR_OFF")
        time.sleep(0.1)
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        
        if self.serial and self.serial.is_open:
            self.serial.close()
        
        self.connected = False
    
    def send_command(self, command):
        """Send command to Arduino"""
        if not self.connected or not self.serial:
            return False
        
        try:
            # Ensure command ends with newline
            if not command.endswith('\n'):
                command += '\n'
            
            self.serial.write(command.encode())
            self.serial.flush()
            return True
        except Exception as e:
            self.status_messages.append(f"Send error: {str(e)}")
            return False
    
    def _read_loop(self):
        """Background thread to read from Arduino"""
        while self.running and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode().strip()
                    if line:
                        self._process_message(line)
            except Exception as e:
                self.status_messages.append(f"Read error: {str(e)}")
                break
            
            time.sleep(0.01)  # Small delay
    
    def _process_message(self, message):
        """Process messages from Arduino"""
        print(f"Arduino: {message}")  # Print all messages for debugging
        
        # Add to status messages (limit to last 20)
        self.status_messages.append(message)
        if len(self.status_messages) > 20:
            self.status_messages.pop(0)
        
        # Check for error state
        if "ERROR:" in message:
            self.error_state = True
        
        # Check for state resets
        if "EMERGENCY_STOP" in message or message == "READY":
            self.error_state = False
        
        # Update component states based on messages
        if message.startswith("DATA:"):
            parts = message[5:].split(',')
            if len(parts) == 2 and parts[0] == "7":
                # Lick event detected
                self.lick_count += 1
                self.last_lick_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        elif message.startswith("STATUS:"):
            if "Reward:ON" in message:
                self.reward_active = True
            elif "Reward:OFF" in message:
                self.reward_active = False
                
            if "Odor:ON" in message:
                self.odor_active = True
            elif "Odor:OFF" in message:
                self.odor_active = False
        
        elif message.startswith("MANUAL_REWARD:"):
            if message.endswith("ON"):
                self.reward_active = True
            elif message.endswith("OFF"):
                self.reward_active = False
                
        elif message.startswith("MANUAL_ODOR:"):
            if message.endswith("ON"):
                self.odor_active = True
            elif message.endswith("OFF"):
                self.odor_active = False
                
        elif message.startswith("SAFETY:"):
            if message == "SAFETY:ODOR_OFF":
                self.odor_active = False
            elif message == "SAFETY:REWARD_OFF":
                self.reward_active = False
                
        elif message == "LICK_COUNT_RESET":
            self.lick_count = 0
    
    def reset(self):
        """Send reset command to force Arduino to IDLE state"""
        if self.connected:
            self.send_command("RESET")
            self.error_state = False
            return True
        return False

def main():
    st.set_page_config(
        page_title="Hardware Test GUI",
        page_icon="🔧",
        layout="wide",
    )
    
    st.title("OHRBETS Hardware Test GUI")
    
    # Initialize session state for Arduino tester
    if 'arduino' not in st.session_state:
        st.session_state.arduino = ArduinoTester()
    
    # Connection section
    st.header("1. Connection")
    
    # Connection controls
    ports = st.session_state.arduino.get_ports()
    col1, col2, col3, col_reset = st.columns([2, 1, 1, 1])
    
    with col1:
        selected_port = st.selectbox("Serial Port", ports, index=0 if ports else None)
    
    with col2:
        if not st.session_state.arduino.connected:
            if st.button("Connect", use_container_width=True):
                if st.session_state.arduino.connect(selected_port):
                    st.success("Connected to Arduino")
                    st.session_state.arduino.send_command("STATUS")
                    st.rerun()
        else:
            if st.button("Disconnect", use_container_width=True):
                st.session_state.arduino.disconnect()
                st.rerun()
    
    with col3:
        if st.button("Refresh Ports", use_container_width=True):
            st.rerun()
            
    with col_reset:
        if st.session_state.arduino.connected:
            if st.button("RESET ARDUINO", 
                        type="primary" if st.session_state.arduino.error_state else "secondary",
                        use_container_width=True):
                st.session_state.arduino.reset()
                time.sleep(0.2)  # Short delay
                st.session_state.arduino.send_command("STATUS")
                st.rerun()
    
    if st.session_state.arduino.connected:
        # Show connection status
        if st.session_state.arduino.error_state:
            st.error("⚠️ Arduino is in ERROR state - click RESET ARDUINO to recover")
        else:
            st.success("✅ Connected to Arduino")
        
        # Direct manual control section
        st.header("2. Manual Component Controls")
        
        # Create 3 columns for the 3 main components
        col_reward, col_odor, col_lick = st.columns(3)
        
        # Reward solenoid controls
        with col_reward:
            st.subheader("Reward Solenoid")
            
            # Show current status
            if st.session_state.arduino.reward_active:
                st.error("⚠️ REWARD SOLENOID IS ON")
            else:
                st.info("Reward solenoid is off")
                
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("REWARD ON", 
                             type="primary", 
                             disabled=st.session_state.arduino.reward_active or st.session_state.arduino.error_state,
                             use_container_width=True):
                    st.session_state.arduino.send_command("MANUAL_REWARD_ON")
                    st.rerun()
            
            with col_r2:
                if st.button("REWARD OFF", 
                             type="primary", 
                             disabled=not st.session_state.arduino.reward_active,
                             use_container_width=True):
                    st.session_state.arduino.send_command("MANUAL_REWARD_OFF")
                    st.rerun()
            
            # Add pattern test button
            if st.button("Test 40-140-40ms Pattern", 
                        disabled=st.session_state.arduino.error_state,
                        use_container_width=True):
                st.session_state.arduino.send_command("TEST_REWARD")
        
        # Odor solenoid controls
        with col_odor:
            st.subheader("Odor Solenoid")
            
            # Show current status
            if st.session_state.arduino.odor_active:
                st.error("⚠️ ODOR SOLENOID IS ON")
            else:
                st.info("Odor solenoid is off")
                
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                if st.button("ODOR ON", 
                             type="primary", 
                             disabled=st.session_state.arduino.odor_active or st.session_state.arduino.error_state,
                             use_container_width=True):
                    st.session_state.arduino.send_command("MANUAL_ODOR_ON")
                    st.rerun()
            
            with col_o2:
                if st.button("ODOR OFF", 
                             type="primary", 
                             disabled=not st.session_state.arduino.odor_active,
                             use_container_width=True):
                    st.session_state.arduino.send_command("MANUAL_ODOR_OFF")
                    st.rerun()
            
            # Add 2s test button
            if st.button("Test 2s Odor Pulse", 
                        disabled=st.session_state.arduino.error_state,
                        use_container_width=True):
                st.session_state.arduino.send_command("TEST_ODOR")
        
        # Lick sensor monitoring
        with col_lick:
            st.subheader("Lick Sensor")
            
            # Display lick count
            st.metric("Lick Count", st.session_state.arduino.lick_count)
            
            if st.session_state.arduino.last_lick_time:
                st.write(f"Last lick: {st.session_state.arduino.last_lick_time}")
            
            # Add lick reset button
            if st.button("Reset Lick Counter", use_container_width=True):
                st.session_state.arduino.send_command("RESET_LICK_COUNT")
                st.session_state.arduino.lick_count = 0
            
            # Start/stop lick monitoring (using status check)
            if st.button("Start Lick Monitoring", use_container_width=True):
                st.session_state.arduino.send_command("TEST_LICK")
        
        # Communication log
        st.header("3. Communication Log")
        
        # Status check button
        if st.button("Request Status Update"):
            st.session_state.arduino.send_command("STATUS")
        
        # Display last 20 messages with color coding
        for msg in reversed(st.session_state.arduino.status_messages):
            if "ERROR:" in msg:
                st.error(msg)
            elif any(keyword in msg for keyword in ["SAFETY:", "STATE_TIMEOUT", "EMERGENCY_STOP"]):
                st.warning(msg)
            elif any(keyword in msg for keyword in ["COMPLETE", "MANUAL_", "STATE_CHANGE:", "TEST_", "_START", "_ON", "_OFF"]):
                st.info(msg)
            else:
                st.code(msg)
    
    else:
        st.warning("Please connect to Arduino to control hardware")
    
    # Auto-refresh if connected to keep status updated
    if st.session_state.arduino.connected:
        time.sleep(0.2)  # Short delay
        st.rerun()

if __name__ == "__main__":
    main() 