"""
Location Data Ingestion Helpers
-------------------------------
Helper functions for standardizing location data from various sources.

This module provides utilities to convert raw location data from different sources
into the standardized format expected by the metrics extraction pipeline.
"""

from __future__ import annotations

import pandas as pd
from typing import Any, Dict, List, Optional, Union

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

# Required columns for environmental enrichment
REQUIRED_COLUMNS = ["timestamp_utc", "latitude", "longitude"]

# Optional columns with default values
OPTIONAL_DEFAULTS = {
    "accuracy_m": None,
    "source": "unknown",
    "provenance": "unknown",
    "confidence": 0.5,
    "user_id": None,
}


def to_standardized_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Take raw dicts from parsed location data and coerce to the exact schema.
    
    This function ensures:
    - Enforces column order and dtypes
    - Fills defaults for missing optional fields
    - Validates required fields are present
    - Handles type conversions safely
    
    Parameters
    ----------
    rows : List[Dict[str, Any]]
        List of dictionaries containing location data
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame with proper schema
        
    Raises
    ------
    ValueError
        If required columns are missing or data cannot be converted
    """
    if not rows:
        return pd.DataFrame(columns=STANDARD_LOCATION_COLUMNS)
    
    # Create DataFrame from raw data
    df = pd.DataFrame(rows)
    
    # Ensure all required columns are present
    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")
    
    # Add missing optional columns with defaults
    for col, default_value in OPTIONAL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default_value
    
    # Ensure all standard columns are present
    for col in STANDARD_LOCATION_COLUMNS:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns to match schema
    df = df[STANDARD_LOCATION_COLUMNS]
    
    # Validate and convert data types
    df = _validate_and_convert_types(df)
    
    # Sort by timestamp
    df = df.sort_values('timestamp_utc').reset_index(drop=True)
    
    return df


def _validate_and_convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and convert data types for the standardized schema.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to validate and convert
        
    Returns
    -------
    pd.DataFrame
        DataFrame with proper data types
        
    Raises
    ------
    ValueError
        If data cannot be converted to expected types
    """
    # Convert timestamp_utc to datetime if it's a string
    if df['timestamp_utc'].dtype == 'object':
        try:
            df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], utc=True)
        except Exception as e:
            raise ValueError(f"Failed to convert timestamp_utc to datetime: {e}")
    
    # Convert latitude and longitude to float
    for col in ['latitude', 'longitude']:
        if df[col].dtype == 'object':
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception as e:
                raise ValueError(f"Failed to convert {col} to numeric: {e}")
        
        # Validate coordinate ranges
        if col == 'latitude':
            invalid = (df[col] < -90) | (df[col] > 90)
        else:  # longitude
            invalid = (df[col] < -180) | (df[col] > 180)
        
        if invalid.any():
            raise ValueError(f"Invalid {col} values outside valid range")
    
    # Convert accuracy_m to float
    if df['accuracy_m'].dtype == 'object':
        df['accuracy_m'] = pd.to_numeric(df['accuracy_m'], errors='coerce')
    
    # Convert confidence to float and validate range
    if df['confidence'].dtype == 'object':
        df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    
    invalid_confidence = (df['confidence'] < 0) | (df['confidence'] > 1)
    if invalid_confidence.any():
        raise ValueError("Confidence values must be between 0.0 and 1.0")
    
    # Ensure string columns are strings
    for col in ['source', 'provenance', 'user_id']:
        df[col] = df[col].astype(str)
        # Replace 'None' string with actual None
        df[col] = df[col].replace('None', None)
    
    return df


def validate_location_data(df: pd.DataFrame) -> List[str]:
    """
    Validate location data and return list of issues found.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to validate
        
    Returns
    -------
    List[str]
        List of validation issues (empty if all valid)
    """
    issues = []
    
    # Check required columns
    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        issues.append(f"Missing required columns: {missing_required}")
    
    # Check for empty DataFrame
    if len(df) == 0:
        issues.append("DataFrame is empty")
        return issues
    
    # Check for missing values in required columns
    for col in REQUIRED_COLUMNS:
        if col in df.columns and df[col].isna().any():
            missing_count = df[col].isna().sum()
            issues.append(f"Column '{col}' has {missing_count} missing values")
    
    # Check coordinate ranges
    if 'latitude' in df.columns:
        invalid_lat = (df['latitude'] < -90) | (df['latitude'] > 90)
        if invalid_lat.any():
            issues.append(f"Invalid latitude values: {df[invalid_lat]['latitude'].tolist()}")
    
    if 'longitude' in df.columns:
        invalid_lon = (df['longitude'] < -180) | (df['longitude'] > 180)
        if invalid_lon.any():
            issues.append(f"Invalid longitude values: {df[invalid_lon]['longitude'].tolist()}")
    
    # Check confidence range
    if 'confidence' in df.columns:
        invalid_conf = (df['confidence'] < 0) | (df['confidence'] > 1)
        if invalid_conf.any():
            issues.append(f"Invalid confidence values: {df[invalid_conf]['confidence'].tolist()}")
    
    return issues


def get_schema_info() -> Dict[str, Any]:
    """
    Get information about the standardized location schema.
    
    Returns
    -------
    Dict[str, Any]
        Schema information including column descriptions and requirements
    """
    return {
        "columns": STANDARD_LOCATION_COLUMNS,
        "required_columns": REQUIRED_COLUMNS,
        "optional_columns": list(OPTIONAL_DEFAULTS.keys()),
        "column_descriptions": {
            "timestamp_utc": "ISO 8601 UTC timestamp",
            "latitude": "Latitude in decimal degrees (-90 to 90)",
            "longitude": "Longitude in decimal degrees (-180 to 180)",
            "accuracy_m": "GPS accuracy in meters (optional)",
            "source": "Data source identifier (e.g., 'google_photos', 'apple_photos')",
            "provenance": "Data provenance information (e.g., 'takeout-sidecar')",
            "confidence": "Confidence score (0.0-1.0)",
            "user_id": "User identifier (optional)",
        },
        "default_values": OPTIONAL_DEFAULTS,
    }
