# Research Collection Metadata Dashboard

A Streamlit dashboard for visualizing download and view statistics from research collection metadata.

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

```bash
streamlit run app.py
```

The app will open in your browser at http://localhost:8501

## Features

- **Overview**: View total downloads/views and trends over time
- **Individual Item Analysis**: Analyze specific items in detail
- **Time Series Comparison**: Compare multiple items side by side
- **Top Performers**: See the most downloaded and viewed items

## Data

The app expects CSV files in the `data/` directory:
- `downloads.csv`: Monthly download statistics
- `views.csv`: Monthly view statistics