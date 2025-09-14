#!/usr/bin/env python3
"""
Google Photos Takeout Extractor
-------------------------------
Extract location data from Google Photos Takeout ZIP files by parsing JSON sidecar files.

This module reads Google Photos Takeout archives and extracts timestamp, latitude, longitude,
and metadata from the JSON sidecar files that accompany photos and videos.

Supported file patterns:
- **/*.(jpg|jpeg|png|heic|mp4|mov).json
- **/*.(jpg|jpeg|png|heic|mp4|mov).metadata.json

The extracted data follows the standardized location schema used by the metrics extraction pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

# Standardized location schema columns
STANDARD_LOCATION_COLUMNS = [
    "timestamp_utc",      # ISO 8601 UTC timestamp
    "latitude",           # Decimal degrees
    "longitude",          # Decimal degrees
    "accuracy_m",         # GPS accuracy in meters (optional)
    "source",             # Data source identifier
    "provenance",         # Data provenance information
    "confidence",         # Confidence score (0.0-1.0)
    "user_id",           # User identifier (optional)
]

# File extensions to look for
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov"}

# JSON sidecar patterns
JSON_PATTERNS = [
    re.compile(r"\.(jpg|jpeg|png|heic|mp4|mov)\.json$", re.IGNORECASE),
    re.compile(r"\.(jpg|jpeg|png|heic|mp4|mov)\.metadata\.json$", re.IGNORECASE),
]


def is_json_sidecar(filename: str) -> bool:
    """Check if a filename matches the JSON sidecar pattern."""
    return any(pattern.search(filename) for pattern in JSON_PATTERNS)


def parse_timestamp(data: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract timestamp from Google Photos JSON data.
    
    Priority order:
    1. photoTakenTime.timestamp (UNIX seconds)
    2. creationTime.timestamp (UNIX seconds)  
    3. creationTime (ISO string)
    """
    # Try photoTakenTime.timestamp first
    if "photoTakenTime" in data and isinstance(data["photoTakenTime"], dict):
        timestamp = data["photoTakenTime"].get("timestamp")
        if timestamp:
            try:
                return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
            except (ValueError, TypeError):
                pass
    
    # Try creationTime.timestamp
    if "creationTime" in data and isinstance(data["creationTime"], dict):
        timestamp = data["creationTime"].get("timestamp")
        if timestamp:
            try:
                return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
            except (ValueError, TypeError):
                pass
    
    # Try creationTime as ISO string
    if "creationTime" in data and isinstance(data["creationTime"], str):
        try:
            # Handle various ISO formats
            dt_str = data["creationTime"]
            if dt_str.endswith("Z"):
                dt_str = dt_str.replace("Z", "+00:00")
            return datetime.fromisoformat(dt_str).astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass
    
    return None


def parse_location(data: Dict[str, Any]) -> tuple[Optional[float], Optional[float], Optional[float], bool]:
    """
    Extract location data from Google Photos JSON data.
    
    Returns:
        (latitude, longitude, accuracy_meters, is_estimated)
    """
    lat, lon, accuracy, is_estimated = None, None, None, False
    
    # Try geoData first (preferred)
    if "geoData" in data and isinstance(data["geoData"], dict):
        geo = data["geoData"]
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        accuracy = geo.get("accuracyMeters")
        is_estimated = geo.get("geoIsEstimated", False)
    
    # Fallback to geoDataExif
    elif "geoDataExif" in data and isinstance(data["geoDataExif"], dict):
        geo = data["geoDataExif"]
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        accuracy = geo.get("accuracyMeters")
        is_estimated = geo.get("geoIsEstimated", False)
    
    # Convert to float if possible
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
        accuracy = float(accuracy) if accuracy is not None else None
    except (ValueError, TypeError):
        lat, lon, accuracy = None, None, None
    
    return lat, lon, accuracy, is_estimated


def calculate_confidence(lat: Optional[float], lon: Optional[float], is_estimated: bool) -> float:
    """
    Calculate confidence score based on location data quality.
    
    Returns:
        0.8: lat/lon present and not estimated
        0.6: lat/lon present and estimated
        0.2: no lat/lon data
    """
    if lat is not None and lon is not None:
        return 0.6 if is_estimated else 0.8
    return 0.2


def parse_sidecar_json(json_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parse a single JSON sidecar file and extract location data.
    
    Returns:
        Dictionary with standardized location data or None if no valid data
    """
    # Extract timestamp
    timestamp = parse_timestamp(json_data)
    if not timestamp:
        return None
    
    # Extract location
    lat, lon, accuracy, is_estimated = parse_location(json_data)
    
    # Skip if no location data
    if lat is None or lon is None:
        return None
    
    # Calculate confidence
    confidence = calculate_confidence(lat, lon, is_estimated)
    
    return {
        "timestamp_utc": timestamp.isoformat(),
        "latitude": lat,
        "longitude": lon,
        "accuracy_m": accuracy,
        "source": "google_photos",
        "provenance": "takeout-sidecar",
        "confidence": confidence,
        "user_id": user_id,
    }


def parse_takeout_zip_to_df(zip_path: str, user_id: Optional[str] = None) -> pd.DataFrame:
    """
    Read a Google Photos Takeout ZIP (or re-zipped folder), parse sidecar JSONs,
    and return a DataFrame in the project's standardized location schema.
    
    Parameters
    ----------
    zip_path : str
        Path to the ZIP file
    user_id : str, optional
        User identifier to attach to records
        
    Returns
    -------
    pd.DataFrame
        DataFrame with standardized location columns
    """
    rows = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            # Get list of files in the ZIP
            file_list = zip_file.namelist()
            
            # Filter for JSON sidecar files
            json_files = [f for f in file_list if is_json_sidecar(f)]
            
            print(f"Found {len(json_files)} JSON sidecar files to process...")
            
            for json_file in json_files:
                try:
                    # Read and parse JSON
                    with zip_file.open(json_file) as f:
                        json_data = json.load(f)
                    
                    # Extract location data
                    row_data = parse_sidecar_json(json_data, user_id)
                    if row_data:
                        rows.append(row_data)
                        
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Warning: Failed to parse {json_file}: {e}")
                    continue
                except Exception as e:
                    print(f"Warning: Unexpected error processing {json_file}: {e}")
                    continue
    
    except zipfile.BadZipFile:
        raise ValueError(f"Invalid ZIP file: {zip_path}")
    except FileNotFoundError:
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")
    
    # Create DataFrame with standardized columns
    if not rows:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=STANDARD_LOCATION_COLUMNS)
    
    df = pd.DataFrame(rows)
    
    # Ensure all required columns are present
    for col in STANDARD_LOCATION_COLUMNS:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns to match schema
    df = df[STANDARD_LOCATION_COLUMNS]
    
    # Convert timestamp to datetime
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], utc=True)
    
    # Sort by timestamp
    df = df.sort_values('timestamp_utc').reset_index(drop=True)
    
    print(f"Successfully extracted {len(df)} location records")
    return df


def save_df(df: pd.DataFrame, out_path: str) -> None:
    """
    Save the standardized DataFrame to CSV or Parquet based on extension.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to save
    out_path : str
        Output file path (.csv or .parquet)
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    if out_path.suffix.lower() == '.parquet':
        df.to_parquet(out_path, index=False)
    elif out_path.suffix.lower() == '.csv':
        df.to_csv(out_path, index=False)
    else:
        raise ValueError(f"Unsupported file format: {out_path.suffix}. Use .csv or .parquet")


def main():
    """CLI for Google Photos Takeout extraction."""
    parser = argparse.ArgumentParser(
        description="Extract location data from Google Photos Takeout ZIP files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--zip",
        required=True,
        help="Path to Google Photos Takeout ZIP file"
    )
    parser.add_argument(
        "--out",
        help="Output file path (.csv or .parquet). If not provided, prints preview to stdout"
    )
    parser.add_argument(
        "--user",
        help="User ID to attach to records"
    )
    
    args = parser.parse_args()
    
    try:
        # Parse the ZIP file
        df = parse_takeout_zip_to_df(args.zip, args.user)
        
        if args.out:
            # Save to file
            save_df(df, args.out)
            print(f"Saved {len(df)} records to {args.out}")
        else:
            # Print preview
            print(f"\nExtracted {len(df)} location records:")
            print("\nFirst 5 records:")
            print(df.head().to_string(index=False))
            
            if len(df) > 5:
                print(f"\n... and {len(df) - 5} more records")
            
            print(f"\nSchema summary:")
            print(f"Columns: {list(df.columns)}")
            print(f"Data types:")
            print(df.dtypes.to_string())
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
