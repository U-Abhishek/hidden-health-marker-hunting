# Hidden Health Marker Hunting

Extracting environmental exposure metrics (sunshine, AQI, UV, etc.) from Google Maps location history to derive long-term digital biomarkers.

## Project Structure

This project is divided into two main parts:

### Part 1: Location Extraction
- Extract latitude/longitude coordinates from:
  - Google Maps location history
  - Google Photos geotagged images (via Takeout)
  - Apple Photos geotagged images
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

#### Google Photos Takeout
Extract location data from Google Photos Takeout ZIP files:

```bash
# Basic usage - prints preview to stdout
python -m location_extraction.google_photos_takeout --zip ~/Downloads/Photos-from-2025.zip

# Save to file
python -m location_extraction.google_photos_takeout \
  --zip ~/Downloads/Photos-from-2025.zip \
  --out ~/Downloads/photos_points.parquet \
  --user user_123
```

**How to export Google Photos with Photo metadata enabled:**
1. Go to [Google Takeout](https://takeout.google.com/)
2. Select "Google Photos"
3. Choose "All photo albums included" or select specific albums
4. Under "File type & frequency", select "ZIP file"
5. Under "Include in export", make sure "Photo metadata" is checked
6. Click "Create export"

**Privacy note:** This extractor only reads JSON sidecar files containing metadata. No photo or video bytes are processed.

#### Apple Photos
Extract location data from Apple Photos library:

```bash
cd location_extraction
python photos_geo_export.py -o ~/Desktop/photos_geo.csv
```

### Part 2: Environmental Metrics
```bash
cd metrics_extraction
python main.py
```

## Data Format

All location extractors output data in a standardized format with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp_utc` | datetime | ISO 8601 UTC timestamp |
| `latitude` | float | Latitude in decimal degrees (-90 to 90) |
| `longitude` | float | Longitude in decimal degrees (-180 to 180) |
| `accuracy_m` | float | GPS accuracy in meters (optional) |
| `source` | string | Data source identifier (e.g., 'google_photos', 'apple_photos') |
| `provenance` | string | Data provenance information (e.g., 'takeout-sidecar') |
| `confidence` | float | Confidence score (0.0-1.0) |
| `user_id` | string | User identifier (optional) |

## Data Flow

Google Services → Lat/Long → Environmental APIs → Digital Biomarkers

## Data Privacy

- All raw data is stored locally in the `data/` directory
- The `data/` directory is gitignored to protect personal information
- API keys and sensitive configuration are stored in `.env` files
