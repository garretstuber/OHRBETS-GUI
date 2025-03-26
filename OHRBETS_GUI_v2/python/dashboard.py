import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analysis import (
    load_data, 
    compute_session_metrics, 
    plot_lick_raster_by_type,
    plot_heatmap_by_type,
    plot_mean_lick_timecourse,
    plot_trial_comparison,
    plot_learning_curve,
    plot_perievent_histogram,
    generate_report_html,
    get_download_link
)

# Set page config
st.set_page_config(
    page_title="Pavlovian Conditioning Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.8rem;
        color: #333;
        padding-top: 1rem;
        border-bottom: 1px solid #ddd;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f9f9f9;
        border-radius: 5px;
        padding: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
    .stat-significant {
        color: #4CAF50;
        font-weight: bold;
    }
    .stat-not-significant {
        color: #F44336;
        font-weight: bold;
    }
    .dashboard-container {
        padding: 0.5rem;
    }
    .plot-container {
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Title and description
    st.markdown("<h1 class='main-header'>Pavlovian Odor Conditioning Analysis Dashboard</h1>", unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.markdown("## Data Selection")
    uploaded_file = st.sidebar.file_uploader("Upload CSV data file", type="csv")
    
    # Example data option
    use_example_data = st.sidebar.checkbox("Use example data", value=not bool(uploaded_file))
    
    # Visualization options
    st.sidebar.markdown("## Visualization Options")
    show_raster = st.sidebar.checkbox("Show Raster Plots", value=True)
    show_heatmap = st.sidebar.checkbox("Show Heatmaps", value=True)
    show_timecourse = st.sidebar.checkbox("Show Mean Lick Timecourse", value=True)
    show_learning = st.sidebar.checkbox("Show Learning Curve", value=True)
    show_comparison = st.sidebar.checkbox("Show CS+/CS- Comparison", value=True)
    
    # Time window adjustment
    st.sidebar.markdown("## Time Window")
    time_window = st.sidebar.slider(
        "Time window (seconds from odor onset)",
        min_value=-10.0,
        max_value=15.0,
        value=(-5.0, 10.0),
        step=0.5
    )
    
    # Learning curve bin size
    bin_size = st.sidebar.slider(
        "Learning curve bin size",
        min_value=1,
        max_value=5,
        value=3,
        step=1
    )
    
    # Load data
    if uploaded_file is not None:
        data = load_data(uploaded_file)
    elif use_example_data:
        # Create example data if no file is uploaded
        data = create_example_data()
    else:
        st.info("Please upload a data file or use example data")
        return
    
    # Display main dashboard content
    with st.container():
        # Compute metrics
        metrics = compute_session_metrics(data)
        
        # Session summary metrics
        st.markdown("<h2 class='section-header'>Session Summary</h2>", unsafe_allow_html=True)
        
        # Display metrics in a grid layout
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-value'>{metrics.get('total_trials', 0)}</div>
                    <div class='metric-label'>Total Trials</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-value'>{metrics.get('cs_plus_trials', 0)}</div>
                    <div class='metric-label'>CS+ Trials</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        with col3:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-value'>{metrics.get('cs_minus_trials', 0)}</div>
                    <div class='metric-label'>CS- Trials</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        with col4:
            st.markdown(
                f"""
                <div class='metric-container'>
                    <div class='metric-value'>{int(metrics.get('total_licks', 0))}</div>
                    <div class='metric-label'>Total Licks</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # Statistical results
        if 'p_value' in metrics:
            st.markdown("<h2 class='section-header'>Statistical Analysis</h2>", unsafe_allow_html=True)
            
            p_value = float(metrics['p_value'])
            t_stat = float(metrics['t_stat'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(
                    f"""
                    <div class='metric-container'>
                        <div class='metric-value'>{t_stat:.3f}</div>
                        <div class='metric-label'>t-statistic</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
            with col2:
                st.markdown(
                    f"""
                    <div class='metric-container'>
                        <div class='metric-value'>{p_value:.3f}</div>
                        <div class='metric-label'>p-value</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            # Significance message
            sig_class = "stat-significant" if p_value < 0.05 else "stat-not-significant"
            sig_text = "Significant difference between CS+ and CS- trials" if p_value < 0.05 else "No significant difference between CS+ and CS- trials"
            
            st.markdown(f"<div class='{sig_class}'>{sig_text}</div>", unsafe_allow_html=True)
        
        # Visualizations
        st.markdown("<h2 class='section-header'>Visualizations</h2>", unsafe_allow_html=True)
        
        # Mean lick timecourse
        if show_timecourse:
            st.markdown("<h3>Mean Lick Rate Timecourse</h3>", unsafe_allow_html=True)
            timecourse_fig = plot_mean_lick_timecourse(data, window=time_window)
            st.plotly_chart(timecourse_fig, use_container_width=True)
        
        # Learning curve
        if show_learning:
            st.markdown("<h3>Learning Curve</h3>", unsafe_allow_html=True)
            learning_fig = plot_learning_curve(data, bin_size=bin_size)
            st.plotly_chart(learning_fig, use_container_width=True)
        
        # Trial comparison
        if show_comparison:
            st.markdown("<h3>CS+ vs CS- Comparison</h3>", unsafe_allow_html=True)
            comparison_fig = plot_trial_comparison(data, window=time_window)
            st.plotly_chart(comparison_fig, use_container_width=True)
        
        # Raster plots and heatmaps
        if show_raster or show_heatmap:
            # Create tabs for CS+ and CS-
            cs_tabs = st.tabs(["CS+ Trials", "CS- Trials"])
            
            with cs_tabs[0]:
                if show_raster:
                    st.markdown("<h3>CS+ Lick Raster Plot</h3>", unsafe_allow_html=True)
                    cs_plus_fig = plot_lick_raster_by_type(data, trial_type=1, x_range=time_window)
                    st.plotly_chart(cs_plus_fig, use_container_width=True)
                
                if show_heatmap:
                    st.markdown("<h3>CS+ Lick Heatmap</h3>", unsafe_allow_html=True)
                    cs_plus_heatmap = plot_heatmap_by_type(data, trial_type=1, window=time_window)
                    st.plotly_chart(cs_plus_heatmap, use_container_width=True)
            
            with cs_tabs[1]:
                if show_raster:
                    st.markdown("<h3>CS- Lick Raster Plot</h3>", unsafe_allow_html=True)
                    cs_minus_fig = plot_lick_raster_by_type(data, trial_type=2, x_range=time_window)
                    st.plotly_chart(cs_minus_fig, use_container_width=True)
                
                if show_heatmap:
                    st.markdown("<h3>CS- Lick Heatmap</h3>", unsafe_allow_html=True)
                    cs_minus_heatmap = plot_heatmap_by_type(data, trial_type=2, window=time_window)
                    st.plotly_chart(cs_minus_heatmap, use_container_width=True)
        
        # Download report button
        st.markdown("<h2 class='section-header'>Export Report</h2>", unsafe_allow_html=True)
        
        html_report = generate_report_html(data, metrics)
        download_link = get_download_link(html_report)
        st.markdown(download_link, unsafe_allow_html=True)
        
        with st.expander("Learn more about this dashboard"):
            st.markdown("""
            This dashboard provides interactive visualization of Pavlovian odor conditioning data, allowing researchers to:
            
            1. **Visualize licking behavior** across trial types (CS+ and CS-)
            2. **Track learning** across a session with the learning curve
            3. **Compare metrics** between trial types with statistical analysis
            4. **Export reports** for documentation and sharing
            
            The visualizations include:
            - **Mean Lick Rate**: Shows average licking behavior aligned to odor onset
            - **Raster Plots**: Displays individual licks as vertical lines for each trial
            - **Heatmaps**: Provides a color-coded visualization of lick density
            - **Learning Curve**: Tracks how behavior changes across the session
            - **CS+/CS- Comparison**: Directly compares key metrics between trial types
            
            You can customize the visualizations using the options in the sidebar.
            """)

def create_example_data():
    """Create example data for demonstration with realistic motivated animal behavior"""
    # Parameters
    num_trials = 100  # 100 trials total (50 CS+, 50 CS-)
    session_duration = 3600  # seconds (1 hour session)
    
    # Create empty dataframe
    df = pd.DataFrame(columns=['event_code', 'event_name', 'timestamp', 'trial_number', 'trial_type'])
    
    # Generate balanced trial sequence with exactly 50 CS+ and 50 CS- trials
    # First create equal numbers of each type
    trial_types = [1] * 50 + [2] * 50
    
    # Shuffle with constraints (no more than 3 of same type in a row)
    np.random.shuffle(trial_types)
    
    # Check for runs of more than 3 of the same type and fix if needed
    for i in range(len(trial_types) - 3):
        if trial_types[i] == trial_types[i+1] == trial_types[i+2] == trial_types[i+3]:
            # Find a position after i+3 with a different trial type to swap with i+3
            for j in range(i+4, len(trial_types)):
                if trial_types[j] != trial_types[i]:
                    # Swap positions i+3 and j
                    trial_types[i+3], trial_types[j] = trial_types[j], trial_types[i+3]
                    break
    
    # Event codes
    event_names = {
        1: "Trial Start",
        2: "Trial End",
        3: "Odor On",
        4: "Odor Off",
        5: "Reward On",
        6: "Reward Off",
        7: "Lick"
    }
    
    # Trial timing parameters
    trial_duration = session_duration / num_trials
    odor_duration = 2.0  # seconds
    reward_duration = 0.5  # seconds
    reward_delay = 0.0  # seconds after odor offset
    
    # Add baseline licking for period before first trial (1Hz)
    # This ensures there's consistent licking at the beginning of the session
    pre_session_duration = 10.0  # 10 seconds before first trial
    baseline_lick_rate = 1.0  # 1 Hz baseline licking rate
    
    rows = []
    current_time = -pre_session_duration  # Start with pre-session period
    
    # Add pre-session licking
    num_baseline_licks = np.random.poisson(baseline_lick_rate * pre_session_duration)
    for _ in range(num_baseline_licks):
        lick_time = current_time + np.random.uniform(0, pre_session_duration)
        rows.append({
            'event_code': 7,
            'event_name': event_names[7],
            'timestamp': lick_time,
            'trial_number': 0,  # Pre-session
            'trial_type': 0     # No trial type
        })
    
    # For each trial
    for trial_num, trial_type in enumerate(trial_types, 1):
        trial_start_time = current_time
        
        # Trial start
        rows.append({
            'event_code': 1,
            'event_name': event_names[1],
            'timestamp': trial_start_time,
            'trial_number': trial_num,
            'trial_type': trial_type
        })
        
        # Odor onset (2s after trial start)
        odor_onset_time = trial_start_time + 2.0
        rows.append({
            'event_code': 3,
            'event_name': event_names[3],
            'timestamp': odor_onset_time,
            'trial_number': trial_num,
            'trial_type': trial_type
        })
        
        # Odor offset
        odor_offset_time = odor_onset_time + odor_duration
        rows.append({
            'event_code': 4,
            'event_name': event_names[4],
            'timestamp': odor_offset_time,
            'trial_number': trial_num,
            'trial_type': trial_type
        })
        
        # Reward (only for CS+ trials)
        if trial_type == 1:
            reward_onset_time = odor_offset_time + reward_delay
            rows.append({
                'event_code': 5,
                'event_name': event_names[5],
                'timestamp': reward_onset_time,
                'trial_number': trial_num,
                'trial_type': trial_type
            })
            
            reward_offset_time = reward_onset_time + reward_duration
            rows.append({
                'event_code': 6,
                'event_name': event_names[6],
                'timestamp': reward_offset_time,
                'trial_number': trial_num,
                'trial_type': trial_type
            })
        
        # Generate licks for entire trial period
        trial_end_time = trial_start_time + trial_duration
        
        # Divide the trial into periods for different licking patterns
        periods = []
        
        # 1. Pre-odor period (baseline)
        periods.append(("pre-odor", trial_start_time, odor_onset_time, 1.0))  # 1Hz baseline
        
        if trial_type == 1:  # CS+ trials
            # Learning factor (increases across trials)
            trial_progress = min(1.0, (trial_num / 30))  # Reaches asymptote by trial 30
            
            # 2. Early odor period (immediate vigorous response)
            periods.append(("early-odor", odor_onset_time, odor_onset_time + 0.5, 
                           15.0 * (0.3 + 0.7 * trial_progress)))
            
            # 3. Mid odor period (slight tapering)
            periods.append(("mid-odor", odor_onset_time + 0.5, odor_onset_time + 1.0, 
                           10.0 * (0.3 + 0.7 * trial_progress)))
            
            # 4. Late odor period (further tapering)
            periods.append(("late-odor", odor_onset_time + 1.0, odor_offset_time, 
                           8.0 * (0.3 + 0.7 * trial_progress)))
            
            # 5. Reward period (very vigorous)
            periods.append(("reward", reward_onset_time, reward_onset_time + 2.0, 
                           25.0 * (0.4 + 0.6 * trial_progress)))
            
            # 6. Post-reward period (gradual return to baseline)
            periods.append(("post-reward", reward_onset_time + 2.0, trial_end_time, 
                           max(1.0, 6.0 - (trial_end_time - (reward_onset_time + 2.0)) / 2)))
        else:  # CS- trials
            # Initially some response to CS- that diminishes with learning
            trial_progress = min(1.0, (trial_num / 30))
            cs_minus_factor = max(0.1, 0.8 - 0.7 * trial_progress)  # Decreases from 0.8 to 0.1
            
            # 2. Early odor period (brief response)
            periods.append(("early-odor", odor_onset_time, odor_onset_time + 0.5, 
                           5.0 * cs_minus_factor))
            
            # 3. Late odor period (suppressed)
            periods.append(("late-odor", odor_onset_time + 0.5, odor_offset_time, 
                           2.0 * cs_minus_factor))
            
            # 4. Post-odor period (return to baseline)
            periods.append(("post-odor", odor_offset_time, trial_end_time, 
                           max(1.0, 3.0 - (trial_end_time - odor_offset_time) / 3)))
        
        # Generate licks for each period
        for period_name, start_time, end_time, rate in periods:
            duration = end_time - start_time
            num_licks = np.random.poisson(rate * duration)
            
            # If it's a high-rate period, generate bursts (8-12Hz)
            if rate > 3.0:
                remaining_licks = num_licks
                while remaining_licks > 0:
                    # Burst size depends on rate - higher rates = bigger bursts
                    max_burst_size = max(3, min(int(rate / 3), 8))  # Ensure max_burst_size is at least 3
                    burst_size = min(remaining_licks, np.random.randint(2, max_burst_size))
                    burst_start = start_time + np.random.uniform(0, max(0.01, duration - 0.5))
                    
                    for i in range(burst_size):
                        lick_time = burst_start + i * np.random.uniform(0.08, 0.12)  # 8-12Hz
                        if start_time <= lick_time < end_time:
                            rows.append({
                                'event_code': 7,
                                'event_name': event_names[7],
                                'timestamp': lick_time,
                                'trial_number': trial_num,
                                'trial_type': trial_type
                            })
                    
                    remaining_licks -= burst_size
            else:
                # For baseline/low rate, just distribute randomly
                for _ in range(num_licks):
                    lick_time = start_time + np.random.uniform(0, duration)
                    rows.append({
                        'event_code': 7,
                        'event_name': event_names[7],
                        'timestamp': lick_time,
                        'trial_number': trial_num,
                        'trial_type': trial_type
                    })
        
        # Trial end
        rows.append({
            'event_code': 2,
            'event_name': event_names[2],
            'timestamp': trial_end_time,
            'trial_number': trial_num,
            'trial_type': trial_type
        })
        
        current_time = trial_end_time
    
    # Add post-session licking at 1Hz
    post_session_duration = 10.0  # 10 seconds after last trial
    num_post_licks = np.random.poisson(baseline_lick_rate * post_session_duration)
    
    for _ in range(num_post_licks):
        lick_time = current_time + np.random.uniform(0, post_session_duration)
        rows.append({
            'event_code': 7,
            'event_name': event_names[7],
            'timestamp': lick_time,
            'trial_number': num_trials,  # Last trial
            'trial_type': 0  # No trial type for post-session
        })
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Verify we have exactly 50 of each trial type
    cs_plus_trials = df[df['trial_type'] == 1]['trial_number'].unique()
    cs_minus_trials = df[df['trial_type'] == 2]['trial_number'].unique()
    
    print(f"Generated {len(cs_plus_trials)} CS+ trials and {len(cs_minus_trials)} CS- trials")
    
    return df

if __name__ == "__main__":
    main() 