# Hidden Health Marker Hunting

Extracting environmental exposure metrics (sunshine, AQI, UV, etc.) from Google Maps location history to derive long-term digital biomarkers.

## Project Structure

This project is divided into two main parts:

### Part 1: Location Extraction
- Extract latitude/longitude coordinates from:
  - Google Maps location history
  - Google Photos geotagged images
  - Google Calendar location events

### Part 2: Environmental Metrics
- Convert lat/long coordinates to environmental exposure metrics:
  - Air Quality Index (AQI)
  - UV Index
  - Weather data
  - Sunshine exposure

## Folder Structure

```
hidden-health-marker-hunting/
├── location_extraction/           # Google services → lat/long
├── metrics_extraction/            # lat/long → environmental data
├── data/                          # Raw and processed data (gitignored)
├── notebooks/                     # Analysis notebooks
├── README.md
├── requirements.txt
└── .gitignore
```

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd hidden-health-marker-hunting
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Usage

### Part 1: Location Extraction
```bash
cd location_extraction
python main.py
```

### Part 2: Environmental Metrics
```bash
cd metrics_extraction
python main.py
```

## Data Flow

Google Services → Lat/Long → Environmental APIs → Digital Biomarkers

## Data Privacy

- All raw data is stored locally in the `data/` directory
- The `data/` directory is gitignored to protect personal information
- API keys and sensitive configuration are stored in `.env` files
