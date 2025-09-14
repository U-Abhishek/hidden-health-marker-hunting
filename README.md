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
├── part1_location_extraction/     # Google services → lat/long
├── part2_environmental_metrics/   # lat/long → environmental data
├── data/                          # Raw and processed data
└── notebooks/                     # Analysis notebooks
```


## Data Flow

Google Services → Lat/Long → Environmental APIs → Digital Biomarkers
