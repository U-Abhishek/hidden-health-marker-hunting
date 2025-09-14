"""
Timeline Data Extraction Module
-------------------------------
Extracts location data from Google Timeline JSON format.
Takes the first entry for each day and extracts lat/lon coordinates.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import os


def extract_geo_coordinates(geo_string: str) -> Optional[Tuple[float, float]]:
    """
    Extract latitude and longitude from geo string format.
    
    Parameters
    ----------
    geo_string : str
        Geo string in format "geo:lat,lon" (e.g., "geo:34.844606,-117.085584")
    
    Returns
    -------
    Optional[Tuple[float, float]]
        A tuple of (latitude, longitude) in decimal degrees, or None if parsing fails.
    """
    if not geo_string or not geo_string.startswith("geo:"):
        return None
    
    try:
        # Remove "geo:" prefix and split by comma
        coords_str = geo_string[4:]  # Remove "geo:" prefix
        lat_str, lon_str = coords_str.split(',')
        
        lat = float(lat_str)
        lon = float(lon_str)
        
        return (lat, lon)
    except (ValueError, IndexError) as e:
        print(f"Error parsing geo string '{geo_string}': {e}")
        return None


def extract_date_from_timeline(timeline_entry: Dict[str, Any]) -> Optional[str]:
    """
    Extract date in YYYY-MM-DD format from timeline entry.
    
    Parameters
    ----------
    timeline_entry : Dict[str, Any]
        Timeline entry containing startTime and endTime
    
    Returns
    -------
    Optional[str]
        Date in YYYY-MM-DD format, or None if parsing fails.
    """
    # Try startTime first, then endTime
    time_fields = ["startTime", "endTime"]
    
    for time_field in time_fields:
        if time_field in timeline_entry:
            time_str = timeline_entry[time_field]
            try:
                # Parse ISO format with timezone
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d")
            except ValueError as e:
                print(f"Error parsing {time_field} '{time_str}': {e}")
                continue
    
    return None


def extract_location_from_timeline_entry(timeline_entry: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    Extract location coordinates from a timeline entry.
    Prioritizes visit locations over activity locations.
    
    Parameters
    ----------
    timeline_entry : Dict[str, Any]
        Timeline entry containing visit or activity data
    
    Returns
    -------
    Optional[Tuple[float, float]]
        A tuple of (latitude, longitude) in decimal degrees, or None if no location found.
    """
    # Priority 1: Visit location (more specific)
    if "visit" in timeline_entry:
        visit = timeline_entry["visit"]
        if "topCandidate" in visit and "placeLocation" in visit["topCandidate"]:
            geo_string = visit["topCandidate"]["placeLocation"]
            return extract_geo_coordinates(geo_string)
    
    # Priority 2: Activity start location
    if "activity" in timeline_entry:
        activity = timeline_entry["activity"]
        if "start" in activity:
            geo_string = activity["start"]
            return extract_geo_coordinates(geo_string)
    
    # Priority 3: Activity end location
    if "activity" in timeline_entry:
        activity = timeline_entry["activity"]
        if "end" in activity:
            geo_string = activity["end"]
            return extract_geo_coordinates(geo_string)
    
    return None


def extract_daily_locations(timeline_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract daily location data from Google Maps timeline JSON, taking the first entry for each day.
    
    Parameters
    ----------
    timeline_data : List[Dict[str, Any]]
        List of timeline entries from Google Maps Timeline JSON
    
    Returns
    -------
    List[Dict[str, Any]]
        List of daily location data in format:
        [
            {
                "lat": float,
                "lon": float, 
                "date_str": str
            },
            ...
        ]
    """
    daily_location_data = []
    processed_dates = set()  # Track dates we've already processed
    
    for entry in timeline_data:
        # Extract date from this entry
        date_str = extract_date_from_timeline(entry)
        if not date_str:
            continue
        
        # Skip if we've already processed this date
        if date_str in processed_dates:
            continue
        
        # Extract location coordinates
        coordinates = extract_location_from_timeline_entry(entry)
        if not coordinates:
            continue
        
        lat, lon = coordinates
        
        # Create daily location data for this day
        daily_data = {
            "lat": lat,
            "lon": lon, 
            "date_str": date_str
        }
        
        daily_location_data.append(daily_data)
        processed_dates.add(date_str)
        
        print(f"Date: {date_str} -> Lat: {lat:.6f}, Lon: {lon:.6f}")
    
    return daily_location_data


def load_timeline_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load timeline data from JSON file.
    
    Parameters
    ----------
    file_path : str
        Path to the timeline JSON file
    
    Returns
    -------
    List[Dict[str, Any]]
        Timeline data as list of dictionaries
    """
    if not os.path.exists(file_path):
        print(f"Error: Timeline file not found at {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error loading timeline data: {e}")
        return []


def process_timeline_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Main function to process Google Maps timeline file and extract daily location data.
    
    Parameters
    ----------
    file_path : str
        Path to the Google Maps timeline JSON file
    
    Returns
    -------
    List[Dict[str, Any]]
        List of daily location data with lat/lon/date for each day
    """
    print(f"Loading Google Maps timeline data from: {file_path}")
    timeline_data = load_timeline_data(file_path)
    
    if not timeline_data:
        return []
    
    print(f"Processing {len(timeline_data)} timeline entries...")
    daily_location_data = extract_daily_locations(timeline_data)
    
    print(f"Extracted daily location data for {len(daily_location_data)} unique days")
    return daily_location_data


# ---- Exports ----
__all__ = [
    "extract_daily_locations",
    "process_timeline_file", 
    "load_timeline_data",
    "extract_geo_coordinates",
    "extract_date_from_timeline",
    "extract_location_from_timeline_entry"
]


# if __name__ == "__main__":
#     # Example usage
#     timeline_file = "data/timeline_data.json"
#     daily_location_data = process_timeline_file(timeline_file)
    
#     print(f"\nExtracted daily location data:")
#     for i, daily_data in enumerate(daily_location_data[:10]):  # Show first 10
#         print(f"{i+1}. {daily_data}")
    
#     if len(daily_location_data) > 10:
#         print(f"... and {len(daily_location_data) - 10} more entries")