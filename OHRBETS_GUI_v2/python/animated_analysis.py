import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
from datetime import datetime
import scipy.ndimage as ndimage

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

def load_data(file_path):
    """Load and preprocess CSV data file."""
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def create_animated_lick_heatmap(data, bin_size=0.1, window=(-5, 10), smoothing=True):
    """
    Create an animated heatmap of licking activity aligned to odor onset.
    
    Parameters:
    - data: DataFrame with event data
    - bin_size: Size of time bins in seconds
    - window: Time window around odor onset (pre, post) in seconds
    - smoothing: Whether to apply Gaussian smoothing to the heatmap
    
    Returns:
    - Plotly figure object
    """
    if data.empty or 'trial_type' not in data.columns:
        return None
    
    # Get odor onset events
    odor_events = data[data['event_code'] == 3].copy()
    if odor_events.empty:
        return None
    
    # Create bins for time window
    bin_edges = np.arange(window[0], window[1] + bin_size, bin_size)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Initialize arrays to store lick counts
    trials = odor_events['trial_number'].unique()
    trials.sort()
    num_trials = len(trials)
    num_bins = len(bin_centers)
    
    lick_matrix = np.zeros((num_trials, num_bins))
    
    # For each trial, bin licks relative to odor onset
    for i, trial in enumerate(trials):
        trial_odor = odor_events[odor_events['trial_number'] == trial]['timestamp'].iloc[0]
        trial_licks = data[(data['event_code'] == 7) & (data['trial_number'] == trial)]['timestamp'].values
        
        # Convert to relative time
        rel_lick_times = trial_licks - trial_odor
        
        # Filter licks within window
        rel_lick_times = rel_lick_times[(rel_lick_times >= window[0]) & (rel_lick_times <= window[1])]
        
        # Bin licks
        if len(rel_lick_times) > 0:
            hist, _ = np.histogram(rel_lick_times, bins=bin_edges)
            lick_matrix[i, :] = hist
    
    # Apply Gaussian smoothing if requested
    if smoothing:
        lick_matrix = ndimage.gaussian_filter(lick_matrix, sigma=(0.8, 0.8))
    
    # Get trial types (CS+ or CS-)
    trial_types = []
    for trial in trials:
        trial_type = odor_events[odor_events['trial_number'] == trial]['trial_type'].iloc[0]
        trial_types.append("CS+" if trial_type == 1 else "CS-")
    
    # Create animated heatmap
    fig = go.Figure()
    
    # Add frames for animation - one frame per trial
    frames = []
    for i in range(num_trials):
        # Add more trials in each frame as animation progresses
        frame_data = lick_matrix[:i+1, :]
        
        if frame_data.shape[0] == 0:
            continue
            
        frame = go.Frame(
            data=[go.Heatmap(
                z=frame_data,
                x=bin_centers,
                y=np.arange(1, i+2),
                colorscale='Viridis',
                zmax=np.max(lick_matrix) if np.max(lick_matrix) > 0 else 1,
                zmin=0,
                colorbar=dict(title="Licks")
            )],
            name=f"frame_{i+1}"
        )
        frames.append(frame)
    
    # Initial empty state
    fig.add_trace(go.Heatmap(
        z=np.zeros((1, num_bins)),
        x=bin_centers,
        y=[1],
        colorscale='Viridis',
        zmax=np.max(lick_matrix) if np.max(lick_matrix) > 0 else 1,
        zmin=0,
        colorbar=dict(title="Licks")
    ))
    
    # Add a vertical line at odor onset (t=0)
    fig.add_shape(
        type="line",
        x0=0, y0=0,
        x1=0, y1=num_trials+1,
        line=dict(color="white", width=2, dash="dash")
    )
    
    # Add annotation for odor onset
    fig.add_annotation(
        x=0, y=num_trials+0.5,
        text="Odor Onset",
        showarrow=False,
        font=dict(color="white"),
        xanchor="center",
        yanchor="bottom"
    )
    
    # Add reward period shade for CS+ trials
    fig.add_shape(
        type="rect",
        x0=2, y0=0,
        x1=2.5, y1=num_trials+1,
        fillcolor="rgba(255,255,0,0.2)",
        line=dict(width=0),
        layer="below"
    )
    
    # Add annotation for reward period
    fig.add_annotation(
        x=2.25, y=num_trials+0.5,
        text="Reward",
        showarrow=False,
        font=dict(color="black"),
        xanchor="center",
        yanchor="bottom"
    )
    
    # Add y-axis trial type labels
    for i, trial in enumerate(trials):
        trial_type = trial_types[i]
        color = "red" if trial_type == "CS+" else "blue"
        
        fig.add_annotation(
            x=window[0] - 0.5, y=i+1,
            text=trial_type,
            showarrow=False,
            font=dict(color=color),
            xanchor="right",
            yanchor="middle"
        )
    
    # Add frames to the figure
    fig.frames = frames
    
    # Configure animation settings
    animation_settings = dict(
        frame=dict(duration=150, redraw=True),
        fromcurrent=True,
        mode="immediate"
    )
    
    # Add animation buttons
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[
                dict(label="Play",
                     method="animate",
                     args=[None, animation_settings]),
                dict(label="Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                       mode="immediate")])
            ],
            x=0.1, y=1.15,
            xanchor="right", yanchor="top"
        )]
    )
    
    # Add slider for manual navigation
    sliders = [dict(
        active=0,
        steps=[dict(
            method="animate",
            args=[[f"frame_{i+1}"], animation_settings],
            label=f"Trial {i+1}"
        ) for i in range(num_trials)],
        x=0.1, y=-0.05,
        len=0.9,
        xanchor="left", yanchor="top"
    )]
    
    # Set layout
    fig.update_layout(
        title="Animated Lick Heatmap (Trial by Trial)",
        xaxis_title="Time from Odor Onset (s)",
        yaxis_title="Trial Number",
        yaxis=dict(autorange="reversed"),  # First trial at top
        sliders=sliders,
        height=600,
        width=800
    )
    
    return fig

def create_animated_learning_curve(data, bin_size=3):
    """
    Create an animated learning curve showing response development over time.
    
    Parameters:
    - data: DataFrame with event data
    - bin_size: Number of trials to bin together
    
    Returns:
    - Plotly figure object
    """
    if data.empty or 'trial_type' not in data.columns:
        return None
    
    # Get odor onset events
    odor_events = data[data['event_code'] == 3].copy()
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
    
    # Create binned trials
    max_trial = trial_df['trial_number'].max()
    bin_edges = list(range(1, max_trial + bin_size, bin_size))
    if bin_edges[-1] < max_trial:
        bin_edges.append(max_trial + 1)
    
    # Create bin labels
    labels = [f"{e}-{min(e+bin_size-1, max_trial)}" for e in bin_edges[:-1]]
    trial_df['bin'] = pd.cut(trial_df['trial_number'], bins=bin_edges, labels=labels, include_lowest=True, right=False)
    
    # Create animated figure
    fig = go.Figure()
    
    # Add frames for animation - one frame per bin
    frames = []
    
    for i, bin_label in enumerate(labels):
        # Calculate mean licks for each trial type up to this bin
        cs_plus_means = []
        cs_minus_means = []
        bin_labels_subset = labels[:i+1]
        
        for bin_l in bin_labels_subset:
            bin_data = trial_df[trial_df['bin'] == bin_l]
            
            cs_plus_mean = bin_data[bin_data['trial_type'] == 1]['lick_count'].mean()
            cs_minus_mean = bin_data[bin_data['trial_type'] == 2]['lick_count'].mean()
            
            if not np.isnan(cs_plus_mean):
                cs_plus_means.append(cs_plus_mean)
            else:
                cs_plus_means.append(0)
                
            if not np.isnan(cs_minus_mean):
                cs_minus_means.append(cs_minus_mean)
            else:
                cs_minus_means.append(0)
        
        frame = go.Frame(
            data=[
                go.Scatter(
                    x=bin_labels_subset,
                    y=cs_plus_means,
                    mode='lines+markers',
                    name='CS+',
                    line=dict(color='red', width=3),
                    marker=dict(size=10)
                ),
                go.Scatter(
                    x=bin_labels_subset,
                    y=cs_minus_means,
                    mode='lines+markers',
                    name='CS-',
                    line=dict(color='blue', width=3),
                    marker=dict(size=10)
                )
            ],
            name=f"bin_{i+1}"
        )
        frames.append(frame)
    
    # Initial state - empty plot with legends
    fig.add_trace(go.Scatter(
        x=[labels[0]],
        y=[0],
        mode='lines+markers',
        name='CS+',
        line=dict(color='red', width=3),
        marker=dict(size=10)
    ))
    
    fig.add_trace(go.Scatter(
        x=[labels[0]],
        y=[0],
        mode='lines+markers',
        name='CS-',
        line=dict(color='blue', width=3),
        marker=dict(size=10)
    ))
    
    # Add frames
    fig.frames = frames
    
    # Animation settings
    animation_settings = dict(
        frame=dict(duration=800, redraw=True),
        fromcurrent=True,
        mode="immediate"
    )
    
    # Add animation controls
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[
                dict(label="Play",
                     method="animate",
                     args=[None, animation_settings]),
                dict(label="Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                      mode="immediate")])
            ],
            x=0.1, y=1.15,
            xanchor="right", yanchor="top"
        )]
    )
    
    # Add slider
    sliders = [dict(
        active=0,
        steps=[dict(
            method="animate",
            args=[[f"bin_{i+1}"], animation_settings],
            label=bin_label
        ) for i, bin_label in enumerate(labels)],
        x=0.1, y=-0.05,
        len=0.9,
        xanchor="left", yanchor="top"
    )]
    
    # Set layout
    fig.update_layout(
        title="Animated Learning Curve",
        xaxis_title="Trial Bins",
        yaxis_title="Average Lick Count",
        sliders=sliders,
        height=500,
        width=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_animated_lick_rate(data, trial_type=None, bin_width=0.1, smoothing=True):
    """
    Create an animated lick rate plot aligned to odor onset.
    
    Parameters:
    - data: DataFrame with event data
    - trial_type: Filter to show only CS+ (1) or CS- (2) trials, or None for all
    - bin_width: Width of time bins in seconds
    - smoothing: Whether to apply smoothing to the curve
    
    Returns:
    - Plotly figure object
    """
    if data.empty:
        return None
    
    # Get odor onset events
    odor_events = data[data['event_code'] == 3].copy()
    if odor_events.empty:
        return None
    
    # Filter by trial type if specified
    if trial_type is not None and 'trial_type' in data.columns:
        odor_events = odor_events[odor_events['trial_type'] == trial_type]
    
    if odor_events.empty:
        return None
    
    # Time window around odor onset
    window = (-5, 10)  # 5s before to 10s after
    
    # Create time bins
    bin_edges = np.arange(window[0], window[1] + bin_width, bin_width)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Initialize data for each trial
    trials = odor_events['trial_number'].unique()
    trials.sort()
    
    # Create animated figure
    fig = go.Figure()
    
    # Add frames for animation - one frame per trial, showing cumulative average
    frames = []
    
    for i, trial_count in enumerate(range(1, len(trials)+1)):
        # Calculate average lick rate across trials up to this point
        lick_rates = np.zeros(len(bin_centers))
        
        for j in range(trial_count):
            trial = trials[j]
            trial_odor = odor_events[odor_events['trial_number'] == trial]['timestamp'].iloc[0]
            trial_licks = data[(data['event_code'] == 7) & (data['trial_number'] == trial)]['timestamp'].values
            
            # Convert to relative time
            rel_lick_times = trial_licks - trial_odor
            
            # Filter licks within window
            rel_lick_times = rel_lick_times[(rel_lick_times >= window[0]) & (rel_lick_times <= window[1])]
            
            # Bin licks
            if len(rel_lick_times) > 0:
                hist, _ = np.histogram(rel_lick_times, bins=bin_edges)
                lick_rates += hist
        
        # Calculate average rate
        lick_rates = lick_rates / trial_count / bin_width  # convert to Hz
        
        # Apply smoothing if requested
        if smoothing:
            lick_rates = ndimage.gaussian_filter1d(lick_rates, sigma=2.0)
        
        # Create frame
        frame = go.Frame(
            data=[go.Scatter(
                x=bin_centers,
                y=lick_rates,
                mode='lines',
                line=dict(
                    width=3, 
                    color='red' if trial_type == 1 else 'blue' if trial_type == 2 else 'green'
                ),
                fill='tozeroy',
                fillcolor='rgba(255,0,0,0.2)' if trial_type == 1 else 
                         'rgba(0,0,255,0.2)' if trial_type == 2 else 
                         'rgba(0,255,0,0.2)'
            )],
            name=f"trial_{trial_count}"
        )
        frames.append(frame)
    
    # Initial state - empty plot
    fig.add_trace(go.Scatter(
        x=bin_centers,
        y=np.zeros(len(bin_centers)),
        mode='lines',
        line=dict(
            width=3, 
            color='red' if trial_type == 1 else 'blue' if trial_type == 2 else 'green'
        ),
        fill='tozeroy',
        fillcolor='rgba(255,0,0,0.2)' if trial_type == 1 else 
                 'rgba(0,0,255,0.2)' if trial_type == 2 else 
                 'rgba(0,255,0,0.2)'
    ))
    
    # Add vertical line at odor onset
    fig.add_shape(
        type="line",
        x0=0, y0=0,
        x1=0, y1=10,  # Set y1 to a high value
        line=dict(color="black", width=2, dash="dash")
    )
    
    # Add reward period indicator (for CS+ trials)
    if trial_type == 1 or trial_type is None:
        fig.add_shape(
            type="rect",
            x0=2, y0=0,
            x1=2.5, y1=10,  # Set y1 to a high value
            fillcolor="rgba(255,255,0,0.2)",
            line=dict(width=0)
        )
    
    # Add frames
    fig.frames = frames
    
    # Animation settings
    animation_settings = dict(
        frame=dict(duration=150, redraw=True),
        fromcurrent=True,
        mode="immediate"
    )
    
    # Add animation controls
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[
                dict(label="Play",
                     method="animate",
                     args=[None, animation_settings]),
                dict(label="Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                      mode="immediate")])
            ],
            x=0.1, y=1.15,
            xanchor="right", yanchor="top"
        )]
    )
    
    # Add slider
    sliders = [dict(
        active=0,
        steps=[dict(
            method="animate",
            args=[[f"trial_{i+1}"], animation_settings],
            label=f"Trials 1-{i+1}"
        ) for i in range(len(trials))],
        x=0.1, y=-0.05,
        len=0.9,
        xanchor="left", yanchor="top"
    )]
    
    # Determine title based on trial type
    if trial_type == 1:
        title = "Animated CS+ Lick Rate"
    elif trial_type == 2:
        title = "Animated CS- Lick Rate"
    else:
        title = "Animated Average Lick Rate"
    
    # Set layout
    fig.update_layout(
        title=title,
        xaxis_title="Time from Odor Onset (s)",
        yaxis_title="Lick Rate (Hz)",
        sliders=sliders,
        height=500,
        width=800
    )
    
    # Add annotations
    fig.add_annotation(
        x=0, y=9,
        text="Odor Onset",
        showarrow=False,
        yshift=10
    )
    
    if trial_type == 1 or trial_type is None:
        fig.add_annotation(
            x=2.25, y=9,
            text="Reward",
            showarrow=False,
            yshift=10
        )
    
    return fig

def create_animated_dashboard(data):
    """Create a comprehensive animated dashboard for analysis."""
    if data.empty:
        st.info("No data available. Please upload a data file.")
        return
    
    st.title("Animated Analysis Dashboard")
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs([
        "Trial-by-Trial Development", 
        "Learning Curve",
        "Response Rate Analysis"
    ])
    
    with tab1:
        st.header("Lick Heatmap Animation")
        st.write("""
        This visualization shows how licking activity develops trial by trial, aligned to odor onset.
        Each row represents a trial, with CS+ trials in red and CS- trials in blue.
        """)
        
        # Animation settings
        col1, col2 = st.columns([1, 1])
        with col1:
            bin_size = st.slider("Time bin size (seconds)", 0.05, 0.5, 0.1, 0.05)
        with col2:
            smoothing = st.checkbox("Apply smoothing", value=True)
        
        # Create and display heatmap
        heatmap_fig = create_animated_lick_heatmap(
            data, 
            bin_size=bin_size, 
            window=(-5, 10),
            smoothing=smoothing
        )
        
        if heatmap_fig:
            st.plotly_chart(heatmap_fig, use_container_width=True)
        else:
            st.warning("Insufficient data to create heatmap.")
    
    with tab2:
        st.header("Learning Curve Animation")
        st.write("""
        This animation shows how the licking response develops across trial bins.
        It highlights the divergence between CS+ and CS- responses over time.
        """)
        
        # Animation settings
        bin_size = st.slider("Trials per bin", 1, 10, 3, 1)
        
        # Create and display learning curve
        learning_fig = create_animated_learning_curve(data, bin_size=bin_size)
        
        if learning_fig:
            st.plotly_chart(learning_fig, use_container_width=True)
        else:
            st.warning("Insufficient data to create learning curve.")
    
    with tab3:
        st.header("Lick Rate Analysis")
        st.write("""
        These animations show how the average lick rate profile develops as more trials are included.
        The vertical dashed line marks odor onset, and the yellow region indicates the reward period.
        """)
        
        # Create two columns for CS+ and CS- plots
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("CS+ Trials")
            cs_plus_fig = create_animated_lick_rate(data, trial_type=1)
            
            if cs_plus_fig:
                st.plotly_chart(cs_plus_fig, use_container_width=True)
            else:
                st.warning("Insufficient CS+ data.")
        
        with col2:
            st.subheader("CS- Trials")
            cs_minus_fig = create_animated_lick_rate(data, trial_type=2)
            
            if cs_minus_fig:
                st.plotly_chart(cs_minus_fig, use_container_width=True)
            else:
                st.warning("Insufficient CS- data.")

def main():
    """Main function to run the animated analysis dashboard."""
    st.set_page_config(
        page_title="OHRBETS Animated Analysis",
        page_icon="🧠",
        layout="wide"
    )
    
    st.title("OHRBETS Animated Data Analysis")
    st.write("""
    This dashboard provides animated visualizations of Pavlovian conditioning data,
    allowing you to see how conditioning develops over the course of an experiment.
    """)
    
    # Data upload
    uploaded_file = st.file_uploader("Upload CSV data file", type="csv")
    
    # Example data option
    use_example = st.checkbox("Use example data instead", value=not bool(uploaded_file))
    
    if uploaded_file is not None:
        data = load_data(uploaded_file)
        create_animated_dashboard(data)
    elif use_example:
        st.info("Using example data...")
        # Import example data generation function
        from dashboard import create_example_data
        data = create_example_data()
        create_animated_dashboard(data)
    else:
        st.info("Please upload a data file or use example data.")

if __name__ == "__main__":
    main() 