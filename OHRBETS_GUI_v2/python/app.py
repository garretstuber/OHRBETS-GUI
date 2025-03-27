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
import queue
# Import the real-time visualization module
from real_time_viz import create_real_time_dashboard, RealTimeVisualizer

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
        self.message_queue = queue.Queue()  # Queue for thread-safe communication
        
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
            self.message_queue.put(("status", f"Connection error: {str(e)}"))
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
            self.message_queue.put(("status", f"Send error: {str(e)}"))
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
                self.message_queue.put(("status", f"Read error: {str(e)}"))
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
                    timestamp = float(parts[1]) / 1000.0  # Convert milliseconds to seconds
                    
                    # Add to data list
                    self.data.append((event_code, timestamp))
                    
                    # Put data in queue for main thread to process
                    self.message_queue.put(("data", (event_code, timestamp)))
                except ValueError:
                    pass
        else:
            # Status messages - log debug info
            print(f"Arduino status: {message}")
            self.message_queue.put(("status", message))

    def process_queue(self):
        """Process messages from the queue in the main thread"""
        messages_processed = 0
        while not self.message_queue.empty() and messages_processed < 100:  # Limit to prevent UI freeze
            msg_type, data = self.message_queue.get()
            if msg_type == "data" and self.data_callback:
                self.data_callback(*data)
            elif msg_type == "status" and self.status_callback:
                self.status_callback(data)
            messages_processed += 1

def main():
    st.set_page_config(
        page_title="Pavlovian Odor Conditioning",
        page_icon="🧠",
        layout="wide",
    )
    
    st.title("🐭 Pavlovian Odor Conditioning 🍬")
    st.markdown("### Stuber Lab - UW")
    
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
    
    if 'arduino_status' not in st.session_state:
        st.session_state.arduino_status = ""
    
    if 'lick_test_active' not in st.session_state:
        st.session_state.lick_test_active = False
    
    if 'lick_count' not in st.session_state:
        st.session_state.lick_count = 0
    
    if 'last_lick_time' not in st.session_state:
        st.session_state.last_lick_time = 0
        
    if 'manual_reward_active' not in st.session_state:
        st.session_state.manual_reward_active = False
    
    if 'manual_odor_active' not in st.session_state:
        st.session_state.manual_odor_active = False
    
    # Create a placeholder for auto-refresh if session is running
    refresh_placeholder = st.empty()
    
    # Process any queued messages from Arduino thread
    st.session_state.arduino.process_queue()
    
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
                        st.rerun()
            else:
                if st.button("Disconnect"):
                    # Make sure to turn off any manual reward first
                    if st.session_state.manual_reward_active:
                        st.session_state.arduino.send_command("MANUAL_REWARD_OFF")
                        st.session_state.manual_reward_active = False
                    st.session_state.arduino.disconnect()
                    st.session_state.status = "Disconnected"
                    st.rerun()
        
        with col_refresh:
            if st.button("Refresh Ports"):
                st.rerun()
        
        # Debug buttons
        col_refresh_display, col_check_status = st.columns(2)
        with col_refresh_display:
            if st.button("Refresh Display"):
                pass  # This just triggers a UI refresh
                
        with col_check_status:
            if st.session_state.arduino.connected and st.button("Check Status"):
                if st.session_state.arduino.send_command("STATUS"):
                    st.success("Status request sent")
        
        # Arduino status display
        if st.session_state.arduino_status:
            st.code(st.session_state.arduino_status)
        
        # Hardware Test Section
        if st.session_state.arduino.connected and not st.session_state.session_running:
            st.write("### Hardware Testing")
            st.write("Test hardware components before starting a session:")
            
            # Odor valve test button
            st.write("**Odor Valve:**")
            if st.button("Test Odor Valve"):
                if st.session_state.arduino.send_command("TEST_ODOR"):
                    st.success("Odor valve activated for 2 seconds")
            
            # Manual odor control
            st.write("Direct Odor Control:")
            
            # Manual Odor control
            col_odor_on, col_odor_off = st.columns(2)
            with col_odor_on:
                if not hasattr(st.session_state, 'manual_odor_active') or not st.session_state.manual_odor_active:
                    if st.button("Odor ON", type="primary"):
                        if st.session_state.arduino.send_command("MANUAL_ODOR_ON"):
                            st.session_state.manual_odor_active = True
                            st.rerun()
            
            with col_odor_off:
                if hasattr(st.session_state, 'manual_odor_active') and st.session_state.manual_odor_active:
                    if st.button("Odor OFF", type="primary"):
                        if st.session_state.arduino.send_command("MANUAL_ODOR_OFF"):
                            st.session_state.manual_odor_active = False
                            st.rerun()
            
            # Warning if manual odor is active
            if hasattr(st.session_state, 'manual_odor_active') and st.session_state.manual_odor_active:
                st.warning("⚠️ Odor valve is currently ON. Click 'Odor OFF' to deactivate.")
            
            # Reward control
            st.write("**Reward Solenoid:**")
            
            # Two-pulse pattern test
            if st.button("Test Reward Pattern"):
                if st.session_state.arduino.send_command("TEST_REWARD"):
                    st.success("Reward solenoid activated (40ms on, 140ms off, 40ms on)")
            
            # Manual reward control
            st.write("Direct Reward Control:")
            col_reward_on, col_reward_off = st.columns(2)
            with col_reward_on:
                if not st.session_state.manual_reward_active:
                    if st.button("Reward ON", type="primary"):
                        if st.session_state.arduino.send_command("MANUAL_REWARD_ON"):
                            st.session_state.manual_reward_active = True
                            st.rerun()
            
            with col_reward_off:
                if st.session_state.manual_reward_active:
                    if st.button("Reward OFF", type="primary"):
                        if st.session_state.arduino.send_command("MANUAL_REWARD_OFF"):
                            st.session_state.manual_reward_active = False
                            st.rerun()
            
            # Warning if manual reward is active
            if st.session_state.manual_reward_active:
                st.warning("⚠️ Reward solenoid is currently ON. Click 'Reward OFF' to deactivate.")
            
            # Lick sensor test
            st.write("**Lick Sensor:**")
            col_lick_test, col_reset_lick = st.columns(2)
            with col_lick_test:
                if not st.session_state.lick_test_active:
                    if st.button("Test Lick Sensor"):
                        if st.session_state.arduino.send_command("TEST_LICK"):
                            st.session_state.lick_test_active = True
                            st.session_state.lick_count = 0
                            st.rerun()
                else:
                    if st.button("Stop Lick Test", type="primary"):
                        st.session_state.lick_test_active = False
                        st.rerun()
            
            with col_reset_lick:
                if st.button("Reset Lick Count"):
                    if st.session_state.arduino.send_command("RESET_LICK_COUNT"):
                        st.session_state.lick_count = 0
                        st.rerun()
            
            # Lick sensor readings display
            if st.session_state.lick_test_active:
                st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin-top:10px;">
                    <div style="text-align:center;"><b>Lick Sensor Test Active</b></div>
                    <div>Lick Count: <b>{st.session_state.lick_count}</b></div>
                    <div>Last Lick: <b>{st.session_state.last_lick_time}</b></div>
                    <div><small>Tap on the lick sensor to test</small></div>
                </div>
                """, unsafe_allow_html=True)
        
        # Experiment settings
        st.write("### Experiment Settings")
        
        # Animal ID field
        animal_id = st.text_input("Animal ID", value="mouse1")
        if not animal_id:
            st.warning("Please enter an Animal ID")
            
        # Add condition fields
        st.write("### Animal Condition")
        condition = st.selectbox(
            "Experimental Condition",
            ["ad lib.", "food restricted", "water restricted"]
        )
        
        # Add treatment field
        treatment = st.text_input("Treatment (e.g., drug dose, injection, etc.)", value="")
        if treatment:
            st.info(f"Current treatment: {treatment}")
        
        # Add restriction metadata
        if condition != "ad lib.":
            restriction_start = st.date_input("Restriction Start Date")
            current_weight = st.number_input("Current Weight (g)", min_value=0.0, max_value=100.0, value=20.0, step=0.1)
            baseline_weight = st.number_input("Baseline Weight (g)", min_value=0.0, max_value=100.0, value=25.0, step=0.1)
            if baseline_weight > 0:
                weight_percent = (current_weight / baseline_weight) * 100
                st.write(f"Current weight is {weight_percent:.1f}% of baseline")
        
        # Timing parameters - ITI range with random sampling
        st.write("### ITI Settings")
        col_iti_min, col_iti_max = st.columns(2)
        with col_iti_min:
            iti_min = st.number_input("Minimum ITI (s)", min_value=1, max_value=30, value=5, step=1)
        with col_iti_max:
            iti_max = st.number_input("Maximum ITI (s)", min_value=iti_min, max_value=30, value=10, step=1)
            
        st.info(f"ITI will be randomly sampled between {iti_min}-{iti_max} seconds in 1s intervals")
        
        # When sending timing command, convert to milliseconds
        if st.button("Apply ITI Settings"):
            # Convert to milliseconds for Arduino
            iti_min_ms = iti_min * 1000
            iti_max_ms = iti_max * 1000
            command = f"SET_ITI_RANGE:{iti_min_ms},{iti_max_ms}"
            if st.session_state.arduino.send_command(command):
                st.success(f"ITI range set: {iti_min}-{iti_max} seconds")
        
        # Information about hardcoded timing
        st.info("⚠️ Odor duration (2000ms) and reward pattern (40ms-140ms-40ms) are now hardcoded in the Arduino firmware for precise timing control.")
        
        # Trial sequence
        st.write("### Trial Sequence")
        st.write("Enter trial types (1=CS+, 2=CS-) separated by commas:")
        
        default_sequence = "1,2,1,2,1,1,2,2,1,2"
        sequence = st.text_area("Sequence", default_sequence)
        
        # Generate a balanced random sequence
        col_gen, col_trials = st.columns(2)
        with col_gen:
            if st.button("Generate Random"):
                num_trials = st.session_state.get('num_trials', 10)
                num_cs_plus = num_trials // 2
                sequence_list = [1] * num_cs_plus + [2] * (num_trials - num_cs_plus)
                np.random.shuffle(sequence_list)
                sequence = ','.join(map(str, sequence_list))
                st.session_state.sequence = sequence
                st.rerun()
                
        with col_trials:
            num_trials = st.number_input("Number of Trials", min_value=2, max_value=100, value=10, step=2)
            st.session_state.num_trials = num_trials
        
        # Session control
        st.write("### Session Control")
        
        if st.session_state.arduino.connected:
            if not st.session_state.session_running:
                # Ensure manual reward is off before starting a session
                if st.session_state.manual_reward_active:
                    st.warning("⚠️ Turn off manual reward control before starting a session.")
                
                col_send, col_start = st.columns(2)
                
                with col_send:
                    if st.button("Send Sequence"):
                        command = f"SEQUENCE:{sequence}"
                        if st.session_state.arduino.send_command(command):
                            st.success(f"Sequence sent with {sequence.count(',')+1} trials")
                
                with col_start:
                    start_disabled = st.session_state.manual_reward_active
                    if st.button("Start Session", disabled=start_disabled):
                        # Store animal ID in session state for later use when saving
                        st.session_state.animal_id = animal_id
                        st.session_state.arduino.send_command("START")
                        st.session_state.session_running = True
                        st.session_state.start_time = time.time()
                        st.session_state.data = pd.DataFrame(columns=['event_code', 'event_name', 'timestamp', 'trial_number'])
                        st.rerun()
            else:
                if st.button("Abort Session", type="primary"):
                    st.session_state.arduino.send_command("ABORT")
                    st.session_state.session_running = False
                    st.rerun()
        
        # Status and info
        st.write("### Status")
        st.info(st.session_state.status)
        
        # Session timer with real-time display
        if st.session_state.session_running and st.session_state.start_time:
            elapsed = time.time() - st.session_state.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            
            # Create a more prominent timer display
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; text-align:center;">
                <h3 style="margin:0;">Session Time</h3>
                <h2 style="margin:0; font-size:2.5rem; font-family:monospace;">{minutes:02d}:{seconds:02d}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Current trial info
            if not st.session_state.data.empty:
                trial_starts = st.session_state.data[st.session_state.data['event_code'] == 1]
                current_trial = len(trial_starts)
                if 'trial_type' in st.session_state.data.columns:
                    last_trial_type = st.session_state.data.loc[st.session_state.data['event_code'] == 1, 'trial_type'].iloc[-1] if not trial_starts.empty else "N/A"
                    trial_type_name = "CS+" if last_trial_type == 1 else "CS-" if last_trial_type == 2 else "N/A"
                    st.write(f"Current Trial: {current_trial} ({trial_type_name})")
                else:
                    st.write(f"Current Trial: {current_trial}")
        
        # Export data
        if not st.session_state.data.empty:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"{date_str}_{animal_id}_pavlovian.csv"
            st.download_button(
                "Download Data (CSV)",
                st.session_state.data.to_csv(index=False).encode('utf-8'),
                filename,
                "text/csv"
            )
    
    with col2:
        st.subheader("Session Metrics")
        
        # Create a metrics dashboard
        if st.session_state.session_running:
            # Calculate core metrics
            total_licks = len(st.session_state.data[st.session_state.data['event_code'] == 7])
            cs_plus_trials = len(st.session_state.data[
                (st.session_state.data['event_code'] == 1) & 
                (st.session_state.data['trial_type'] == 1)
            ])
            cs_minus_trials = len(st.session_state.data[
                (st.session_state.data['event_code'] == 1) & 
                (st.session_state.data['trial_type'] == 2)
            ])
            
            # Session timing
            elapsed = time.time() - st.session_state.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            
            # Estimate time remaining based on trial sequence
            if 'sequence' in st.session_state:
                total_trials = len(st.session_state.sequence.split(','))
                completed_trials = cs_plus_trials + cs_minus_trials
                if completed_trials > 0:
                    avg_trial_time = elapsed / completed_trials
                    remaining_trials = total_trials - completed_trials
                    time_remaining = remaining_trials * avg_trial_time
                    rem_minutes = int(time_remaining // 60)
                    rem_seconds = int(time_remaining % 60)
                else:
                    rem_minutes = 0
                    rem_seconds = 0
            
            # Create three columns for metrics display
            col_timing, col_trials, col_behavior = st.columns(3)
            
            with col_timing:
                st.markdown("### Timing")
                st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin:5px;">
                    <div><b>Session Time:</b> {minutes:02d}:{seconds:02d}</div>
                    <div><b>Est. Remaining:</b> {rem_minutes:02d}:{rem_seconds:02d}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_trials:
                st.markdown("### Trials")
                st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin:5px;">
                    <div><b>CS+ Trials:</b> {cs_plus_trials}</div>
                    <div><b>CS- Trials:</b> {cs_minus_trials}</div>
                    <div><b>Total Trials:</b> {cs_plus_trials + cs_minus_trials}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_behavior:
                st.markdown("### Behavior")
                # Calculate lick rates
                if elapsed > 0:
                    lick_rate = total_licks / (elapsed / 60)  # licks per minute
                else:
                    lick_rate = 0
                
                # Calculate CS+ vs CS- licking
                cs_plus_licks = 0
                cs_minus_licks = 0
                for trial_num in st.session_state.data[st.session_state.data['trial_type'] == 1]['trial_number'].unique():
                    trial_licks = len(st.session_state.data[
                        (st.session_state.data['event_code'] == 7) & 
                        (st.session_state.data['trial_number'] == trial_num)
                    ])
                    cs_plus_licks += trial_licks
                
                for trial_num in st.session_state.data[st.session_state.data['trial_type'] == 2]['trial_number'].unique():
                    trial_licks = len(st.session_state.data[
                        (st.session_state.data['event_code'] == 7) & 
                        (st.session_state.data['trial_number'] == trial_num)
                    ])
                    cs_minus_licks += trial_licks
                
                # Calculate average licks per trial
                avg_plus_licks = cs_plus_licks / cs_plus_trials if cs_plus_trials > 0 else 0
                avg_minus_licks = cs_minus_licks / cs_minus_trials if cs_minus_trials > 0 else 0
                
                st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin:5px;">
                    <div><b>Total Licks:</b> {total_licks}</div>
                    <div><b>Lick Rate:</b> {lick_rate:.1f}/min</div>
                    <div><b>Avg CS+ Licks:</b> {avg_plus_licks:.1f}</div>
                    <div><b>Avg CS- Licks:</b> {avg_minus_licks:.1f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Add a simple progress bar
            progress = (cs_plus_trials + cs_minus_trials) / total_trials if 'sequence' in st.session_state else 0
            st.progress(progress, text=f"Session Progress: {progress*100:.1f}%")
        
        else:
            st.info("Start a session to see metrics")
            
        # Basic event log
        st.markdown("### Recent Events")
        if not st.session_state.data.empty:
            display_df = st.session_state.data[['event_name', 'timestamp', 'trial_number']].copy()
            display_df['timestamp'] = display_df['timestamp'].round(3)
            st.dataframe(
                display_df.sort_values('timestamp', ascending=False).head(10),
                use_container_width=True,
                hide_index=True
            )

    # Callback functions for Arduino interface
    def handle_data(event_code, timestamp):
        # Add trial type information based on trial starts
        if event_code == 1:  # Trial Start
            trial_starts = [row for row in st.session_state.arduino.data if row[0] == 1]
            trial_number = len(trial_starts)
            
            # Try to determine trial type (CS+ or CS-)
            # Assuming trials alternate or follow some pattern
            trial_type = None
            if trial_number > 0 and st.session_state.arduino.data:
                # Look at most recent data to determine trial type
                for i in range(len(st.session_state.arduino.data)-1, -1, -1):
                    if st.session_state.arduino.data[i][0] == 3:  # Odor On
                        # Assuming Odor1 = CS+ = 1, Odor2 = CS- = 2
                        # This is a simplification; actual type may need to be determined from sequence
                        trial_type = 1  # Default to CS+
                        break
        else:
            # For non-trial-start events, get trial number from most recent trial start
            trial_starts = [row for row in st.session_state.arduino.data if row[0] == 1]
            trial_number = len(trial_starts)
            trial_type = None
            
            # Update lick count for lick sensor test
            if event_code == 7 and st.session_state.lick_test_active:  # Lick event
                st.session_state.lick_count += 1
                st.session_state.last_lick_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Add to dataframe
        new_row = pd.DataFrame({
            'event_code': [event_code],
            'event_name': [EVENT_NAMES.get(event_code, f"Unknown ({event_code})")],
            'timestamp': [timestamp],
            'trial_number': [trial_number],
        })
        
        if trial_type is not None:
            new_row['trial_type'] = trial_type
        
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    
    def handle_status(message):
        # Handle status messages from Arduino
        if message.startswith("STATUS:"):
            # Store the status for display
            st.session_state.arduino_status = message
            
            # Parse lick information from status if lick test is active
            if st.session_state.lick_test_active and "Licks:" in message:
                try:
                    lick_part = message.split("Licks:")[1].split(",")[0]
                    st.session_state.lick_count = int(lick_part)
                except:
                    pass
            
            # Check hardware states
            if "Reward:ON" in message:
                st.session_state.manual_reward_active = True
            elif "Reward:OFF" in message:
                st.session_state.manual_reward_active = False
                
            if "Odor:ON" in message:
                st.session_state.manual_odor_active = True
            elif "Odor:OFF" in message:
                st.session_state.manual_odor_active = False
                
            return
        
        # Manual control messages
        if message.startswith("MANUAL_REWARD:"):
            if message.endswith("ON"):
                st.session_state.manual_reward_active = True
            elif message.endswith("OFF"):
                st.session_state.manual_reward_active = False
            return
            
        if message.startswith("MANUAL_ODOR:"):
            if message.endswith("ON"):
                st.session_state.manual_odor_active = True
            elif message.endswith("OFF"):
                st.session_state.manual_odor_active = False
            return
            
        # Safety messages
        if message.startswith("SAFETY:"):
            if message == "SAFETY:ODOR_OFF":
                st.session_state.manual_odor_active = False
            elif message == "SAFETY:REWARD_OFF":
                st.session_state.manual_reward_active = False
            return
            
        # Lick test status messages
        if message == "LICK_TEST:MONITORING":
            st.session_state.lick_test_active = True
            return
        
        if message == "LICK_COUNT_RESET":
            st.session_state.lick_count = 0
            return
            
        # Test messages
        if message.startswith("TEST_ODOR") or message.startswith("TEST_REWARD"):
            if message.endswith("_COMPLETE"):
                st.session_state.status = "Test completed"
            elif message.endswith("_START"):
                st.session_state.status = "Test in progress"
            return
        
        # Only update status if it's one of these important messages
        important_messages = ["SESSION_STARTED", "SESSION_COMPLETE", "SESSION_ABORTED", 
                              "READY", "SEQUENCE_RECEIVED", "TIMING_SET"]
        
        if message in important_messages or any(message.startswith(prefix) for prefix in ["SEQUENCE_RECEIVED:", "TIMING_SET:"]):
            if message == "SESSION_STARTED":
                st.session_state.status = "Session running"
                st.session_state.session_running = True
                st.session_state.start_time = time.time()
            elif message == "SESSION_COMPLETE":
                # Session completed successfully - auto-save data
                st.session_state.session_running = False
                
                # Only save if there's data to save
                if not st.session_state.data.empty:
                    # Use the new naming convention: date_AnimalID_pavlovian.csv
                    date_str = datetime.now().strftime('%Y%m%d')
                    animal_id = st.session_state.get('animal_id', 'unknown')
                    filename = f"{date_str}_{animal_id}_pavlovian.csv"
                    
                    # Save data to file
                    st.session_state.data.to_csv(filename, index=False)
                    st.session_state.status = f"Session completed. Data saved to {filename}"
                else:
                    st.session_state.status = "Session completed. No data to save."
                
                # Ensure all monitoring is stopped
                st.session_state.lick_test_active = False
                st.session_state.manual_reward_active = False
                st.session_state.manual_odor_active = False
                
            elif message == "SESSION_ABORTED":
                # Session aborted - don't auto-save data
                st.session_state.session_running = False
                st.session_state.status = "Session aborted. Data not automatically saved."
                
                # Ensure all monitoring is stopped
                st.session_state.lick_test_active = False
                st.session_state.manual_reward_active = False
                st.session_state.manual_odor_active = False
                
            elif message == "READY":
                st.session_state.status = "Arduino ready"
            elif message.startswith("SEQUENCE_RECEIVED"):
                st.session_state.status = "Sequence received"
            elif message.startswith("TIMING_SET"):
                st.session_state.status = "Timing parameters set"
            else:
                st.session_state.status = message
    
    # Register callbacks
    st.session_state.arduino.data_callback = handle_data
    st.session_state.arduino.status_callback = handle_status
    
    # Auto-refresh during session to update timer
    if st.session_state.session_running or st.session_state.lick_test_active or st.session_state.manual_reward_active:
        refresh_placeholder.empty()
        time.sleep(0.1)  # Small delay to not overwhelm the system
        st.rerun()

if __name__ == "__main__":
    main() 