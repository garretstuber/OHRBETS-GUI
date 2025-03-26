import pandas as pd
import numpy as np
import random
from datetime import datetime
from scipy.stats import norm, gamma

# Define constants
NUM_TRIALS = 20
TRIAL_TYPES = [1, 2]  # 1 = CS+ (with reward), 2 = CS- (no reward)
EVENT_CODES = {
    'TRIAL_START': 1,
    'TRIAL_END': 2,
    'ODOR_ON': 3,
    'ODOR_OFF': 4,
    'REWARD_ON': 5,
    'REWARD_OFF': 6,
    'LICK': 7
}

EVENT_NAMES = {
    1: "Trial Start",
    2: "Trial End",
    3: "Odor On",
    4: "Odor Off",
    5: "Reward On",
    6: "Reward Off",
    7: "Lick"
}

def generate_lick_bursts(start_time, duration, burst_params):
    """Generate realistic lick bursts with specific patterns
    
    Args:
        start_time (float): When to start generating licks
        duration (float): Duration of the lick window in seconds
        burst_params (dict): Parameters defining bursting behavior
        
    Returns:
        list: List of timestamps for licks
    """
    lick_times = []
    current_time = start_time
    end_time = start_time + duration
    
    while current_time < end_time:
        # Check if we should start a burst based on burst probability
        if random.random() < burst_params['burst_prob']:
            # Determine number of licks in burst (usually 2-5 licks)
            burst_size = int(np.random.gamma(
                burst_params['burst_shape'], 
                burst_params['burst_scale']
            ))
            burst_size = max(1, min(burst_size, 15))  # Cap at reasonable values
            
            # Generate licks within burst with characteristic intraburst intervals
            burst_start = current_time
            for i in range(burst_size):
                # Add jitter to make it realistic
                jitter = random.uniform(-burst_params['jitter'], burst_params['jitter'])
                lick_time = burst_start + (i * burst_params['intraburst_interval']) + jitter
                
                # Only add if within window
                if lick_time <= end_time:
                    lick_times.append(lick_time)
                else:
                    break
            
            # Move time to after burst plus interburst interval
            current_time = burst_start + (burst_size * burst_params['intraburst_interval']) + burst_params['interburst_interval']
        else:
            # Move time forward by baseline interval
            current_time += burst_params['baseline_interval']
    
    return lick_times

def create_burst_params(profile_type, phase):
    """Create lick burst parameters based on animal profile and trial phase
    
    Args:
        profile_type (str): Type of animal profile ('normal', 'robust', etc.)
        phase (str): Trial phase ('baseline', 'anticipatory', 'reward')
        
    Returns:
        dict: Parameters for generating lick bursts
    """
    # Base parameters that match rodent licking behaviors
    # Baseline: ~1-2Hz
    # Reward-related: 5-10Hz
    # Intraburst interval: ~100-200ms
    # Interburst interval: ~0.5-1s
    base_params = {
        'baseline': {
            'burst_prob': 0.05,         # Low probability of bursts
            'burst_shape': 1.2,         # Shape parameter for gamma distribution
            'burst_scale': 1.2,         # Scale parameter for gamma distribution
            'intraburst_interval': 0.12, # ~8Hz within bursts
            'interburst_interval': 0.8,  # Longer pauses between bursts
            'baseline_interval': 0.5,    # ~2Hz baseline rate
            'jitter': 0.01              # Small timing jitter
        },
        'anticipatory': {
            'burst_prob': 0.2,          # Medium probability of bursts
            'burst_shape': 1.5,         # Shape parameter
            'burst_scale': 1.2,         # Scale parameter
            'intraburst_interval': 0.10, # ~10Hz within bursts
            'interburst_interval': 0.4,  # Medium pauses between bursts
            'baseline_interval': 0.3,    # ~3-4Hz baseline 
            'jitter': 0.02              # Timing jitter
        },
        'reward': {
            'burst_prob': 0.6,          # High probability of bursts
            'burst_shape': 2.5,         # Shape parameter for larger bursts
            'burst_scale': 1.0,         # Scale parameter
            'intraburst_interval': 0.08, # ~12Hz within bursts (can go up to 10-12Hz)
            'interburst_interval': 0.3,  # Shorter pauses between bursts
            'baseline_interval': 0.2,    # ~5Hz baseline
            'jitter': 0.01              # Small timing jitter
        }
    }
    
    # Modify parameters based on the animal profile
    params = base_params[phase].copy()
    
    if profile_type == 'robust':
        # Strong CS+/CS- discrimination, robust reward response
        if phase == 'reward':
            params['burst_prob'] *= 1.3         # More frequent bursts
            params['burst_shape'] *= 1.2        # Longer bursts
            params['intraburst_interval'] *= 0.9 # Faster licking
        elif phase == 'anticipatory':
            params['burst_prob'] *= 1.2         # More frequent bursts 
        elif phase == 'baseline':
            params['burst_prob'] *= 0.8         # Quieter during baseline
    
    elif profile_type == 'anticipatory':
        # Strong anticipatory licking before reward
        if phase == 'anticipatory':
            params['burst_prob'] *= 1.5         # Many anticipatory bursts
            params['burst_shape'] *= 1.3        # Longer bursts
        elif phase == 'reward':
            params['burst_prob'] *= 0.9         # Slightly reduced reward response
    
    elif profile_type == 'non_learner':
        # Poor discrimination between CS+ and CS-
        if phase == 'anticipatory':
            params['burst_prob'] *= 0.7         # Less anticipatory licking
        elif phase == 'reward':
            params['burst_prob'] *= 0.7         # Reduced reward response
            params['burst_shape'] *= 0.8        # Shorter bursts
        elif phase == 'baseline':
            params['burst_prob'] *= 1.5         # More random baseline licking
    
    return params

def generate_trial_licking(trial_type, odor_time, odor_duration, reward_time=None, profile_type='normal'):
    """Generate all licking events for a single trial with realistic bursting patterns
    
    Args:
        trial_type (int): Trial type (1=CS+, 2=CS-)
        odor_time (float): Timestamp of odor onset
        odor_duration (float): Duration of odor presentation
        reward_time (float): Timestamp of reward (None for CS- trials)
        profile_type (str): Type of animal profile
        
    Returns:
        list: List of lick timestamps
    """
    all_lick_times = []
    
    # 1. Pre-odor baseline period (5 seconds before odor)
    baseline_params = create_burst_params(profile_type, 'baseline')
    baseline_licks = generate_lick_bursts(
        odor_time - 5.0,  # Start 5s before odor
        5.0,              # Duration of baseline period
        baseline_params
    )
    all_lick_times.extend(baseline_licks)
    
    # 2. Anticipatory licking during odor period
    # For CS+ vs CS-, we modulate the probability of bursts
    anticipatory_params = create_burst_params(profile_type, 'anticipatory')
    
    # Adjust parameters based on trial type
    if trial_type == 2:  # CS-
        anticipatory_params['burst_prob'] *= 0.3  # Much lower anticipatory licking for CS-
    
    anticipatory_licks = generate_lick_bursts(
        odor_time,
        odor_duration,
        anticipatory_params
    )
    all_lick_times.extend(anticipatory_licks)
    
    # 3. Post-odor/reward period
    # For CS+ trials with reward, generate intensive licking after reward
    if trial_type == 1 and reward_time is not None:
        # Reward consumption licking (high rate for ~2-3s after reward)
        reward_params = create_burst_params(profile_type, 'reward')
        reward_licks = generate_lick_bursts(
            reward_time,
            3.0,  # Reward consumption period
            reward_params
        )
        all_lick_times.extend(reward_licks)
        
        # Gradual return to baseline (transition period)
        post_reward_params = create_burst_params(profile_type, 'anticipatory')
        post_reward_params['burst_prob'] *= 0.7  # Reducing, but still elevated
        post_reward_licks = generate_lick_bursts(
            reward_time + 3.0,  # After main reward consumption
            2.0,                # Transition period
            post_reward_params
        )
        all_lick_times.extend(post_reward_licks)
    else:
        # For CS- trials, just continue with low-rate baseline licking
        post_odor_params = create_burst_params(profile_type, 'baseline')
        if trial_type == 2:  # Further reduce for CS-
            post_odor_params['burst_prob'] *= 0.8
        
        post_odor_licks = generate_lick_bursts(
            odor_time + odor_duration,
            5.0,  # Post-odor period
            post_odor_params
        )
        all_lick_times.extend(post_odor_licks)
    
    return sorted(all_lick_times)  # Sort by time

def generate_dataset(profile_type="robust", num_trials=20, filename=None):
    """Generate a complete dataset with the specified animal profile"""
    # Initialize data structure and trial sequence
    data = []
    trial_sequence = []
    
    # Generate balanced trial sequence
    for _ in range(num_trials // 2):
        trial_sequence.extend([1, 2])  # Add one CS+ and one CS- trial
    random.shuffle(trial_sequence)  # Randomize the order
    
    # Set timing parameters
    iti_duration = 5.0  # seconds
    odor_duration = 2.0  # seconds
    reward_duration = 0.5  # seconds
    
    # Generate all events for each trial
    current_time = 0
    for trial_number, trial_type in enumerate(trial_sequence, 1):
        # 1. Trial start
        trial_start_time = current_time
        data.append({
            'event_code': EVENT_CODES['TRIAL_START'],
            'event_name': EVENT_NAMES[EVENT_CODES['TRIAL_START']],
            'timestamp': trial_start_time,
            'trial_number': trial_number,
            'trial_type': trial_type
        })
        
        # 2. Odor onset
        odor_on_time = trial_start_time + random.uniform(4.5, 5.5)  # Variable ITI
        data.append({
            'event_code': EVENT_CODES['ODOR_ON'],
            'event_name': EVENT_NAMES[EVENT_CODES['ODOR_ON']],
            'timestamp': odor_on_time,
            'trial_number': trial_number,
            'trial_type': trial_type
        })
        
        # 3. Odor offset
        odor_off_time = odor_on_time + odor_duration
        data.append({
            'event_code': EVENT_CODES['ODOR_OFF'],
            'event_name': EVENT_NAMES[EVENT_CODES['ODOR_OFF']],
            'timestamp': odor_off_time,
            'trial_number': trial_number,
            'trial_type': trial_type
        })
        
        # 4. Reward events (only for CS+ trials)
        reward_on_time = None
        reward_off_time = None
        
        if trial_type == 1:  # CS+
            reward_on_time = odor_off_time
            data.append({
                'event_code': EVENT_CODES['REWARD_ON'],
                'event_name': EVENT_NAMES[EVENT_CODES['REWARD_ON']],
                'timestamp': reward_on_time,
                'trial_number': trial_number,
                'trial_type': trial_type
            })
            
            reward_off_time = reward_on_time + reward_duration
            data.append({
                'event_code': EVENT_CODES['REWARD_OFF'],
                'event_name': EVENT_NAMES[EVENT_CODES['REWARD_OFF']],
                'timestamp': reward_off_time,
                'trial_number': trial_number,
                'trial_type': trial_type
            })
        
        # 5. Generate licks with realistic burst patterns
        lick_times = generate_trial_licking(
            trial_type, 
            odor_on_time, 
            odor_duration, 
            reward_on_time if trial_type == 1 else None,
            profile_type
        )
        
        # Add lick events to data
        for lick_time in lick_times:
            data.append({
                'event_code': EVENT_CODES['LICK'],
                'event_name': EVENT_NAMES[EVENT_CODES['LICK']],
                'timestamp': lick_time,
                'trial_number': trial_number,
                'trial_type': trial_type
            })
        
        # 6. Trial end time (ensure it captures all generated licking)
        trial_end_time = max(lick_times) + 1.0 if lick_times else odor_off_time + 5.0
        data.append({
            'event_code': EVENT_CODES['TRIAL_END'],
            'event_name': EVENT_NAMES[EVENT_CODES['TRIAL_END']],
            'timestamp': trial_end_time,
            'trial_number': trial_number,
            'trial_type': trial_type
        })
        
        # Update current time for next trial
        current_time = trial_end_time
    
    # Convert to DataFrame and sort by timestamp
    df = pd.DataFrame(data)
    df = df.sort_values('timestamp')
    
    # Save the data if filename is provided
    if filename:
        df.to_csv(filename, index=False)
        print(f"Generated {len(df)} events across {num_trials} trials")
        print(f"Data saved to {filename}")
    
    return df

# Generate and save datasets with different profiles
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Generate robust learner dataset
robust_filename = f"pavlovian_realistic_robust_{timestamp}.csv"
robust_data = generate_dataset("robust", NUM_TRIALS, robust_filename)

# Generate anticipatory learner dataset
anticipatory_filename = f"pavlovian_realistic_anticipatory_{timestamp}.csv"
anticipatory_data = generate_dataset("anticipatory", NUM_TRIALS, anticipatory_filename)

# Generate non-learner dataset
nonlearner_filename = f"pavlovian_realistic_nonlearner_{timestamp}.csv"
nonlearner_data = generate_dataset("non_learner", NUM_TRIALS, nonlearner_filename)

# Generate normal dataset
normal_filename = f"pavlovian_realistic_normal_{timestamp}.csv"
normal_data = generate_dataset("normal", NUM_TRIALS, normal_filename)

# Calculate and print licking rate statistics
def calculate_lick_statistics(data, name):
    licks = data[data['event_code'] == EVENT_CODES['LICK']]
    total_licks = len(licks)
    
    cs_plus_licks = licks[licks['trial_type'] == 1]
    cs_minus_licks = licks[licks['trial_type'] == 2]
    
    # Calculate lick rates during reward period for CS+ trials
    reward_period_licks = []
    for trial_num in data[data['trial_type'] == 1]['trial_number'].unique():
        reward_events = data[(data['trial_number'] == trial_num) & (data['event_code'] == EVENT_CODES['REWARD_ON'])]
        if not reward_events.empty:
            reward_time = reward_events.iloc[0]['timestamp']
            # Count licks in 2 second window after reward
            period_licks = licks[(licks['trial_number'] == trial_num) & 
                              (licks['timestamp'] >= reward_time) & 
                              (licks['timestamp'] < reward_time + 2.0)]
            if len(period_licks) > 0:
                reward_period_licks.append(len(period_licks))
    
    # Calculate interlick intervals within bursts
    ilis = []
    for trial_num in data['trial_number'].unique():
        trial_licks = licks[licks['trial_number'] == trial_num]['timestamp'].sort_values().values
        if len(trial_licks) > 1:
            trial_ilis = np.diff(trial_licks)
            # Only consider within-burst ILIs (typically <300ms)
            burst_ilis = trial_ilis[trial_ilis < 0.3]
            ilis.extend(burst_ilis)
    
    avg_reward_licks = np.mean(reward_period_licks) if reward_period_licks else 0
    avg_reward_rate = avg_reward_licks / 2.0  # Licks per second during reward
    mean_ili = np.mean(ilis) if ilis else 0
    burst_freq = 1.0 / mean_ili if mean_ili > 0 else 0
    
    print(f"\n{name} dataset statistics:")
    print(f"  Total events: {len(data)}")
    print(f"  Total licks: {total_licks}")
    print(f"  CS+ licks: {len(cs_plus_licks)}")
    print(f"  CS- licks: {len(cs_minus_licks)}")
    print(f"  Avg licks in 2s after reward: {avg_reward_licks:.1f} ({avg_reward_rate:.1f} Hz)")
    print(f"  Mean intraburst interval: {mean_ili*1000:.1f}ms (equivalent to {burst_freq:.1f} Hz)")
    return {
        'total_licks': total_licks,
        'cs_plus_licks': len(cs_plus_licks),
        'cs_minus_licks': len(cs_minus_licks),
        'avg_reward_licks': avg_reward_licks,
        'avg_reward_rate': avg_reward_rate,
        'mean_ili': mean_ili,
        'burst_freq': burst_freq
    }

print("\nLick statistics for generated datasets:")
robust_stats = calculate_lick_statistics(robust_data, "Robust")
anticipatory_stats = calculate_lick_statistics(anticipatory_data, "Anticipatory")
nonlearner_stats = calculate_lick_statistics(nonlearner_data, "Non-learner")
normal_stats = calculate_lick_statistics(normal_data, "Normal") 