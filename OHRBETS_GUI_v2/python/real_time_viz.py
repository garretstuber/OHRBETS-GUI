import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime

# Constants for event codes
EVENT_NAMES = {
    1: "Trial Start",
    2: "Trial End",
    3: "Odor On",
    4: "Odor Off",
    5: "Reward On",
    6: "Reward Off",
    7: "Lick"
}

class RealTimeVisualizer:
    """Class to handle real-time visualization of experimental data."""
    
    def __init__(self):
        """Initialize the visualizer."""
        self.last_update_time = time.time()
        self.update_interval = 0.5  # Update visualizations every 0.5 seconds
    
    def should_update(self):
        """Check if visualizations should be updated based on time interval."""
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            return True
        return False
    
    def plot_trial_timeline(self, data, current_trial, container=None):
        """Create a timeline visualization of the current trial events."""
        if data.empty:
            return None
            
        # Filter data for the current trial
        trial_data = data[data['trial_number'] == current_trial]
        if trial_data.empty:
            return None
            
        # Get the trial type
        trial_type = trial_data['trial_type'].iloc[0] if 'trial_type' in trial_data.columns else 1
        trial_type_name = "CS+" if trial_type == 1 else "CS-"
        
        # Find events
        events = []
        for event_code in [1, 3, 4, 5, 6]:  # Trial start, odor on/off, reward on/off
            event_rows = trial_data[trial_data['event_code'] == event_code]
            if not event_rows.empty:
                for _, row in event_rows.iterrows():
                    events.append({
                        'event': EVENT_NAMES[event_code],
                        'time': row['timestamp'],
                        'color': self._get_event_color(event_code)
                    })
        
        # Sort events by time
        events.sort(key=lambda x: x['time'])
        
        # Create timeline figure
        fig = go.Figure()
        
        # Add timeline events
        y_pos = 1
        for event in events:
            fig.add_trace(go.Scatter(
                x=[event['time'], event['time']],
                y=[0, y_pos],
                mode='lines',
                name=event['event'],
                line=dict(color=event['color'], width=2),
                showlegend=True
            ))
            
            # Add marker at event time
            fig.add_trace(go.Scatter(
                x=[event['time']],
                y=[y_pos],
                mode='markers',
                marker=dict(size=10, color=event['color']),
                name=event['event'],
                showlegend=False
            ))
        
        # Add lick events
        lick_data = trial_data[trial_data['event_code'] == 7]
        if not lick_data.empty:
            fig.add_trace(go.Scatter(
                x=lick_data['timestamp'],
                y=[0.3] * len(lick_data),
                mode='markers',
                name='Licks',
                marker=dict(size=8, color='green', symbol='triangle-up'),
            ))
        
        # Set layout
        fig.update_layout(
            title=f"Trial {current_trial} Timeline ({trial_type_name})",
            xaxis_title="Time (s)",
            yaxis_title="",
            yaxis=dict(
                showticklabels=False,
                range=[-0.1, 1.1]
            ),
            height=250,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Display in the provided container if available
        if container:
            container.plotly_chart(fig, use_container_width=True)
            
        return fig
    
    def plot_realtime_raster(self, data, window_size=5, trial_limit=None, container=None):
        """Create a real-time raster plot showing recent trials."""
        if data.empty:
            return None
            
        # Get unique trials
        trials = data['trial_number'].unique()
        trials.sort()
        
        # Limit to the most recent trials if specified
        if trial_limit and len(trials) > trial_limit:
            trials = trials[-trial_limit:]
        
        # Create figure
        fig = go.Figure()
        
        # For each trial, add events
        for trial_num in trials:
            trial_data = data[data['trial_number'] == trial_num]
            
            # Get trial type
            trial_type = trial_data['trial_type'].iloc[0] if 'trial_type' in trial_data.columns else 1
            marker_color = 'rgba(255, 0, 0, 0.7)' if trial_type == 1 else 'rgba(0, 0, 255, 0.7)'
            
            # Add odor events
            odor_on = trial_data[trial_data['event_code'] == 3]
            if not odor_on.empty:
                fig.add_trace(go.Scatter(
                    x=odor_on['timestamp'],
                    y=[trial_num] * len(odor_on),
                    mode='markers',
                    marker=dict(size=12, symbol='square', color=marker_color),
                    name=f'Odor On (Trial {trial_num})',
                    showlegend=False
                ))
            
            # Add reward events for CS+ trials
            if trial_type == 1:
                reward_on = trial_data[trial_data['event_code'] == 5]
                if not reward_on.empty:
                    fig.add_trace(go.Scatter(
                        x=reward_on['timestamp'],
                        y=[trial_num] * len(reward_on),
                        mode='markers',
                        marker=dict(size=14, symbol='star', color='gold'),
                        name=f'Reward (Trial {trial_num})',
                        showlegend=False
                    ))
            
            # Add lick events
            licks = trial_data[trial_data['event_code'] == 7]
            if not licks.empty:
                fig.add_trace(go.Scatter(
                    x=licks['timestamp'],
                    y=[trial_num] * len(licks),
                    mode='markers',
                    marker=dict(size=6, symbol='line-ns', color='green'),
                    name=f'Licks (Trial {trial_num})',
                    showlegend=False
                ))
        
        # Find the last timestamp to set the window
        last_time = data['timestamp'].max() if not data.empty else 0
        
        # Set layout with a moving time window
        fig.update_layout(
            title="Real-time Lick Raster",
            xaxis_title="Time (s)",
            yaxis_title="Trial Number",
            xaxis=dict(
                range=[max(0, last_time - window_size), last_time + 1]
            ),
            yaxis=dict(
                range=[trials[0] - 0.5, trials[-1] + 0.5]
            ),
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        # Add legend
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(size=12, symbol='square', color='red'),
            name='CS+ Odor',
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(size=12, symbol='square', color='blue'),
            name='CS- Odor',
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(size=14, symbol='star', color='gold'),
            name='Reward',
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(size=6, symbol='line-ns', color='green'),
            name='Lick',
            showlegend=True
        ))
        
        # Update legend position
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Display in the provided container if available
        if container:
            container.plotly_chart(fig, use_container_width=True)
            
        return fig
    
    def plot_lick_rate(self, data, bin_width=0.5, window_size=10, container=None):
        """Create a real-time plot of lick rate over time."""
        if data.empty:
            return None
            
        # Get lick events
        licks = data[data['event_code'] == 7]['timestamp'].values
        if len(licks) == 0:
            return None
            
        # Create time bins
        max_time = data['timestamp'].max()
        min_time = max(0, max_time - window_size)
        bins = np.arange(min_time, max_time + bin_width, bin_width)
        
        # Calculate lick rate
        lick_counts, bin_edges = np.histogram(licks, bins=bins)
        lick_rate = lick_counts / bin_width  # licks per second
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Create figure
        fig = go.Figure()
        
        # Add lick rate trace
        fig.add_trace(go.Scatter(
            x=bin_centers,
            y=lick_rate,
            mode='lines+markers',
            line=dict(width=2, color='green'),
            marker=dict(size=5),
            name='Lick Rate'
        ))
        
        # Add odor and reward events as vertical lines
        for event_code, event_name in [(3, 'Odor On'), (5, 'Reward On')]:
            events = data[data['event_code'] == event_code]
            
            for _, event in events.iterrows():
                if min_time <= event['timestamp'] <= max_time:
                    trial_type = event['trial_type'] if 'trial_type' in data.columns else 1
                    color = 'red' if trial_type == 1 else 'blue'
                    
                    fig.add_shape(
                        type="line",
                        x0=event['timestamp'],
                        y0=0,
                        x1=event['timestamp'],
                        y1=max(lick_rate) if len(lick_rate) > 0 else 5,
                        line=dict(color=color, width=1.5, dash="dash"),
                    )
                    
                    # Add label
                    label = "CS+" if trial_type == 1 else "CS-"
                    fig.add_annotation(
                        x=event['timestamp'],
                        y=max(lick_rate) if len(lick_rate) > 0 else 5,
                        text=label,
                        showarrow=False,
                        yshift=10,
                        font=dict(color=color)
                    )
        
        # Set layout
        fig.update_layout(
            title="Real-time Lick Rate",
            xaxis_title="Time (s)",
            yaxis_title="Lick Rate (Hz)",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        # Display in the provided container if available
        if container:
            container.plotly_chart(fig, use_container_width=True)
            
        return fig
    
    def plot_trial_comparison(self, data, container=None):
        """Create a bar chart comparing lick counts between CS+ and CS- trials."""
        if data.empty:
            return None
            
        # Check if we have trial type information
        if 'trial_type' not in data.columns:
            return None
            
        # Get odor on events
        odor_events = data[data['event_code'] == 3]
        if odor_events.empty:
            return None
            
        # Calculate licks in response window for each trial
        trial_licks = []
        
        for _, odor_row in odor_events.iterrows():
            trial_num = odor_row['trial_number']
            trial_type = odor_row['trial_type']
            odor_time = odor_row['timestamp']
            
            # Define response window (0-4 seconds after odor onset)
            window_start = odor_time
            window_end = odor_time + 4.0
            
            # Count licks in window
            licks = data[(data['event_code'] == 7) & 
                          (data['trial_number'] == trial_num) & 
                          (data['timestamp'] >= window_start) & 
                          (data['timestamp'] <= window_end)]
            
            lick_count = len(licks)
            
            trial_licks.append({
                'trial_number': trial_num,
                'trial_type': trial_type,
                'lick_count': lick_count
            })
        
        # Convert to DataFrame
        trial_df = pd.DataFrame(trial_licks)
        
        # Calculate average licks per trial type
        cs_plus_licks = trial_df[trial_df['trial_type'] == 1]['lick_count'].mean()
        cs_minus_licks = trial_df[trial_df['trial_type'] == 2]['lick_count'].mean()
        
        # Calculate standard error
        cs_plus_sem = trial_df[trial_df['trial_type'] == 1]['lick_count'].sem() if len(trial_df[trial_df['trial_type'] == 1]) > 0 else 0
        cs_minus_sem = trial_df[trial_df['trial_type'] == 2]['lick_count'].sem() if len(trial_df[trial_df['trial_type'] == 2]) > 0 else 0
        
        # Create bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['CS+', 'CS-'],
            y=[cs_plus_licks, cs_minus_licks],
            error_y=dict(
                type='data',
                array=[cs_plus_sem, cs_minus_sem],
                visible=True
            ),
            marker_color=['rgba(255, 0, 0, 0.7)', 'rgba(0, 0, 255, 0.7)']
        ))
        
        # Set layout
        fig.update_layout(
            title="Response Comparison",
            xaxis_title="Trial Type",
            yaxis_title="Average Licks (0-4s after odor)",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        # Display in the provided container if available
        if container:
            container.plotly_chart(fig, use_container_width=True)
            
        return fig
    
    def plot_learning_curve(self, data, bin_size=3, container=None):
        """Plot learning curve showing how behavior changes over trials."""
        if data.empty or 'trial_type' not in data.columns:
            return None
            
        # Get odor on events
        odor_events = data[data['event_code'] == 3]
        if odor_events.empty:
            return None
            
        # Calculate licks in response window for each trial
        trial_licks = []
        
        for _, odor_row in odor_events.iterrows():
            trial_num = odor_row['trial_number']
            trial_type = odor_row['trial_type']
            odor_time = odor_row['timestamp']
            
            # Define response window (0-4 seconds after odor onset)
            window_start = odor_time
            window_end = odor_time + 4.0
            
            # Count licks in window
            licks = data[(data['event_code'] == 7) & 
                          (data['trial_number'] == trial_num) & 
                          (data['timestamp'] >= window_start) & 
                          (data['timestamp'] <= window_end)]
            
            lick_count = len(licks)
            
            trial_licks.append({
                'trial_number': trial_num,
                'trial_type': trial_type,
                'lick_count': lick_count
            })
        
        # Convert to DataFrame
        trial_df = pd.DataFrame(trial_licks)
        
        # Skip if we don't have enough trials
        if len(trial_df) < bin_size:
            return None
            
        # Create binned trials
        max_trial = trial_df['trial_number'].max()
        bin_edges = list(range(1, max_trial + bin_size, bin_size))
        if bin_edges[-1] < max_trial:
            bin_edges.append(max_trial + 1)
        
        labels = [f"{e}-{e+bin_size-1}" for e in bin_edges[:-1]]
        trial_df['bin'] = pd.cut(trial_df['trial_number'], bins=bin_edges, labels=labels, include_lowest=True, right=False)
        
        # Calculate mean licks per bin for each trial type
        binned_data = trial_df.groupby(['bin', 'trial_type'])['lick_count'].mean().reset_index()
        
        # Create figure
        fig = go.Figure()
        
        # Add CS+ curve
        cs_plus_data = binned_data[binned_data['trial_type'] == 1]
        if not cs_plus_data.empty:
            fig.add_trace(go.Scatter(
                x=cs_plus_data['bin'],
                y=cs_plus_data['lick_count'],
                mode='lines+markers',
                name='CS+',
                line=dict(color='red', width=2),
                marker=dict(size=8)
            ))
        
        # Add CS- curve
        cs_minus_data = binned_data[binned_data['trial_type'] == 2]
        if not cs_minus_data.empty:
            fig.add_trace(go.Scatter(
                x=cs_minus_data['bin'],
                y=cs_minus_data['lick_count'],
                mode='lines+markers',
                name='CS-',
                line=dict(color='blue', width=2),
                marker=dict(size=8)
            ))
        
        # Set layout
        fig.update_layout(
            title="Learning Curve",
            xaxis_title="Trial Bins",
            yaxis_title="Average Licks",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Display in the provided container if available
        if container:
            container.plotly_chart(fig, use_container_width=True)
            
        return fig
    
    def _get_event_color(self, event_code):
        """Get color for different event types."""
        color_map = {
            1: "grey",         # Trial Start
            2: "grey",         # Trial End
            3: "blue",         # Odor On
            4: "lightblue",    # Odor Off
            5: "gold",         # Reward On
            6: "orange",       # Reward Off
            7: "green"         # Lick
        }
        return color_map.get(event_code, "black")

def create_real_time_dashboard(data, session_running=False):
    """Create a real-time dashboard for the experiment."""
    visualizer = RealTimeVisualizer()
    
    if data.empty:
        st.info("No data available yet. Start a session to see real-time visualization.")
        return
    
    # Create layout
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Main visualization area - Raster plot
        raster_container = st.container()
        visualizer.plot_realtime_raster(data, window_size=10, trial_limit=10, container=raster_container)
        
        # Lick rate visualization
        rate_container = st.container()
        visualizer.plot_lick_rate(data, window_size=20, container=rate_container)
    
    with col2:
        # Show current trial information if session is running
        if session_running:
            # Get the current trial
            current_trial = data['trial_number'].max() if not data.empty else 0
            
            # Show timeline for current trial
            timeline_container = st.container()
            visualizer.plot_trial_timeline(data, current_trial, container=timeline_container)
        
        # Show learning and comparison plots if we have enough data
        min_trials_for_comparison = 3
        
        # Count unique trials of each type
        if 'trial_type' in data.columns:
            cs_plus_trials = data[data['trial_type'] == 1]['trial_number'].nunique()
            cs_minus_trials = data[data['trial_type'] == 2]['trial_number'].nunique()
            
            # Only show comparison if we have enough trials of each type
            if cs_plus_trials >= min_trials_for_comparison and cs_minus_trials >= min_trials_for_comparison:
                comparison_container = st.container()
                visualizer.plot_trial_comparison(data, container=comparison_container)
                
                learning_container = st.container()
                visualizer.plot_learning_curve(data, bin_size=3, container=learning_container)

# Example usage as standalone script
if __name__ == "__main__":
    # This is for testing/demo purposes
    st.set_page_config(
        page_title="OHRBETS Real-time Visualization",
        page_icon="🧠",
        layout="wide"
    )
    
    st.title("OHRBETS Real-time Visualization Demo")
    
    # Create fake data for demonstration
    from dashboard import create_example_data
    demo_data = create_example_data()
    
    # Show the dashboard
    create_real_time_dashboard(demo_data, session_running=True) 