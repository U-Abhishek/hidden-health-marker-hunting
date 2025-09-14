"""
Environmental Data Extraction Service
------------------------------------
Integrates with location extraction services to fetch environmental conditions
(UV index, air quality, weather) for each location and date.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import os

from .env_conditions_module import get_environment_blocking
from .timeline_extraction import process_timeline_file
from .calender_extraction import oprate_calendar_data


def extract_environmental_data_for_locations(
    location_data: List[Dict[str, Any]], 
    google_api_key: Optional[str] = None,
    openuv_api_key: Optional[str] = None,
    max_requests: int = 50
) -> List[Dict[str, Any]]:
    """
    Extract environmental data for a list of location entries.
    
    Parameters
    ----------
    location_data : List[Dict[str, Any]]
        List of location data with 'lat', 'lon', 'date_str' keys
    google_api_key : str, optional
        Google Maps API key for air quality data
    openuv_api_key : str, optional
        OpenUV API key for UV data (optional)
    max_requests : int
        Maximum number of API requests to make (to avoid rate limits)
    
    Returns
    -------
    List[Dict[str, Any]]
        List of location data with added environmental information
    """
    enriched_data = []
    processed_count = 0
    
    print(f"Processing environmental data for {len(location_data)} locations...")
    print(f"Limiting to {max_requests} requests to avoid rate limits")
    
    for i, location in enumerate(location_data[:max_requests]):
        try:
            lat = location.get('lat')
            lon = location.get('lon')
            date_str = location.get('date_str')
            
            if not all([lat, lon, date_str]):
                print(f"Skipping location {i+1}: missing required data")
                continue
            
            print(f"Processing location {i+1}/{min(len(location_data), max_requests)}: {lat:.4f}, {lon:.4f} on {date_str}")
            
            # Get environmental data for this location and date
            env_data = get_environment_blocking(
                lat=lat,
                lon=lon,
                date_str=date_str,
                google_key=google_api_key,
                openuv_key=openuv_api_key
            )
            
            # Extract key environmental metrics
            enriched_location = location.copy()
            enriched_location['environmental_data'] = extract_key_metrics(env_data)
            enriched_data.append(enriched_location)
            
            processed_count += 1
            
            # Add a small delay to be respectful to APIs
            if i < len(location_data) - 1:
                import time
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error processing location {i+1}: {str(e)}")
            # Still add the location without environmental data
            enriched_data.append(location.copy())
            continue
    
    print(f"Successfully processed {processed_count} locations with environmental data")
    return enriched_data


def extract_key_metrics(env_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key environmental metrics from the full environmental data response.
    
    Parameters
    ----------
    env_data : Dict[str, Any]
        Full environmental data response from env_conditions_module
    
    Returns
    -------
    Dict[str, Any]
        Simplified environmental metrics for display
    """
    metrics = {
        'uv_index': None,
        'uv_index_max': None,
        'temperature': None,
        'humidity': None,
        'air_quality_index': None,
        'air_quality_level': None,
        'precipitation': None,
        'cloud_cover': None,
        'wind_speed': None,
        'data_sources': [],
        'errors': []
    }
    
    try:
        # Extract UV data from Open-Meteo
        weather = env_data.get('weather', {})
        if weather and 'sample_at_local_noon' in weather:
            sample = weather['sample_at_local_noon']
            if sample:
                metrics['uv_index'] = sample.get('uv_index')
                metrics['temperature'] = sample.get('temperature_2m')
                metrics['humidity'] = sample.get('relative_humidity_2m')
                metrics['precipitation'] = sample.get('precipitation')
                metrics['cloud_cover'] = sample.get('cloudcover')
                metrics['wind_speed'] = sample.get('wind_speed_10m')
        
        # Extract daily UV max from Open-Meteo
        if weather and 'raw' in weather:
            daily = weather['raw'].get('daily', {})
            if daily and 'uv_index_max' in daily:
                uv_max_values = daily['uv_index_max']
                if uv_max_values and len(uv_max_values) > 0:
                    metrics['uv_index_max'] = uv_max_values[0]
        
        # Extract air quality data from Google
        google_air = env_data.get('google_air_quality', {})
        if google_air and 'current' in google_air:
            current = google_air['current']
            if 'indexes' in current and len(current['indexes']) > 0:
                aqi_data = current['indexes'][0]
                metrics['air_quality_index'] = aqi_data.get('aqi')
                metrics['air_quality_level'] = aqi_data.get('category')
        
        # Track data sources
        if google_air and 'used' in google_air:
            metrics['data_sources'].extend([f"Google Air Quality: {source}" for source in google_air['used']])
        
        if weather and 'source' in weather:
            metrics['data_sources'].append(f"Weather: {weather['source']}")
        
        # Track any errors
        if 'error' in google_air:
            metrics['errors'].append(f"Google Air Quality: {google_air['error']}")
        
        if weather and 'error' in weather:
            metrics['errors'].append(f"Weather: {weather['error']}")
        
        uv_extra = env_data.get('uv_extra')
        if uv_extra and 'error' in uv_extra:
            metrics['errors'].append(f"OpenUV: {uv_extra['error']}")
        elif uv_extra:
            metrics['data_sources'].append("OpenUV")
    
    except Exception as e:
        metrics['errors'].append(f"Error extracting metrics: {str(e)}")
    
    return metrics


def process_timeline_with_environmental_data(
    timeline_file_path: str,
    google_api_key: Optional[str] = None,
    openuv_api_key: Optional[str] = None,
    max_requests: int = 50
) -> List[Dict[str, Any]]:
    """
    Process timeline file and extract environmental data for each location.
    
    Parameters
    ----------
    timeline_file_path : str
        Path to the timeline JSON file
    google_api_key : str, optional
        Google Maps API key for air quality data
    openuv_api_key : str, optional
        OpenUV API key for UV data
    max_requests : int
        Maximum number of API requests to make
    
    Returns
    -------
    List[Dict[str, Any]]
        Timeline data with environmental information
    """
    # First extract location data from timeline
    location_data = process_timeline_file(timeline_file_path)
    
    if not location_data:
        print("No location data found in timeline file")
        return []
    
    # Then enrich with environmental data
    enriched_data = extract_environmental_data_for_locations(
        location_data, 
        google_api_key, 
        openuv_api_key, 
        max_requests
    )
    
    return enriched_data


def process_calendar_with_environmental_data(
    calendar_file_path: str,
    google_api_key: Optional[str] = None,
    openuv_api_key: Optional[str] = None,
    max_requests: int = 50
) -> List[Dict[str, Any]]:
    """
    Process calendar file and extract environmental data for each event location.
    
    Parameters
    ----------
    calendar_file_path : str
        Path to the calendar JSON file
    google_api_key : str, optional
        Google Maps API key for air quality data
    openuv_api_key : str, optional
        OpenUV API key for UV data
    max_requests : int
        Maximum number of API requests to make
    
    Returns
    -------
    List[Dict[str, Any]]
        Calendar data with environmental information
    """
    # First extract location data from calendar
    location_data = oprate_calendar_data(calendar_file_path)
    
    if not location_data:
        print("No location data found in calendar file")
        return []
    
    # Then enrich with environmental data
    enriched_data = extract_environmental_data_for_locations(
        location_data, 
        google_api_key, 
        openuv_api_key, 
        max_requests
    )
    
    return enriched_data


def save_enriched_data(
    enriched_data: List[Dict[str, Any]], 
    output_file: str,
    data_type: str = "environmental"
):
    """
    Save enriched data to JSON file.
    
    Parameters
    ----------
    enriched_data : List[Dict[str, Any]]
        Data with environmental information
    output_file : str
        Path to save the data
    data_type : str
        Type of data for logging
    """
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(enriched_data)} {data_type} entries to {output_file}")
        
    except Exception as e:
        print(f"Error saving enriched data: {str(e)}")


def load_enriched_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load enriched data from JSON file.
    
    Parameters
    ----------
    file_path : str
        Path to the enriched data file
    
    Returns
    -------
    List[Dict[str, Any]]
        Loaded enriched data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading enriched data: {str(e)}")
        return []


# Export functions
__all__ = [
    "extract_environmental_data_for_locations",
    "extract_key_metrics", 
    "process_timeline_with_environmental_data",
    "process_calendar_with_environmental_data",
    "save_enriched_data",
    "load_enriched_data"
]
