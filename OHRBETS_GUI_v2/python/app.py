import streamlit as st
import serial
import serial.tools.list_ports
import time
import threading
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Event code mappings
EVENT_NAMES = {
    1: "Trial Start",
    2: "Trial End",
    3: "Odor On",
    4: "Odor Off",
    5: "Reward On",
    6: "Reward Off",
    7: "Lick"
}

class ArduinoInterface:
    def __init__(self):
        self.serial = None
        self.running = False
        self.connected = False
        self.data_callback = None
        self.status_callback = None
        self.thread = None
        self.data = []  # Store event data
        
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
            if self.status_callback:
                self.status_callback(f"Connection error: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from Arduino"""
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
            if self.status_callback:
                self.status_callback(f"Send error: {str(e)}")
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
                if self.status_callback:
                    self.status_callback(f"Read error: {str(e)}")
                break
            
            time.sleep(0.01)  # Small delay
    
    def _process_message(self, message):
        """Process messages from Arduino"""
        if message.startswith("DATA:"):
            # Parse data message: DATA:event_code,timestamp
            data_str = message[5:]  # Remove "DATA:" prefix
            parts = data_str.split(',')
            if len(parts) == 2:
                try:
                    event_code = int(parts[0])
                    timestamp = float(parts[1]) / 1000000.0  # Convert microseconds to seconds
                    
                    # Add to data list
                    self.data.append((event_code, timestamp))
                    
                    # Call data callback if registered
                    if self.data_callback:
                        self.data_callback(event_code, timestamp)
                except ValueError:
                    pass
        else:
            # Status messages
            if self.status_callback:
                self.status_callback(message)

def main():
    st.set_page_config(
        page_title="Pavlovian Odor Conditioning",
        page_icon="🧠",
        layout="wide",
    )
    
    st.title("Pavlovian Odor Conditioning")
    
    # Initialize session state for data
    if 'arduino' not in st.session_state:
        st.session_state.arduino = ArduinoInterface()
    
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame(columns=['event_code', 'event_name', 'timestamp', 'trial_number'])
    
    if 'status' not in st.session_state:
        st.session_state.status = "Not connected"
    
    if 'session_running' not in st.session_state:
        st.session_state.session_running = False
    
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    
    # Set up layout
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Control Panel")
        
        # Connection settings
        st.write("### Connection")
        ports = st.session_state.arduino.get_ports()
        selected_port = st.selectbox("Serial Port", ports, index=0 if ports else None)
        
        col_connect, col_refresh = st.columns(2)
        with col_connect:
            if not st.session_state.arduino.connected:
                if st.button("Connect"):
                    if st.session_state.arduino.connect(selected_port):
                        st.session_state.status = "Connected to Arduino"
                        st.experimental_rerun()
            else:
                if st.button("Disconnect"):
                    st.session_state.arduino.disconnect()
                    st.session_state.status = "Disconnected"
                    st.experimental_rerun()
        
        with col_refresh:
            if st.button("Refresh Ports"):
                st.experimental_rerun()
        
        # Experiment settings
        st.write("### Experiment Settings")
        
        # Timing parameters
        iti_duration = st.slider("Inter-trial Interval (ms)", 1000, 10000, 5000, step=500)
        odor_duration = st.slider("Odor Duration (ms)", 500, 5000, 2000, step=100)
        reward_duration = st.slider("Reward Duration (ms)", 50, 1000, 500, step=50)
        
        # Apply timing button
        if st.button("Apply Timing"):
            command = f"SET_TIMING:{iti_duration},{odor_duration},{reward_duration}"
            st.session_state.arduino.send_command(command)
        
        # Trial sequence
        st.write("### Trial Sequence")
        st.write("Enter trial types (1=CS+, 2=CS-) separated by commas:")
        
        default_sequence = "1,2,1,2,1,1,2,2,1,2"
        sequence = st.text_area("Sequence", default_sequence)
        
        # Generate a balanced random sequence
        if st.button("Generate Random"):
            num_trials = st.session_state.get('num_trials', 10)
            num_cs_plus = num_trials // 2
            sequence_list = [1] * num_cs_plus + [2] * (num_trials - num_cs_plus)
            np.random.shuffle(sequence_list)
            sequence = ','.join(map(str, sequence_list))
            st.session_state.sequence = sequence
            st.experimental_rerun()
        
        # Session control
        st.write("### Session Control")
        
        if st.session_state.arduino.connected:
            if not st.session_state.session_running:
                col_send, col_start = st.columns(2)
                
                with col_send:
                    if st.button("Send Sequence"):
                        command = f"SEQUENCE:{sequence}"
                        st.session_state.arduino.send_command(command)
                
                with col_start:
                    if st.button("Start Session"):
                        st.session_state.arduino.send_command("START")
                        st.session_state.session_running = True
                        st.session_state.start_time = time.time()
                        st.session_state.data = pd.DataFrame(columns=['event_code', 'event_name', 'timestamp', 'trial_number'])
                        st.experimental_rerun()
            else:
                if st.button("Abort Session", type="primary"):
                    st.session_state.arduino.send_command("ABORT")
                    st.session_state.session_running = False
                    st.experimental_rerun()
        
        # Status and info
        st.write("### Status")
        st.info(st.session_state.status)
        
        if st.session_state.session_running and st.session_state.start_time:
            elapsed = time.time() - st.session_state.start_time
            st.write(f"Session time: {int(elapsed // 60)}:{int(elapsed % 60):02d}")
        
        # Export data
        if not st.session_state.data.empty:
            st.download_button(
                "Download Data (CSV)",
                st.session_state.data.to_csv(index=False).encode('utf-8'),
                f"pavlovian_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )
    
    with col2:
        st.subheader("Data Visualization")
        
        # Create tabs for different visualizations
        tab1, tab2, tab3 = st.tabs(["Raster Plot", "Cumulative Events", "Event Log"])
        
        with tab1:
            # Raster plot
            fig1 = go.Figure()
            
            if not st.session_state.data.empty:
                # Group data by event type for raster plot
                for event_code, event_name in EVENT_NAMES.items():
                    event_data = st.session_state.data[st.session_state.data['event_code'] == event_code]
                    if not event_data.empty:
                        fig1.add_trace(go.Scatter(
                            x=event_data['timestamp'],
                            y=event_data['trial_number'],
                            mode='markers',
                            name=event_name,
                            marker=dict(size=8)
                        ))
            
            fig1.update_layout(
                xaxis_title="Time (s)",
                yaxis_title="Trial Number",
                height=500
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        
        with tab2:
            # Cumulative events plot
            fig2 = go.Figure()
            
            if not st.session_state.data.empty:
                # Plot cumulative events by type
                for event_code, event_name in EVENT_NAMES.items():
                    event_data = st.session_state.data[st.session_state.data['event_code'] == event_code]
                    if not event_data.empty:
                        # Create cumulative count
                        event_data = event_data.sort_values('timestamp')
                        event_data['cumulative'] = range(1, len(event_data) + 1)
                        
                        fig2.add_trace(go.Scatter(
                            x=event_data['timestamp'],
                            y=event_data['cumulative'],
                            mode='lines',
                            name=event_name
                        ))
            
            fig2.update_layout(
                xaxis_title="Time (s)",
                yaxis_title="Cumulative Count",
                height=500
            )
            
            st.plotly_chart(fig2, use_container_width=True)
        
        with tab3:
            # Event log as a table
            if not st.session_state.data.empty:
                display_df = st.session_state.data[['event_name', 'timestamp', 'trial_number']].copy()
                display_df['timestamp'] = display_df['timestamp'].round(3)
                st.dataframe(
                    display_df.sort_values('timestamp', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No events recorded yet")

    # Callback functions for Arduino interface
    def handle_data(event_code, timestamp):
        # Determine trial number based on trial start events
        trial_starts = [row for row in st.session_state.arduino.data if row[0] == 1]
        trial_number = len(trial_starts)
        
        # Add to dataframe
        new_row = pd.DataFrame({
            'event_code': [event_code],
            'event_name': [EVENT_NAMES.get(event_code, f"Unknown ({event_code})")],
            'timestamp': [timestamp],
            'trial_number': [trial_number]
        })
        
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    
    def handle_status(message):
        if message == "SESSION_STARTED":
            st.session_state.status = "Session running"
            st.session_state.session_running = True
            st.session_state.start_time = time.time()
        elif message == "SESSION_COMPLETE":
            st.session_state.status = "Session completed"
            st.session_state.session_running = False
        elif message == "SESSION_ABORTED":
            st.session_state.status = "Session aborted"
            st.session_state.session_running = False
        else:
            st.session_state.status = message
    
    # Register callbacks
    st.session_state.arduino.data_callback = handle_data
    st.session_state.arduino.status_callback = handle_status

if __name__ == "__main__":
    main() 