import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats
from plotly.subplots import make_subplots
import base64
from io import BytesIO

def load_data(file_path):
    """Load and preprocess experimental data"""
    df = pd.read_csv(file_path)
    return df

def compute_session_metrics(df):
    """Compute key metrics for the session"""
    metrics = {}
    
    # Total trials
    trial_starts = df[df['event_code'] == 1]
    metrics['total_trials'] = len(trial_starts)
    
    # Trial types
    if 'trial_type' in df.columns:
        cs_plus_trials = trial_starts[trial_starts['trial_type'] == 1]
        cs_minus_trials = trial_starts[trial_starts['trial_type'] == 2]
        metrics['cs_plus_trials'] = len(cs_plus_trials)
        metrics['cs_minus_trials'] = len(cs_minus_trials)
    
    # Lick analysis
    licks = df[df['event_code'] == 7]
    if not licks.empty:
        metrics['total_licks'] = len(licks)
        
        # Group licks by trial
        licks_by_trial = licks.groupby('trial_number').size()
        metrics['mean_licks_per_trial'] = licks_by_trial.mean()
        metrics['median_licks_per_trial'] = licks_by_trial.median()
        
        # Licks by trial type
        if 'trial_type' in licks.columns:
            licks_cs_plus = licks[licks['trial_type'] == 1]
            licks_cs_minus = licks[licks['trial_type'] == 2]
            
            metrics['licks_cs_plus'] = len(licks_cs_plus)
            metrics['licks_cs_minus'] = len(licks_cs_minus)
            
            # Statistical test
            if len(licks_cs_plus) > 0 and len(licks_cs_minus) > 0:
                t_stat, p_value = stats.ttest_ind(
                    licks_cs_plus.groupby('trial_number').size(),
                    licks_cs_minus.groupby('trial_number').size()
                )
                metrics['t_stat'] = t_stat
                metrics['p_value'] = p_value
    
    # Session duration
    if not df.empty:
        metrics['session_duration'] = df['timestamp'].max() - df['timestamp'].min()
    
    return metrics

def plot_lick_raster(df, x_range=None):
    """Create a raster plot of licking behavior aligned to odor onset
    
    Args:
        df: DataFrame with experiment data
        x_range: Optional tuple (min, max) for x-axis range in seconds from odor onset
    """
    # Create a figure
    fig = go.Figure()
    
    # Find all trial numbers
    trial_numbers = df['trial_number'].unique()
    
    # Track min and max lick times for auto-ranging
    min_lick_time = float('inf')
    max_lick_time = float('-inf')
    
    # Process each trial
    for trial_num in sorted(trial_numbers):
        # Get trial type
        trial_type = df[df['trial_number'] == trial_num]['trial_type'].iloc[0] if 'trial_type' in df.columns else None
        
        # Get odor onset time for this trial
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial_num)]
        if odor_events.empty:
            continue
        odor_onset_time = odor_events.iloc[0]['timestamp']
        
        # Get reward onset time for this trial (if any)
        reward_time = None
        reward_events = df[(df['event_code'] == 5) & (df['trial_number'] == trial_num)]
        if not reward_events.empty:
            reward_time = reward_events.iloc[0]['timestamp'] - odor_onset_time  # Time relative to odor onset
        
        # Get licks for this trial
        licks = df[(df['event_code'] == 7) & (df['trial_number'] == trial_num)]
        
        # Convert to time relative to odor onset
        lick_times = licks['timestamp'].values - odor_onset_time
        
        # Update min/max lick times
        if len(lick_times) > 0:
            min_lick_time = min(min_lick_time, np.min(lick_times))
            max_lick_time = max(max_lick_time, np.max(lick_times))
        
        # Plot licks as tick marks
        color = 'blue' if trial_type == 1 else 'red' if trial_type == 2 else 'gray'
        name = f"Trial {trial_num} (CS+)" if trial_type == 1 else f"Trial {trial_num} (CS-)" if trial_type == 2 else f"Trial {trial_num}"
        
        # Add licks as vertical ticks (using line segments for each lick)
        if len(lick_times) > 0:
            for lick_time in lick_times:
                fig.add_trace(go.Scatter(
                    x=[lick_time, lick_time],
                    y=[trial_num - 0.3, trial_num + 0.3],  # Create vertical tick marks
                    mode='lines',
                    line=dict(color=color, width=1.5),
                    showlegend=False,
                    hoverinfo='x+text',
                    hovertext=f"Trial {trial_num}, Time: {lick_time:.2f}s"
                ))
        
        # Add odor onset marker
        is_first_trial = bool(trial_num == min(trial_numbers))  # Explicitly convert to built-in bool
        fig.add_trace(go.Scatter(
            x=[0],
            y=[trial_num],
            mode='markers',
            marker=dict(color='green', size=10, symbol='triangle-right'),
            name='Odor Onset',
            showlegend=is_first_trial  # Using explicitly converted bool
        ))
        
        # Add reward marker if applicable
        if reward_time is not None:
            # Only show in legend if this is the first reward marker we're adding
            has_reward_in_legend = any(trace.name == 'Reward' for trace in fig.data)
            show_in_legend = bool(is_first_trial and not has_reward_in_legend)  # Explicitly convert to built-in bool
            fig.add_trace(go.Scatter(
                x=[reward_time],
                y=[trial_num],
                mode='markers',
                marker=dict(color='purple', size=12, symbol='star'),
                name='Reward',
                showlegend=show_in_legend  # Using explicitly converted bool
            ))
    
    # Add legend entries for trial types
    if 'trial_type' in df.columns:
        # Create custom horizontal line segments for the legend
        fig.add_trace(go.Scatter(
            x=[None, None], 
            y=[None, None],
            mode='lines',
            line=dict(color='blue', width=1.5),
            name='CS+ Licks'
        ))
        
        fig.add_trace(go.Scatter(
            x=[None, None], 
            y=[None, None],
            mode='lines',
            line=dict(color='red', width=1.5),
            name='CS- Licks'
        ))
    
    # Add vertical line at odor onset (t=0)
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="green")
    
    # Add rectangle for approximate odor duration (2s)
    fig.add_vrect(x0=0, x1=2, fillcolor="rgba(0,255,0,0.1)", layer="below", line_width=0)
    
    # Set default x-range if not provided and there are licks to show
    if x_range is None:
        if min_lick_time != float('inf') and max_lick_time != float('-inf'):
            # Add 10% padding on each side
            padding = (max_lick_time - min_lick_time) * 0.1
            x_min = min_lick_time - padding
            x_max = max_lick_time + padding
            
            # Ensure we at least see odor onset and a bit before/after
            x_min = min(x_min, -2)
            x_max = max(x_max, 5)
        else:
            # Default if no licks
            x_min = -5
            x_max = 10
    else:
        x_min, x_max = x_range
    
    # Update layout
    fig.update_layout(
        title='Lick Raster Plot (Aligned to Odor Onset)',
        xaxis_title='Time from Odor Onset (s)',
        yaxis_title='Trial Number',
        yaxis=dict(
            tickmode='linear',
            tick0=min(trial_numbers),
            dtick=1
        ),
        xaxis=dict(
            range=[x_min, x_max]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        height=max(500, len(trial_numbers) * 25)  # Adjust height based on number of trials
    )
    
    return fig

def plot_lick_rate(df):
    """Plot lick rate over time"""
    # Filter for lick events
    licks = df[df['event_code'] == 7]
    
    # Group by trial number and count licks
    if 'trial_type' in df.columns:
        lick_counts = licks.groupby(['trial_number', 'trial_type']).size().reset_index(name='lick_count')
    else:
        lick_counts = licks.groupby(['trial_number']).size().reset_index(name='lick_count')
    
    # Create figure
    fig = px.bar(
        lick_counts,
        x='trial_number',
        y='lick_count',
        color='trial_type' if 'trial_type' in lick_counts.columns else None,
        labels={'trial_number': 'Trial', 'lick_count': 'Number of Licks', 'trial_type': 'Trial Type'},
        title='Lick Count per Trial',
        color_discrete_map={1: 'blue', 2: 'red'}
    )
    
    return fig

def compute_perievent_licking(df, align_event, trial_type=None, window=(-2, 5), bin_size=0.1):
    """Compute perievent licking histogram data aligned to a specific event
    
    Args:
        df: DataFrame with experiment data
        align_event: Event code to align to (e.g., 3 for odor onset, 5 for reward)
        trial_type: Optional filter for trial type (1=CS+, 2=CS-)
        window: Time window around event in seconds (pre, post)
        bin_size: Size of time bins in seconds
        
    Returns:
        DataFrame with binned lick counts
    """
    # Filter for alignment events
    alignment_events = df[df['event_code'] == align_event].copy()
    
    # Filter by trial type if specified
    if trial_type is not None:
        alignment_events = alignment_events[alignment_events['trial_type'] == trial_type]
    
    # If no events found, return empty DataFrame
    if alignment_events.empty:
        return pd.DataFrame({'time': [], 'lick_count': [], 'trial_type': []})
    
    # Create time bins
    bins = np.arange(window[0], window[1] + bin_size, bin_size)
    bin_centers = bins[:-1] + bin_size/2
    
    # Initialize counts array
    counts = np.zeros(len(bin_centers))
    
    # For each alignment event, find licks in the window
    licks = df[df['event_code'] == 7]  # Lick event code
    
    for _, event in alignment_events.iterrows():
        event_time = event['timestamp']
        trial_num = event['trial_number']
        
        # Get licks for this trial
        trial_licks = licks[licks['trial_number'] == trial_num]
        
        # Calculate relative time of licks
        rel_times = trial_licks['timestamp'] - event_time
        
        # Count licks in each bin
        for i, (bin_start, bin_end) in enumerate(zip(bins[:-1], bins[1:])):
            bin_licks = ((rel_times >= bin_start) & (rel_times < bin_end)).sum()
            counts[i] += bin_licks
    
    # Create result DataFrame
    result = pd.DataFrame({
        'time': bin_centers,
        'lick_count': counts,
        'trial_type': trial_type if trial_type is not None else 'all'
    })
    
    # Normalize by number of trials
    result['lick_rate'] = result['lick_count'] / len(alignment_events)
    
    return result

def plot_perievent_histogram(df, align_event_code, align_event_name, window=(-2, 5)):
    """Create a perievent time histogram for licking aligned to a specific event"""
    # Get data for CS+ and CS- trials
    cs_plus_data = compute_perievent_licking(df, align_event_code, trial_type=1, window=window)
    cs_minus_data = compute_perievent_licking(df, align_event_code, trial_type=2, window=window)
    
    # Create figure
    fig = go.Figure()
    
    # Add traces
    if not cs_plus_data.empty:
        fig.add_trace(go.Bar(
            x=cs_plus_data['time'],
            y=cs_plus_data['lick_rate'],
            name='CS+ Trials',
            marker_color='rgba(0, 0, 255, 0.7)',
            width=0.08  # Make bars thinner
        ))
    
    if not cs_minus_data.empty:
        fig.add_trace(go.Bar(
            x=cs_minus_data['time'],
            y=cs_minus_data['lick_rate'],
            name='CS- Trials',
            marker_color='rgba(255, 0, 0, 0.7)',
            width=0.08  # Make bars thinner
        ))
    
    # Add a vertical line at t=0 (alignment event)
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="green")
    
    # Update layout
    fig.update_layout(
        title=f'Licking Aligned to {align_event_name}',
        xaxis_title=f'Time from {align_event_name} (s)',
        yaxis_title='Licks per Trial',
        barmode='overlay',
        bargap=0,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig

def compute_trial_lick_timecourse(df, window=(-5, 10), bin_size=0.1):
    """Compute lick rate timecourse for each trial, aligned to odor onset
    
    Args:
        df: DataFrame with experiment data
        window: Time window around odor onset (pre, post)
        bin_size: Size of time bins in seconds
    
    Returns:
        Dict with trial-by-trial lick rate timecourses and mean ± SEM
    """
    # Create time bins
    bins = np.arange(window[0], window[1] + bin_size, bin_size)
    bin_centers = bins[:-1] + bin_size/2
    
    # Find odor onset events
    odor_onsets = df[df['event_code'] == 3].copy()
    
    # Separate by trial type
    cs_plus_trials = odor_onsets[odor_onsets['trial_type'] == 1]['trial_number'].unique()
    cs_minus_trials = odor_onsets[odor_onsets['trial_type'] == 2]['trial_number'].unique()
    
    # Find reward timing relative to odor onset (for plotting vertical lines)
    reward_timing = {}
    for trial_num in cs_plus_trials:
        odor_time = df[(df['event_code'] == 3) & (df['trial_number'] == trial_num)]['timestamp'].iloc[0]
        reward_times = df[(df['event_code'] == 5) & (df['trial_number'] == trial_num)]['timestamp']
        if not reward_times.empty:
            reward_timing[trial_num] = reward_times.iloc[0] - odor_time
    
    # Calculate average reward time if any rewards occurred
    mean_reward_time = np.mean(list(reward_timing.values())) if reward_timing else None
    
    # Initialize data structures
    cs_plus_trial_data = {trial: np.zeros(len(bin_centers)) for trial in cs_plus_trials}
    cs_minus_trial_data = {trial: np.zeros(len(bin_centers)) for trial in cs_minus_trials}
    
    # Get licks
    licks = df[df['event_code'] == 7]
    
    # Process CS+ trials
    for trial_num in cs_plus_trials:
        odor_time = df[(df['event_code'] == 3) & (df['trial_number'] == trial_num)]['timestamp'].iloc[0]
        trial_licks = licks[licks['trial_number'] == trial_num]
        rel_times = trial_licks['timestamp'] - odor_time
        
        # Count licks in each bin
        for i, (bin_start, bin_end) in enumerate(zip(bins[:-1], bins[1:])):
            bin_licks = ((rel_times >= bin_start) & (rel_times < bin_end)).sum()
            cs_plus_trial_data[trial_num][i] = bin_licks / bin_size  # Convert to rate (licks/sec)
    
    # Process CS- trials
    for trial_num in cs_minus_trials:
        odor_time = df[(df['event_code'] == 3) & (df['trial_number'] == trial_num)]['timestamp'].iloc[0]
        trial_licks = licks[licks['trial_number'] == trial_num]
        rel_times = trial_licks['timestamp'] - odor_time
        
        # Count licks in each bin
        for i, (bin_start, bin_end) in enumerate(zip(bins[:-1], bins[1:])):
            bin_licks = ((rel_times >= bin_start) & (rel_times < bin_end)).sum()
            cs_minus_trial_data[trial_num][i] = bin_licks / bin_size  # Convert to rate (licks/sec)
    
    # Calculate statistics
    cs_plus_mean = np.mean(list(cs_plus_trial_data.values()), axis=0) if cs_plus_trial_data else np.zeros(len(bin_centers))
    cs_plus_sem = np.std(list(cs_plus_trial_data.values()), axis=0) / np.sqrt(len(cs_plus_trial_data)) if len(cs_plus_trial_data) > 0 else np.zeros(len(bin_centers))
    
    cs_minus_mean = np.mean(list(cs_minus_trial_data.values()), axis=0) if cs_minus_trial_data else np.zeros(len(bin_centers))
    cs_minus_sem = np.std(list(cs_minus_trial_data.values()), axis=0) / np.sqrt(len(cs_minus_trial_data)) if len(cs_minus_trial_data) > 0 else np.zeros(len(bin_centers))
    
    return {
        'time': bin_centers,
        'cs_plus_mean': cs_plus_mean,
        'cs_plus_sem': cs_plus_sem,
        'cs_minus_mean': cs_minus_mean,
        'cs_minus_sem': cs_minus_sem,
        'mean_reward_time': mean_reward_time
    }

def plot_mean_lick_timecourse(df, window=(-5, 10)):
    """Plot mean ± SEM lick rate aligned to odor onset with reward timing"""
    # Compute trial-by-trial lick rates
    results = compute_trial_lick_timecourse(df, window=window)
    
    # Create figure
    fig = go.Figure()
    
    # Add CS+ trace with error bands
    fig.add_trace(go.Scatter(
        x=results['time'],
        y=results['cs_plus_mean'],
        mode='lines',
        line=dict(color='blue', width=2),
        name='CS+ Mean'
    ))
    
    # Add CS+ error bands (mean ± SEM)
    fig.add_trace(go.Scatter(
        x=np.concatenate([results['time'], results['time'][::-1]]),
        y=np.concatenate([
            results['cs_plus_mean'] + results['cs_plus_sem'],
            (results['cs_plus_mean'] - results['cs_plus_sem'])[::-1]
        ]),
        fill='toself',
        fillcolor='rgba(0, 0, 255, 0.2)',
        line=dict(color='rgba(0, 0, 255, 0)'),
        hoverinfo='skip',
        showlegend=False
    ))
    
    # Add CS- trace with error bands
    fig.add_trace(go.Scatter(
        x=results['time'],
        y=results['cs_minus_mean'],
        mode='lines',
        line=dict(color='red', width=2),
        name='CS- Mean'
    ))
    
    # Add CS- error bands (mean ± SEM)
    fig.add_trace(go.Scatter(
        x=np.concatenate([results['time'], results['time'][::-1]]),
        y=np.concatenate([
            results['cs_minus_mean'] + results['cs_minus_sem'],
            (results['cs_minus_mean'] - results['cs_minus_sem'])[::-1]
        ]),
        fill='toself',
        fillcolor='rgba(255, 0, 0, 0.2)',
        line=dict(color='rgba(255, 0, 0, 0)'),
        hoverinfo='skip',
        showlegend=False
    ))
    
    # Add vertical lines for important events
    # Odor onset at t=0
    fig.add_vline(x=0, line_width=2, line_dash="solid", line_color="green", annotation_text="Odor Onset")
    
    # Reward delivery (average time)
    if results['mean_reward_time'] is not None:
        fig.add_vline(
            x=results['mean_reward_time'], 
            line_width=2, 
            line_dash="dash", 
            line_color="purple",
            annotation_text="Reward"
        )
    
    # Update layout
    fig.update_layout(
        title='Mean Lick Rate (± SEM) Aligned to Odor Onset',
        xaxis_title='Time from Odor Onset (s)',
        yaxis_title='Lick Rate (licks/sec)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified'
    )
    
    return fig

def plot_lick_raster_by_type(df, trial_type, x_range=None):
    """Create a raster plot for only CS+ or CS- trials
    
    Args:
        df: DataFrame with experiment data
        trial_type: Trial type to display (1=CS+, 2=CS-)
        x_range: Optional tuple (min, max) for x-axis range in seconds from odor onset
    """
    # Create a figure
    fig = go.Figure()
    
    # Filter for the specified trial type
    if 'trial_type' in df.columns:
        trial_numbers = df[df['trial_type'] == trial_type]['trial_number'].unique()
    else:
        return fig  # Return empty figure if no trial type info
    
    if len(trial_numbers) == 0:
        return fig  # Return empty figure if no trials of this type
    
    # Track min and max lick times for auto-ranging
    min_lick_time = float('inf')
    max_lick_time = float('-inf')
    
    # Track actual y-positions for sequential display
    y_positions = {}
    for i, trial_num in enumerate(sorted(trial_numbers), 1):
        y_positions[trial_num] = i
    
    # Process each trial
    for trial_num in sorted(trial_numbers):
        # Get y-position (sequential, not by trial number)
        y_pos = y_positions[trial_num]
        
        # Get odor onset time for this trial
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial_num)]
        if odor_events.empty:
            continue
        odor_onset_time = odor_events.iloc[0]['timestamp']
        
        # Get reward onset time for this trial (if any)
        reward_time = None
        reward_events = df[(df['event_code'] == 5) & (df['trial_number'] == trial_num)]
        if not reward_events.empty:
            reward_time = reward_events.iloc[0]['timestamp'] - odor_onset_time  # Time relative to odor onset
        
        # Get licks for this trial
        licks = df[(df['event_code'] == 7) & (df['trial_number'] == trial_num)]
        
        # Convert to time relative to odor onset
        lick_times = licks['timestamp'].values - odor_onset_time
        
        # Update min/max lick times
        if len(lick_times) > 0:
            min_lick_time = min(min_lick_time, np.min(lick_times))
            max_lick_time = max(max_lick_time, np.max(lick_times))
        
        # Set color based on trial type
        color = 'blue' if trial_type == 1 else 'red'
        name = f"Trial {trial_num}"
        
        # Add licks as vertical ticks (using line segments for each lick)
        if len(lick_times) > 0:
            for lick_time in lick_times:
                fig.add_trace(go.Scatter(
                    x=[lick_time, lick_time],
                    y=[y_pos - 0.3, y_pos + 0.3],  # Create vertical tick marks
                    mode='lines',
                    line=dict(color=color, width=1.5),
                    showlegend=False,
                    hoverinfo='x+text',
                    hovertext=f"Trial {trial_num}, Time: {lick_time:.2f}s"
                ))
        
        # Add odor onset marker
        is_first_trial = bool(y_pos == 1)  # First in display order
        fig.add_trace(go.Scatter(
            x=[0],
            y=[y_pos],
            mode='markers',
            marker=dict(color='green', size=10, symbol='triangle-right'),
            name='Odor Onset',
            showlegend=is_first_trial
        ))
        
        # Add reward marker if applicable
        if reward_time is not None:
            # Only show in legend if this is the first reward marker
            has_reward_in_legend = any(trace.name == 'Reward' for trace in fig.data)
            show_in_legend = bool(is_first_trial and not has_reward_in_legend)
            fig.add_trace(go.Scatter(
                x=[reward_time],
                y=[y_pos],
                mode='markers',
                marker=dict(color='purple', size=12, symbol='star'),
                name='Reward',
                showlegend=show_in_legend
            ))
    
    # Add vertical line at odor onset (t=0)
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="green")
    
    # Add rectangle for approximate odor duration (2s)
    fig.add_vrect(x0=0, x1=2, fillcolor="rgba(0,255,0,0.1)", layer="below", line_width=0)
    
    # Set x-range (default -5 to 10 if not specified)
    x_min, x_max = x_range if x_range else (-5, 10)
    
    # Update layout
    title = 'CS+ Lick Raster Plot' if trial_type == 1 else 'CS- Lick Raster Plot'
    fig.update_layout(
        title=title,
        xaxis_title='Time from Odor Onset (s)',
        yaxis_title='Trial (in sequence)',
        yaxis=dict(
            tickmode='linear',
            tick0=1,
            dtick=1,
            range=[0, len(trial_numbers) + 1]
        ),
        xaxis=dict(
            range=[x_min, x_max],
            dtick=1  # 1-second intervals
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        height=max(400, len(trial_numbers) * 30)  # Adjust height based on number of trials
    )
    
    return fig

def plot_heatmap_by_type(df, trial_type, window=(-5, 10), bin_size=0.1):
    """Create a heatmap visualization of licking activity for CS+ or CS- trials
    
    Args:
        df: DataFrame with experiment data
        trial_type: Trial type to display (1=CS+, 2=CS-)
        window: Time window around odor onset in seconds (pre, post)
        bin_size: Size of time bins in seconds
    
    Returns:
        Plotly figure with heatmap visualization
    """
    # Filter for the specified trial type
    if 'trial_type' not in df.columns:
        return go.Figure()  # Return empty figure if no trial type info
    
    # Get trial numbers for the specified trial type
    trial_numbers = sorted(df[df['trial_type'] == trial_type]['trial_number'].unique())
    
    if not trial_numbers:
        return go.Figure()  # Return empty figure if no trials of this type
    
    # Create time bins
    bins = np.arange(window[0], window[1] + bin_size, bin_size)
    bin_centers = bins[:-1] + bin_size/2
    
    # Initialize matrix to store lick counts: trials × time bins
    heatmap_data = np.zeros((len(trial_numbers), len(bin_centers)))
    
    # Get licks
    licks = df[df['event_code'] == 7]  # Lick event code
    
    # Process each trial
    for i, trial_num in enumerate(trial_numbers):
        # Get odor onset time for this trial
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial_num)]
        if odor_events.empty:
            continue
        odor_onset_time = odor_events.iloc[0]['timestamp']
        
        # Get licks for this trial
        trial_licks = licks[licks['trial_number'] == trial_num]
        
        # Calculate relative time of licks
        rel_times = trial_licks['timestamp'] - odor_onset_time
        
        # Count licks in each bin
        for j, (bin_start, bin_end) in enumerate(zip(bins[:-1], bins[1:])):
            bin_licks = ((rel_times >= bin_start) & (rel_times < bin_end)).sum()
            heatmap_data[i, j] = bin_licks
    
    # Create figure
    fig = go.Figure()
    
    # Add heatmap trace
    title = 'CS+ Lick Heatmap' if trial_type == 1 else 'CS- Lick Heatmap'
    colorscale = 'Blues' if trial_type == 1 else 'Reds'
    
    fig.add_trace(go.Heatmap(
        z=heatmap_data,
        x=bin_centers,
        y=[f"Trial {num}" for num in trial_numbers],
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(title="Lick Count"),
        hovertemplate="Trial: %{y}<br>Time: %{x:.2f}s<br>Licks: %{z}<extra></extra>"
    ))
    
    # Add vertical line at odor onset (t=0)
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="green")
    
    # Add rectangle for approximate odor duration (2s)
    fig.add_vrect(x0=0, x1=2, fillcolor="rgba(0,255,0,0.1)", layer="below", line_width=0)
    
    # Add reward markers for CS+ trials
    if trial_type == 1:
        for i, trial_num in enumerate(trial_numbers):
            # Get reward time for this trial
            odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial_num)]
            reward_events = df[(df['event_code'] == 5) & (df['trial_number'] == trial_num)]
            
            if not odor_events.empty and not reward_events.empty:
                odor_time = odor_events.iloc[0]['timestamp']
                reward_time = reward_events.iloc[0]['timestamp'] - odor_time
                
                # Add reward marker
                fig.add_shape(
                    type="line",
                    x0=reward_time, y0=i-0.5,
                    x1=reward_time, y1=i+0.5,
                    line=dict(color="purple", width=2)
                )
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title='Time from Odor Onset (s)',
        yaxis_title='Trial',
        xaxis=dict(
            range=window,
            dtick=1  # 1-second intervals
        ),
        yaxis=dict(
            autorange="reversed"  # First trial at top
        ),
        height=max(400, len(trial_numbers) * 25)  # Adjust height based on number of trials
    )
    
    return fig

def plot_trial_comparison(df, window=(-5, 10)):
    """Create a comparison visualization showing key differences between CS+ and CS- trials
    
    Args:
        df: DataFrame with experiment data
        window: Time window for analysis
    
    Returns:
        Plotly figure with comparison visualization
    """
    # Create figure with subplots: 2 rows, 2 columns
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Total Licks per Trial",
            "Lick Latency after Odor Onset",
            "Anticipatory Licking (0-2s)",
            "Post-Odor Licking (2-5s)"
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    # Filter for trial types
    if 'trial_type' not in df.columns:
        return fig  # Return empty figure if no trial type info
    
    # Get trial numbers
    cs_plus_trials = df[df['trial_type'] == 1]['trial_number'].unique()
    cs_minus_trials = df[df['trial_type'] == 2]['trial_number'].unique()
    
    if len(cs_plus_trials) == 0 or len(cs_minus_trials) == 0:
        return fig  # Not enough data
    
    # Get licks
    licks = df[df['event_code'] == 7]  # Lick event code
    
    # Custom colors with better opacity for bar plots
    cs_plus_color = 'rgba(25, 118, 210, 0.7)'  # Blue
    cs_minus_color = 'rgba(229, 57, 53, 0.7)'  # Red
    
    # Data point colors (darker)
    cs_plus_point_color = 'rgba(10, 50, 150, 0.8)'  # Darker blue
    cs_minus_point_color = 'rgba(150, 30, 30, 0.8)'  # Darker red
    
    # Bar positions
    bar_positions = [0, 1]  # CS+, CS-
    bar_width = 0.6
    
    # Statistics results storage
    stats_results = []
    
    # 1. Total licks per trial
    cs_plus_licks = []
    cs_minus_licks = []
    
    # Calculate total licks for each trial
    for trial in cs_plus_trials:
        trial_lick_count = len(licks[licks['trial_number'] == trial])
        cs_plus_licks.append(trial_lick_count)
    
    for trial in cs_minus_trials:
        trial_lick_count = len(licks[licks['trial_number'] == trial])
        cs_minus_licks.append(trial_lick_count)
    
    # Calculate mean and SEM
    cs_plus_mean = np.mean(cs_plus_licks)
    cs_plus_sem = np.std(cs_plus_licks) / np.sqrt(len(cs_plus_licks))
    cs_minus_mean = np.mean(cs_minus_licks)
    cs_minus_sem = np.std(cs_minus_licks) / np.sqrt(len(cs_minus_licks))
    
    # Add bar plots for total licks
    fig.add_trace(
        go.Bar(
            x=['CS+', 'CS-'],
            y=[cs_plus_mean, cs_minus_mean],
            error_y=dict(
                type='data',
                array=[cs_plus_sem, cs_minus_sem],
                visible=True,
                color='rgba(0,0,0,0.7)',
                thickness=1,
                width=4
            ),
            marker_color=[cs_plus_color, cs_minus_color],
            width=bar_width,
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Add individual data points for CS+ with slight jitter
    fig.add_trace(
        go.Scatter(
            x=np.random.uniform(-0.15, 0.15, len(cs_plus_licks)) + bar_positions[0],
            y=cs_plus_licks,
            mode='markers',
            marker=dict(color=cs_plus_point_color, size=4, opacity=0.7),
            name='CS+ Trials',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Add individual data points for CS- with slight jitter
    fig.add_trace(
        go.Scatter(
            x=np.random.uniform(-0.15, 0.15, len(cs_minus_licks)) + bar_positions[1],
            y=cs_minus_licks,
            mode='markers',
            marker=dict(color=cs_minus_point_color, size=4, opacity=0.7),
            name='CS- Trials',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Calculate statistics for total licks
    t_stat, p_value = stats.ttest_ind(cs_plus_licks, cs_minus_licks)
    df_value = len(cs_plus_licks) + len(cs_minus_licks) - 2  # Degrees of freedom
    stats_results.append({
        'metric': 'Total Licks',
        't': t_stat,
        'df': df_value,
        'p': p_value
    })
    
    # Add concise statistics display
    sig_symbol = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
    sig_text = f"t({df_value})={t_stat:.2f}, p={p_value:.3f} {sig_symbol}"
    
    fig.add_annotation(
        text=sig_text,
        x=0.5, y=1.05,
        xref="x domain", yref="y domain",
        showarrow=False,
        font=dict(size=10),
        row=1, col=1
    )
    
    # 2. First lick latency after odor onset
    cs_plus_latencies = []
    cs_minus_latencies = []
    
    # Calculate latency for each trial
    for trial in cs_plus_trials:
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial)]
        if odor_events.empty:
            continue
        
        odor_time = odor_events.iloc[0]['timestamp']
        trial_licks = licks[licks['trial_number'] == trial]
        
        if not trial_licks.empty:
            # Get licks after odor onset
            post_odor_licks = trial_licks[trial_licks['timestamp'] > odor_time]
            if not post_odor_licks.empty:
                first_lick = post_odor_licks.iloc[0]['timestamp']
                latency = first_lick - odor_time
                if 0 <= latency <= 10:  # Only count reasonable latencies
                    cs_plus_latencies.append(latency)
    
    for trial in cs_minus_trials:
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial)]
        if odor_events.empty:
            continue
        
        odor_time = odor_events.iloc[0]['timestamp']
        trial_licks = licks[licks['trial_number'] == trial]
        
        if not trial_licks.empty:
            # Get licks after odor onset
            post_odor_licks = trial_licks[trial_licks['timestamp'] > odor_time]
            if not post_odor_licks.empty:
                first_lick = post_odor_licks.iloc[0]['timestamp']
                latency = first_lick - odor_time
                if 0 <= latency <= 10:  # Only count reasonable latencies
                    cs_minus_latencies.append(latency)
    
    # Calculate mean and SEM for latencies
    cs_plus_lat_mean = np.mean(cs_plus_latencies) if cs_plus_latencies else 0
    cs_plus_lat_sem = np.std(cs_plus_latencies) / np.sqrt(len(cs_plus_latencies)) if cs_plus_latencies else 0
    cs_minus_lat_mean = np.mean(cs_minus_latencies) if cs_minus_latencies else 0
    cs_minus_lat_sem = np.std(cs_minus_latencies) / np.sqrt(len(cs_minus_latencies)) if cs_minus_latencies else 0
    
    # Add bar plots for latencies
    fig.add_trace(
        go.Bar(
            x=['CS+', 'CS-'],
            y=[cs_plus_lat_mean, cs_minus_lat_mean],
            error_y=dict(
                type='data',
                array=[cs_plus_lat_sem, cs_minus_lat_sem],
                visible=True,
                color='rgba(0,0,0,0.7)',
                thickness=1,
                width=4
            ),
            marker_color=[cs_plus_color, cs_minus_color],
            width=bar_width,
            showlegend=False
        ),
        row=1, col=2
    )
    
    # Add individual data points for CS+ latencies with slight jitter
    if cs_plus_latencies:
        fig.add_trace(
            go.Scatter(
                x=np.random.uniform(-0.15, 0.15, len(cs_plus_latencies)) + bar_positions[0],
                y=cs_plus_latencies,
                mode='markers',
                marker=dict(color=cs_plus_point_color, size=4, opacity=0.7),
                showlegend=False
            ),
            row=1, col=2
        )
    
    # Add individual data points for CS- latencies with slight jitter
    if cs_minus_latencies:
        fig.add_trace(
            go.Scatter(
                x=np.random.uniform(-0.15, 0.15, len(cs_minus_latencies)) + bar_positions[1],
                y=cs_minus_latencies,
                mode='markers',
                marker=dict(color=cs_minus_point_color, size=4, opacity=0.7),
                showlegend=False
            ),
            row=1, col=2
        )
    
    # Calculate statistics for latencies
    if len(cs_plus_latencies) > 0 and len(cs_minus_latencies) > 0:
        t_stat, p_value = stats.ttest_ind(cs_plus_latencies, cs_minus_latencies)
        df_value = len(cs_plus_latencies) + len(cs_minus_latencies) - 2  # Degrees of freedom
        stats_results.append({
            'metric': 'Lick Latency',
            't': t_stat,
            'df': df_value,
            'p': p_value
        })
        
        # Add statistics annotation
        sig_symbol = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
        sig_text = f"t({df_value})={t_stat:.2f}, p={p_value:.3f} {sig_symbol}"
        
        fig.add_annotation(
            text=sig_text,
            x=0.5, y=1.05,
            xref="x2 domain", yref="y2 domain",
            showarrow=False,
            font=dict(size=10),
            row=1, col=2
        )
    
    # 3. Anticipatory licking (during odor: 0-2s)
    cs_plus_anticipatory = []
    cs_minus_anticipatory = []
    
    # Calculate anticipatory licking for each trial
    for trial in cs_plus_trials:
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial)]
        if odor_events.empty:
            continue
        
        odor_time = odor_events.iloc[0]['timestamp']
        trial_licks = licks[licks['trial_number'] == trial]
        
        # Count licks during odor presentation (0-2s)
        anticipatory_licks = trial_licks[
            (trial_licks['timestamp'] >= odor_time) & 
            (trial_licks['timestamp'] <= odor_time + 2)
        ]
        
        cs_plus_anticipatory.append(len(anticipatory_licks))
    
    for trial in cs_minus_trials:
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial)]
        if odor_events.empty:
            continue
        
        odor_time = odor_events.iloc[0]['timestamp']
        trial_licks = licks[licks['trial_number'] == trial]
        
        # Count licks during odor presentation (0-2s)
        anticipatory_licks = trial_licks[
            (trial_licks['timestamp'] >= odor_time) & 
            (trial_licks['timestamp'] <= odor_time + 2)
        ]
        
        cs_minus_anticipatory.append(len(anticipatory_licks))
    
    # Calculate mean and SEM for anticipatory licking
    cs_plus_ant_mean = np.mean(cs_plus_anticipatory)
    cs_plus_ant_sem = np.std(cs_plus_anticipatory) / np.sqrt(len(cs_plus_anticipatory))
    cs_minus_ant_mean = np.mean(cs_minus_anticipatory)
    cs_minus_ant_sem = np.std(cs_minus_anticipatory) / np.sqrt(len(cs_minus_anticipatory))
    
    # Add bar plots for anticipatory licking
    fig.add_trace(
        go.Bar(
            x=['CS+', 'CS-'],
            y=[cs_plus_ant_mean, cs_minus_ant_mean],
            error_y=dict(
                type='data',
                array=[cs_plus_ant_sem, cs_minus_ant_sem],
                visible=True,
                color='rgba(0,0,0,0.7)',
                thickness=1,
                width=4
            ),
            marker_color=[cs_plus_color, cs_minus_color],
            width=bar_width,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Add individual data points for CS+ anticipatory licking with slight jitter
    fig.add_trace(
        go.Scatter(
            x=np.random.uniform(-0.15, 0.15, len(cs_plus_anticipatory)) + bar_positions[0],
            y=cs_plus_anticipatory,
            mode='markers',
            marker=dict(color=cs_plus_point_color, size=4, opacity=0.7),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Add individual data points for CS- anticipatory licking with slight jitter
    fig.add_trace(
        go.Scatter(
            x=np.random.uniform(-0.15, 0.15, len(cs_minus_anticipatory)) + bar_positions[1],
            y=cs_minus_anticipatory,
            mode='markers',
            marker=dict(color=cs_minus_point_color, size=4, opacity=0.7),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Calculate statistics for anticipatory licking
    t_stat, p_value = stats.ttest_ind(cs_plus_anticipatory, cs_minus_anticipatory)
    df_value = len(cs_plus_anticipatory) + len(cs_minus_anticipatory) - 2  # Degrees of freedom
    stats_results.append({
        'metric': 'Anticipatory Licking',
        't': t_stat,
        'df': df_value,
        'p': p_value
    })
    
    # Add statistics annotation
    sig_symbol = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
    sig_text = f"t({df_value})={t_stat:.2f}, p={p_value:.3f} {sig_symbol}"
    
    fig.add_annotation(
        text=sig_text,
        x=0.5, y=1.05,
        xref="x3 domain", yref="y3 domain",
        showarrow=False,
        font=dict(size=10),
        row=2, col=1
    )
    
    # 4. Post-odor licking (2-5s)
    cs_plus_post = []
    cs_minus_post = []
    
    # Calculate post-odor licking for each trial
    for trial in cs_plus_trials:
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial)]
        if odor_events.empty:
            continue
        
        odor_time = odor_events.iloc[0]['timestamp']
        trial_licks = licks[licks['trial_number'] == trial]
        
        # Count licks after odor presentation (2-5s)
        post_licks = trial_licks[
            (trial_licks['timestamp'] >= odor_time + 2) & 
            (trial_licks['timestamp'] <= odor_time + 5)
        ]
        
        cs_plus_post.append(len(post_licks))
    
    for trial in cs_minus_trials:
        odor_events = df[(df['event_code'] == 3) & (df['trial_number'] == trial)]
        if odor_events.empty:
            continue
        
        odor_time = odor_events.iloc[0]['timestamp']
        trial_licks = licks[licks['trial_number'] == trial]
        
        # Count licks after odor presentation (2-5s)
        post_licks = trial_licks[
            (trial_licks['timestamp'] >= odor_time + 2) & 
            (trial_licks['timestamp'] <= odor_time + 5)
        ]
        
        cs_minus_post.append(len(post_licks))
    
    # Calculate mean and SEM for post-odor licking
    cs_plus_post_mean = np.mean(cs_plus_post)
    cs_plus_post_sem = np.std(cs_plus_post) / np.sqrt(len(cs_plus_post))
    cs_minus_post_mean = np.mean(cs_minus_post)
    cs_minus_post_sem = np.std(cs_minus_post) / np.sqrt(len(cs_minus_post))
    
    # Add bar plots for post-odor licking
    fig.add_trace(
        go.Bar(
            x=['CS+', 'CS-'],
            y=[cs_plus_post_mean, cs_minus_post_mean],
            error_y=dict(
                type='data',
                array=[cs_plus_post_sem, cs_minus_post_sem],
                visible=True,
                color='rgba(0,0,0,0.7)',
                thickness=1,
                width=4
            ),
            marker_color=[cs_plus_color, cs_minus_color],
            width=bar_width,
            showlegend=False
        ),
        row=2, col=2
    )
    
    # Add individual data points for CS+ post-odor licking with slight jitter
    fig.add_trace(
        go.Scatter(
            x=np.random.uniform(-0.15, 0.15, len(cs_plus_post)) + bar_positions[0],
            y=cs_plus_post,
            mode='markers',
            marker=dict(color=cs_plus_point_color, size=4, opacity=0.7),
            showlegend=False
        ),
        row=2, col=2
    )
    
    # Add individual data points for CS- post-odor licking with slight jitter
    fig.add_trace(
        go.Scatter(
            x=np.random.uniform(-0.15, 0.15, len(cs_minus_post)) + bar_positions[1],
            y=cs_minus_post,
            mode='markers',
            marker=dict(color=cs_minus_point_color, size=4, opacity=0.7),
            showlegend=False
        ),
        row=2, col=2
    )
    
    # Calculate statistics for post-odor licking
    t_stat, p_value = stats.ttest_ind(cs_plus_post, cs_minus_post)
    df_value = len(cs_plus_post) + len(cs_minus_post) - 2  # Degrees of freedom
    stats_results.append({
        'metric': 'Post-Odor Licking',
        't': t_stat,
        'df': df_value,
        'p': p_value
    })
    
    # Add statistics annotation
    sig_symbol = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
    sig_text = f"t({df_value})={t_stat:.2f}, p={p_value:.3f} {sig_symbol}"
    
    fig.add_annotation(
        text=sig_text,
        x=0.5, y=1.05,
        xref="x4 domain", yref="y4 domain",
        showarrow=False,
        font=dict(size=10),
        row=2, col=2
    )
    
    # Set layout title without duplicating in subplots
    fig.update_layout(
        title=dict(
            text="CS+ vs CS- Trial Comparison",
            font=dict(size=18, color="#333"),
            x=0.5
        ),
        height=600,
        width=900,
        font=dict(family="Arial", size=12),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#ddd",
            borderwidth=1,
            font=dict(size=12)
        ),
        plot_bgcolor='rgba(240,240,240,0.2)',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=60, b=60)
    )
    
    # Update x-axes settings
    for i in range(1, 5):
        row = (i-1) // 2 + 1
        col = (i-1) % 2 + 1
        
        fig.update_xaxes(
            showgrid=True,
            gridcolor='rgba(200,200,200,0.3)',
            tickfont=dict(size=12),
            row=row, col=col
        )
    
    # Update y-axis labels
    fig.update_yaxes(
        title=dict(text="Number of Licks", font=dict(size=12, color="#444")),
        showgrid=True,
        gridcolor='rgba(200,200,200,0.3)',
        zeroline=True,
        zerolinecolor='rgba(0,0,0,0.2)',
        row=1, col=1
    )
    
    fig.update_yaxes(
        title=dict(text="Latency (s)", font=dict(size=12, color="#444")),
        showgrid=True,
        gridcolor='rgba(200,200,200,0.3)',
        zeroline=True,
        zerolinecolor='rgba(0,0,0,0.2)',
        row=1, col=2
    )
    
    fig.update_yaxes(
        title=dict(text="Number of Licks", font=dict(size=12, color="#444")),
        showgrid=True,
        gridcolor='rgba(200,200,200,0.3)',
        zeroline=True,
        zerolinecolor='rgba(0,0,0,0.2)',
        row=2, col=1
    )
    
    fig.update_yaxes(
        title=dict(text="Number of Licks", font=dict(size=12, color="#444")),
        showgrid=True,
        gridcolor='rgba(200,200,200,0.3)',
        zeroline=True,
        zerolinecolor='rgba(0,0,0,0.2)',
        row=2, col=2
    )
    
    # Add significance symbols explanation in footer
    footnote = "Statistical significance: ns = p>0.05, * = p<0.05, ** = p<0.01, *** = p<0.001"
    fig.add_annotation(
        text=footnote,
        xref="paper", yref="paper",
        x=0.5, y=-0.05,
        showarrow=False,
        font=dict(size=10, color="#555"),
        align="center"
    )
    
    return fig

def plot_learning_curve(df, bin_size=3):
    """Create a learning curve visualization showing how licking behavior changes across trials
    
    Args:
        df: DataFrame with experiment data
        bin_size: Number of trials to group together
    
    Returns:
        Plotly figure with learning curve visualization
    """
    # Filter for trial types
    if 'trial_type' not in df.columns:
        return go.Figure()  # Return empty figure if no trial type info
    
    # Get trial numbers
    all_trials = sorted(df['trial_number'].unique())
    if len(all_trials) < bin_size:
        return go.Figure()  # Not enough trials
    
    # Get licks and trial events
    licks = df[df['event_code'] == 7]  # Lick event code
    odor_onsets = df[df['event_code'] == 3]  # Odor onset
    
    # Initialize data structures
    anticipatory_cs_plus = []  # Licking during odor (0-2s)
    anticipatory_cs_minus = []
    trial_numbers = []
    discrimination_index = []  # (CS+ - CS-)/(CS+ + CS-)
    
    # Process trials in bins
    bin_edges = list(range(1, len(all_trials) + 1, bin_size))
    if bin_edges[-1] < len(all_trials):
        bin_edges.append(len(all_trials) + 1)
    
    for i in range(len(bin_edges) - 1):
        start_idx = bin_edges[i] - 1  # Convert to 0-indexed
        end_idx = bin_edges[i+1] - 1
        bin_trials = all_trials[start_idx:end_idx]
        
        # Track lick data for this bin
        bin_cs_plus_licks = 0
        bin_cs_minus_licks = 0
        bin_cs_plus_count = 0
        bin_cs_minus_count = 0
        
        # Process each trial in this bin
        for trial_num in bin_trials:
            # Get odor onset for this trial
            odor_event = odor_onsets[odor_onsets['trial_number'] == trial_num]
            if odor_event.empty:
                continue
            
            odor_time = odor_event.iloc[0]['timestamp']
            trial_type = odor_event.iloc[0]['trial_type'] if 'trial_type' in odor_event.columns else None
            
            # Skip if no trial type
            if trial_type is None:
                continue
                
            # Count anticipatory licks (during odor presentation: 0-2s)
            trial_licks = licks[licks['trial_number'] == trial_num]
            anticipatory_licks = trial_licks[
                (trial_licks['timestamp'] >= odor_time) & 
                (trial_licks['timestamp'] <= odor_time + 2)
            ]
            
            # Add to appropriate counter
            if trial_type == 1:  # CS+
                bin_cs_plus_licks += len(anticipatory_licks)
                bin_cs_plus_count += 1
            elif trial_type == 2:  # CS-
                bin_cs_minus_licks += len(anticipatory_licks)
                bin_cs_minus_count += 1
        
        # Calculate average licks per trial for this bin
        if bin_cs_plus_count > 0:
            anticipatory_cs_plus.append(bin_cs_plus_licks / bin_cs_plus_count)
        else:
            anticipatory_cs_plus.append(0)
            
        if bin_cs_minus_count > 0:
            anticipatory_cs_minus.append(bin_cs_minus_licks / bin_cs_minus_count)
        else:
            anticipatory_cs_minus.append(0)
        
        # Calculate discrimination index
        total_licks = bin_cs_plus_licks + bin_cs_minus_licks
        if total_licks > 0:
            d_index = (bin_cs_plus_licks - bin_cs_minus_licks) / total_licks
        else:
            d_index = 0
        discrimination_index.append(d_index)
        
        # Use middle trial number for x-axis
        middle_trial = (bin_trials[0] + bin_trials[-1]) / 2
        trial_numbers.append(middle_trial)
    
    # Create figure
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "Anticipatory Licking During Odor Presentation",
            "Discrimination Index (CS+ preference)"
        ),
        shared_xaxes=True,
        vertical_spacing=0.15
    )
    
    # Add anticipatory licking traces
    fig.add_trace(
        go.Scatter(
            x=trial_numbers,
            y=anticipatory_cs_plus,
            mode='lines+markers',
            name='CS+',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=trial_numbers,
            y=anticipatory_cs_minus,
            mode='lines+markers',
            name='CS-',
            line=dict(color='red', width=2),
            marker=dict(size=8)
        ),
        row=1, col=1
    )
    
    # Add discrimination index
    fig.add_trace(
        go.Scatter(
            x=trial_numbers,
            y=discrimination_index,
            mode='lines+markers',
            name='Discrimination Index',
            line=dict(color='purple', width=2),
            marker=dict(size=8)
        ),
        row=2, col=1
    )
    
    # Add horizontal line at y=0 for discrimination index
    fig.add_shape(
        type="line",
        x0=min(trial_numbers),
        y0=0,
        x1=max(trial_numbers),
        y1=0,
        line=dict(color="black", width=1, dash="dash"),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title="Learning Curve",
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    # Update axes
    fig.update_xaxes(title_text="Trial Number", row=2, col=1)
    fig.update_yaxes(title_text="Licks per Trial", row=1, col=1)
    fig.update_yaxes(
        title_text="(CS+ - CS-)/(CS+ + CS-)",
        range=[-1.1, 1.1],  # Range from -1 to 1 with a bit of padding
        row=2, col=1
    )
    
    return fig

def generate_report_html(data, metrics):
    """Generate an HTML report with all visualizations and analysis
    
    Args:
        data: DataFrame with experiment data
        metrics: Dictionary of session metrics
    
    Returns:
        HTML string with report content
    """
    # Fixed range for plots
    fixed_range = (-5, 10)
    
    # Create all figures
    mean_lick_fig = plot_mean_lick_timecourse(data)
    raster_plus_fig = plot_lick_raster_by_type(data, trial_type=1, x_range=fixed_range)
    raster_minus_fig = plot_lick_raster_by_type(data, trial_type=2, x_range=fixed_range)
    heatmap_plus_fig = plot_heatmap_by_type(data, trial_type=1, window=fixed_range)
    heatmap_minus_fig = plot_heatmap_by_type(data, trial_type=2, window=fixed_range)
    comparison_fig = plot_trial_comparison(data)
    learning_fig = plot_learning_curve(data)
    
    # Convert figures to HTML
    mean_lick_html = mean_lick_fig.to_html(full_html=False, include_plotlyjs='cdn')
    raster_plus_html = raster_plus_fig.to_html(full_html=False, include_plotlyjs=False)
    raster_minus_html = raster_minus_fig.to_html(full_html=False, include_plotlyjs=False)
    heatmap_plus_html = heatmap_plus_fig.to_html(full_html=False, include_plotlyjs=False)
    heatmap_minus_html = heatmap_minus_fig.to_html(full_html=False, include_plotlyjs=False)
    comparison_html = comparison_fig.to_html(full_html=False, include_plotlyjs=False)
    learning_html = learning_fig.to_html(full_html=False, include_plotlyjs=False)
    
    # Construct HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pavlovian Conditioning Analysis Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                line-height: 1.6;
            }}
            h1, h2, h3 {{
                color: #333;
            }}
            .metrics-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-box {{
                border: 1px solid #ddd;
                padding: 15px;
                border-radius: 5px;
                min-width: 200px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #0066cc;
                margin-top: 5px;
            }}
            .plot-container {{
                margin-bottom: 40px;
            }}
            .significance {{
                font-weight: bold;
                color: #cc0000;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>Pavlovian Conditioning Analysis Report</h1>
        <h2>Session Summary</h2>
        <div class="metrics-container">
            <div class="metric-box">
                <h3>Total Trials</h3>
                <div class="metric-value">{metrics.get('total_trials', 0)}</div>
            </div>
            <div class="metric-box">
                <h3>CS+ Trials</h3>
                <div class="metric-value">{metrics.get('cs_plus_trials', 0)}</div>
            </div>
            <div class="metric-box">
                <h3>CS- Trials</h3>
                <div class="metric-value">{metrics.get('cs_minus_trials', 0)}</div>
            </div>
            <div class="metric-box">
                <h3>Total Licks</h3>
                <div class="metric-value">{metrics.get('total_licks', 0)}</div>
            </div>
            <div class="metric-box">
                <h3>Mean Licks/Trial</h3>
                <div class="metric-value">{metrics.get('mean_licks_per_trial', 0):.1f}</div>
            </div>
            <div class="metric-box">
                <h3>Session Duration</h3>
                <div class="metric-value">{metrics.get('session_duration', 0):.1f}s</div>
            </div>
        </div>
    """
    
    # Add statistical analysis if available
    if 'p_value' in metrics:
        p_value = float(metrics['p_value'])
        t_stat = float(metrics['t_stat'])
        sig_text = "Significant difference between CS+ and CS- trials" if p_value < 0.05 else "No significant difference between CS+ and CS- trials"
        
        html_content += f"""
        <h2>Statistical Analysis</h2>
        <p>t-statistic: {t_stat:.3f}</p>
        <p>p-value: {p_value:.3f}</p>
        <div class="significance">{sig_text}</div>
        """
    
    # Add visualizations
    html_content += f"""
        <h2>Mean Lick Rate Timecourse</h2>
        <div class="plot-container">
            {mean_lick_html}
            <p>This plot shows the mean licking rate (± SEM) aligned to odor onset (t=0), 
            separated by trial type. The solid green line indicates odor onset, and the 
            dashed purple line indicates the average time of reward delivery for CS+ trials.</p>
        </div>
        
        <h2>CS+ Lick Raster Plot</h2>
        <div class="plot-container">
            {raster_plus_html}
            <p>This raster plot shows licking for CS+ trials only (with reward delivery).
            Each vertical line represents a lick, aligned to odor onset (t=0).
            The green triangle marks odor onset, and the purple star indicates reward delivery.</p>
        </div>
        
        <h2>CS+ Lick Heatmap</h2>
        <div class="plot-container">
            {heatmap_plus_html}
            <p>This heatmap provides another view of CS+ licking activity, with color intensity 
            representing lick density across time for each trial.</p>
        </div>
        
        <h2>CS- Lick Raster Plot</h2>
        <div class="plot-container">
            {raster_minus_html}
            <p>This raster plot shows licking for CS- trials only (without reward).
            Each vertical line represents a lick, aligned to odor onset (t=0).
            The green triangle marks odor onset.</p>
        </div>
        
        <h2>CS- Lick Heatmap</h2>
        <div class="plot-container">
            {heatmap_minus_html}
            <p>This heatmap provides another view of CS- licking activity, with color intensity 
            representing lick density across time for each trial.</p>
        </div>
        
        <h2>Learning Curve Analysis</h2>
        <div class="plot-container">
            {learning_html}
            <p>The learning curve shows how behavior changes across trials:
            <ul>
                <li><strong>Anticipatory Licking</strong>: Licks during odor presentation (0-2s)</li>
                <li><strong>Discrimination Index</strong>: Measures preference for CS+ over CS-
                    <ul>
                        <li>Formula: (CS+ licks - CS- licks) / (CS+ licks + CS- licks)</li>
                        <li>Values range from -1 (only responds to CS-) to +1 (only responds to CS+)</li>
                        <li>Values near 0 indicate no discrimination between odors</li>
                    </ul>
                </li>
            </ul>
            </p>
        </div>
        
        <h2>CS+ vs CS- Trial Comparison</h2>
        <div class="plot-container">
            {comparison_html}
            <p>This comparison highlights key differences between CS+ and CS- trials:
            <ul>
                <li><strong>Total Licks</strong>: Overall licking activity per trial</li>
                <li><strong>Lick Latency</strong>: Time to first lick after odor onset</li>
                <li><strong>Anticipatory Licking</strong>: Licks during odor presentation (0-2s)</li>
                <li><strong>Post-Odor Licking</strong>: Licks after odor offset but before reward (2-5s)</li>
            </ul>
            Asterisks (*) indicate statistically significant differences (p < 0.05).
            </p>
        </div>
    </body>
    </html>
    """
    
    return html_content

def get_download_link(html_content, filename="pavlovian_analysis_report.html"):
    """Generate a download link for the HTML report
    
    Args:
        html_content: HTML string with report content
        filename: Name of the file to download
    
    Returns:
        HTML download link
    """
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; padding: 10px 15px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">Download HTML Report</a>'
    return href

def main():
    """Streamlit app for offline data analysis"""
    st.title("Pavlovian Conditioning Data Analysis")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload CSV data file", type="csv")
    
    if uploaded_file is not None:
        # Load data
        data = load_data(uploaded_file)
        
        # Display basic info
        st.write(f"Loaded {len(data)} events from data file")
        
        # Check if we need to derive trial types
        if 'trial_type' not in data.columns:
            st.warning("No trial type information in the file. Using event patterns to infer trial types...")
            
            # We'll try to infer trial types from reward events
            # Assuming trial type 1 (CS+) has reward, and type 2 (CS-) doesn't
            trial_numbers = data['trial_number'].unique()
            trial_types = {}
            
            for trial in trial_numbers:
                # Check if this trial had a reward event
                reward_events = data[(data['trial_number'] == trial) & (data['event_code'] == 5)]
                if len(reward_events) > 0:
                    trial_types[trial] = 1  # CS+
                else:
                    trial_types[trial] = 2  # CS-
            
            # Add trial type to the dataframe
            data['trial_type'] = data['trial_number'].map(trial_types)
            
            st.success(f"Inferred trial types: {sum(v==1 for v in trial_types.values())} CS+ and {sum(v==2 for v in trial_types.values())} CS- trials")
        
        # Compute and display metrics
        metrics = compute_session_metrics(data)
        
        st.subheader("Session Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Trials", int(metrics.get('total_trials', 0)))
            # Use float() for session duration to ensure it's a Python built-in type
            session_duration = float(metrics.get('session_duration', 0))
            st.metric("Session Duration", f"{session_duration:.1f}s")
        
        with col2:
            st.metric("CS+ Trials", int(metrics.get('cs_plus_trials', 0)))
            st.metric("CS- Trials", int(metrics.get('cs_minus_trials', 0)))
        
        with col3:
            if 'total_licks' in metrics:
                st.metric("Total Licks", int(metrics['total_licks']))
                # Convert mean licks to float to ensure it's a Python built-in type
                mean_licks = float(metrics['mean_licks_per_trial'])
                st.metric("Mean Licks/Trial", f"{mean_licks:.1f}")
        
        # Statistical results
        if 'p_value' in metrics:
            st.subheader("Statistical Analysis")
            # Convert to built-in types to avoid numpy type issues
            t_stat = float(metrics['t_stat'])
            p_value = float(metrics['p_value'])
            st.write(f"t-statistic: {t_stat:.3f}")
            st.write(f"p-value: {p_value:.3f}")
            
            if p_value < 0.05:
                st.success("Significant difference in licking between CS+ and CS- trials")
            else:
                st.info("No significant difference in licking between CS+ and CS- trials")
        
        # Visualizations
        st.subheader("Visualizations")
        
        # Mean lick rate timecourse
        st.write("### Mean Lick Rate Timecourse")
        
        # Create timecourse plot
        window = st.slider(
            "Time window (seconds from odor onset)",
            min_value=-10.0,
            max_value=15.0,
            value=(-5.0, 10.0),
            step=0.5
        )
        
        lick_timecourse_fig = plot_mean_lick_timecourse(data, window=window)
        st.plotly_chart(lick_timecourse_fig, use_container_width=True)
        
        st.write("""
        This plot shows the mean licking rate (± SEM) aligned to odor onset (t=0), 
        separated by trial type. The solid green line indicates odor onset, and the 
        dashed purple line indicates the average time of reward delivery for CS+ trials.
        
        Note how CS+ trials (blue) typically show increased licking after odor onset, 
        with a larger increase following reward delivery. CS- trials (red) typically 
        show little to no increase in licking rate.
        """)
        
        # Perievent histograms
        st.write("### Perievent Time Histograms")
        
        # Create tabs for different alignments
        peth_tab1, peth_tab2 = st.tabs(["Aligned to Odor Onset", "Aligned to Reward"])
        
        with peth_tab1:
            # Perievent histogram aligned to odor onset
            odor_fig = plot_perievent_histogram(data, 3, "Odor Onset", window=(-2, 8))
            st.plotly_chart(odor_fig, use_container_width=True)
            
            st.write("""
            This histogram shows licking rate aligned to odor onset (t=0). 
            Notice how licking patterns differ between CS+ trials (blue) and CS- trials (red).
            For CS+ trials, anticipatory licking may increase during odor presentation,
            followed by a larger increase when reward is delivered.
            """)
        
        with peth_tab2:
            # Perievent histogram aligned to reward onset
            reward_fig = plot_perievent_histogram(data, 5, "Reward Delivery", window=(-2, 8))
            st.plotly_chart(reward_fig, use_container_width=True)
            
            st.write("""
            This histogram shows licking rate aligned to reward delivery (t=0).
            Note that only CS+ trials have reward events. Licking typically increases
            sharply after reward delivery and gradually returns to baseline.
            """)
        
        # Lick Raster Plots
        st.write("### Lick Raster Plots")
        
        # Combined lick raster plot
        st.write("#### Combined Trials Raster Plot")
        
        # Fixed x-axis range as requested
        fixed_range = (-5, 10)
        
        # Lick raster plot with fixed range
        st.plotly_chart(plot_lick_raster(data, x_range=fixed_range), use_container_width=True)
        
        # Separate CS+ and CS- plots using tabs
        cs_tabs = st.tabs(["CS+ Trials", "CS- Trials"])
        
        with cs_tabs[0]:
            # CS+ lick raster plot
            cs_plus_fig = plot_lick_raster_by_type(data, trial_type=1, x_range=fixed_range)
            st.plotly_chart(cs_plus_fig, use_container_width=True)
            
            # Add heatmap for CS+ trials
            st.write("#### CS+ Lick Heatmap")
            cs_plus_heatmap = plot_heatmap_by_type(data, trial_type=1, window=fixed_range)
            st.plotly_chart(cs_plus_heatmap, use_container_width=True)
            
            st.write("""
            This raster plot shows licking for CS+ trials only (with reward delivery).
            Each vertical line represents a lick, aligned to odor onset (t=0).
            The green triangle marks odor onset, and the purple star indicates reward delivery.
            Note the pattern of anticipatory licking during odor presentation and increased
            licking after reward delivery.
            
            The heatmap below provides another view of the same data, with color intensity 
            representing lick density across time for each trial.
            """)
        
        with cs_tabs[1]:
            # CS- lick raster plot
            cs_minus_fig = plot_lick_raster_by_type(data, trial_type=2, x_range=fixed_range)
            st.plotly_chart(cs_minus_fig, use_container_width=True)
            
            # Add heatmap for CS- trials
            st.write("#### CS- Lick Heatmap")
            cs_minus_heatmap = plot_heatmap_by_type(data, trial_type=2, window=fixed_range)
            st.plotly_chart(cs_minus_heatmap, use_container_width=True)
            
            st.write("""
            This raster plot shows licking for CS- trials only (without reward).
            Each vertical line represents a lick, aligned to odor onset (t=0).
            The green triangle marks odor onset. Note that there is typically 
            less licking during and after odor presentation compared to CS+ trials.
            
            The heatmap below provides another view of the same data, with color intensity 
            representing lick density across time for each trial.
            """)
        
        # Trial summary plot
        st.write("### Lick Count per Trial")
        st.plotly_chart(plot_lick_rate(data), use_container_width=True)
        
        # Add trial comparison
        st.write("### CS+ vs CS- Trial Comparison")
        comparison_fig = plot_trial_comparison(data)
        st.plotly_chart(comparison_fig, use_container_width=True)
        
        st.write("""
        This comparison highlights key differences between CS+ and CS- trials:
        - **Total Licks**: Overall licking activity per trial
        - **Lick Latency**: Time to first lick after odor onset
        - **Anticipatory Licking**: Licks during odor presentation (0-2s)
        - **Post-Odor Licking**: Licks after odor offset but before reward (2-5s)
        
        Asterisks (*) indicate statistically significant differences (p < 0.05).
        """)
        
        # Add the learning curve
        st.write("### Learning Curve Analysis")
        bin_size = st.slider(
            "Trials per bin",
            min_value=1,
            max_value=5,
            value=3,
            step=1,
            help="Number of trials to group together for the learning curve"
        )
        
        learning_fig = plot_learning_curve(data, bin_size=bin_size)
        st.plotly_chart(learning_fig, use_container_width=True)
        
        st.write("""
        The learning curve shows how behavior changes across trials:
        - **Anticipatory Licking**: Licks during odor presentation (0-2s)
        - **Discrimination Index**: Measures preference for CS+ over CS-
          - Formula: (CS+ licks - CS- licks) / (CS+ licks + CS- licks)
          - Values range from -1 (only responds to CS-) to +1 (only responds to CS+)
          - Values near 0 indicate no discrimination between odors
        
        As learning occurs, you should see increasing anticipatory licking for CS+ 
        and a positive trend in the discrimination index.
        """)
        
        # Add report download button
        if 'total_licks' in metrics:
            st.write("### Download Analysis Report")
            html_report = generate_report_html(data, metrics)
            download_link = get_download_link(html_report)
            st.markdown(download_link, unsafe_allow_html=True)
            
            st.info("""
            The HTML report contains all visualizations and analysis results shown above,
            formatted for easy sharing and presentation. Download it to view offline or
            to include in your research documentation.
            """)
        
        # Raw data table
        with st.expander("View Raw Data"):
            st.dataframe(data)

if __name__ == "__main__":
    main() 