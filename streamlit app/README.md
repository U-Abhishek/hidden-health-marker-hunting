# Hidden Health Marker Hunting - Streamlit App

A Streamlit application for processing Google Timeline and Calendar data to extract location-based health markers and environmental exposure patterns.

## Features

- **File Upload**: Upload Google Timeline JSON and Calendar ICS files
- **Data Processing**: Extract location coordinates and dates from uploaded files
- **Visualization**: Interactive maps and charts showing location data over time
- **Data Export**: Download processed data as CSV files

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to the URL shown in the terminal (usually http://localhost:8501)

3. Follow the workflow:
   - **Data Upload**: Upload your Google Timeline JSON and Calendar ICS files
   - **Data Processing**: Extract location data from the uploaded files
   - **Visualization**: View interactive maps and charts of your location data
   - **Data Export**: Download the processed data for further analysis

## Data Sources

### Google Timeline Data
- Export your Google Timeline data as JSON from Google Takeout
- The app extracts daily location coordinates from timeline entries

### Google Calendar Data
- Export your Google Calendar as ICS file from Google Calendar settings
- Note: Calendar processing requires the ICS file to be converted to JSON first using the main project's calendar conversion tools

## File Structure

```
streamlit app/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── services/                 # Data processing services
│   ├── timeline_extraction.py
│   └── calender_extraction.py
├── data/                     # Uploaded and processed data
└── README.md                # This file
```

## Requirements

- Python 3.8+
- Streamlit
- Pandas
- Plotly
- httpx (for geocoding)
