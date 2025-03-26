# Pavlovian Odor Conditioning Analysis Dashboard

A data visualization and analysis tool for Pavlovian conditioning experiments with odor stimuli and licking responses.

![Dashboard Preview](dashboard_preview.png)

## Features

- **Real-time visualization** of licking behavior during experiments
- **Offline analysis** of previously collected data
- **Interactive plots** to explore behavioral patterns:
  - Raster plots showing individual licks aligned to odor onset
  - Heatmaps displaying lick density across trials
  - Mean lick rate timecourse with SEM bands
  - Learning curves tracking discrimination improvement
  - CS+ vs CS- comparative analysis
- **Statistical analysis** of differences between CS+ and CS- trials
- **Exportable reports** in HTML format for documentation and sharing

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Required Python packages: streamlit, pandas, numpy, plotly, scipy
  (These will be automatically installed if missing)

### Running the Dashboard

1. Make the script executable (one-time setup):
   ```bash
   chmod +x run_dashboard.sh
   ```

2. Run the dashboard:
   ```bash
   ./run_dashboard.sh
   ```

Or manually with:
```bash
streamlit run dashboard.py
```

The dashboard will open in your default web browser.

## Using the Dashboard

### Data Input

- **Upload CSV files** containing experimental data
- **Use example data** for demonstration and testing
- **View live data** during ongoing experiments (when connected to Arduino)

### Customizing Visualizations

Use the sidebar to:
- Select which plots to display
- Adjust time windows
- Change learning curve bin sizes
- Configure other visualization parameters

### Exporting Results

- **Download HTML reports** containing all visualizations and analysis results
- **Save CSV data** from experimental sessions

## Data Format

The dashboard expects CSV files with the following columns:
- `event_code`: Integer code for event type (1=Trial Start, 2=Trial End, 3=Odor On, 4=Odor Off, 5=Reward On, 6=Reward Off, 7=Lick)
- `event_name`: Text description of event (optional)
- `timestamp`: Time in seconds
- `trial_number`: Integer trial identifier
- `trial_type`: 1 for CS+ trials, 2 for CS- trials

## Contributing

Contributions to improve the dashboard are welcome. Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 