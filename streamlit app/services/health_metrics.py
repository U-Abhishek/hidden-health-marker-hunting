"""
Health Metrics Calculation Service
---------------------------------
Implements health-focused environmental analysis based on WHO guidelines
and health impact scoring algorithms from frontend_algo.md
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np


# =========================
# HEALTH GUIDELINES & CONSTANTS
# =========================

# WHO Air Quality Guidelines
WHO_PM25_ANNUAL = 5.0      # µg/m³
WHO_PM25_24H = 15.0        # µg/m³
US_PM25_24H_AQI100 = 35.0  # µg/m³ (reference for "unhealthy for sensitive")

O3_8H_HEALTH = 50.0        # ppb ~ WHO peak-season target-level avg
O3_8H_AQI100 = 70.0        # ppb (US NAAQS)

NO2_ANNUAL_HEALTH = 10.0   # µg/m³ WHO
SO2_24H_HEALTH = 40.0      # µg/m³ WHO
CO_24H_HEALTH_PPM = 3.5    # ppm (≈4 mg/m³)

# UV Protection Guidelines
UV_PROTECT_THRESHOLD = 3.0  # UV index at/above -> protection advised
UV_VERY_HIGH = 8.0

# Thermal Comfort Guidelines
TEMP_COMFORT_MIN_C = 18.0
TEMP_COMFORT_MAX_C = 24.0
HEAT_STRESS_CUTOFF_C = 32.0
COLD_STRESS_CUTOFF_C = 0.0

# Humidity & Dew Point Comfort
RH_LOW = 30   # %
RH_HIGH = 60  # %
DEWPOINT_OPPRESSIVE_F = 70  # ~21.1°C

# Wind Hazard Thresholds
WIND_DUSTY_KMH = 30      # ~18 mph – can loft dust given dry soils
WIND_HAZARD_KMH = 60     # ~37 mph – tree limbs, debris risks

# Precipitation Thresholds
HEAVY_RAIN_MM_DAY = 50   # flood risk heuristic

# Composite Weights (sum to 1.0)
COMPOSITE_WEIGHTS = {
    'pm25': 0.30,
    'o3': 0.15,
    'no2': 0.07,
    'so2': 0.03,
    'co': 0.03,
    'uv': 0.20,
    'temp': 0.12,
    'humidity_dew': 0.06,
    'wind': 0.02,
    'precip': 0.02
}


def calculate_health_metrics(environmental_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate comprehensive health metrics for environmental data.
    
    Parameters
    ----------
    environmental_data : List[Dict[str, Any]]
        List of environmental data entries with lat, lon, date_str, and environmental_data
    
    Returns
    -------
    List[Dict[str, Any]]
        Enhanced data with health metrics and scores
    """
    enhanced_data = []
    
    for entry in environmental_data:
        if 'environmental_data' not in entry:
            enhanced_data.append(entry)
            continue
            
        env = entry['environmental_data']
        health_metrics = calculate_entry_health_metrics(env)
        
        # Create enhanced entry
        enhanced_entry = entry.copy()
        enhanced_entry['health_metrics'] = health_metrics
        enhanced_data.append(enhanced_entry)
    
    return enhanced_data


def calculate_entry_health_metrics(env_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate health metrics for a single environmental data entry.
    
    Parameters
    ----------
    env_data : Dict[str, Any]
        Environmental data from API response
    
    Returns
    -------
    Dict[str, Any]
        Health metrics including scores, risk levels, and insights
    """
    metrics = {
        'scores': {},
        'risk_levels': {},
        'exposure_hours': {},
        'insights': [],
        'composite_score': 0,
        'confidence': 0.0
    }
    
    # Extract pollutant data
    pollutants = extract_pollutant_data(env_data)
    
    # Calculate individual health scores
    metrics['scores']['pm25'] = score_pm25(pollutants.get('pm25_ugm3'))
    metrics['scores']['o3'] = score_o3(pollutants.get('o3_ppb'))
    metrics['scores']['no2'] = score_no2(pollutants.get('no2_ugm3'))
    metrics['scores']['so2'] = score_so2(pollutants.get('so2_ugm3'))
    metrics['scores']['co'] = score_co(pollutants.get('co_ppm'))
    
    # Calculate environmental scores
    metrics['scores']['uv'] = score_uv(env_data.get('uv_index'), env_data.get('uv_index_max'))
    metrics['scores']['temp'] = score_temperature(env_data.get('temperature'))
    metrics['scores']['humidity_dew'] = score_humidity_dew(
        env_data.get('humidity'), 
        env_data.get('dewpoint_c')
    )
    metrics['scores']['wind'] = score_wind(env_data.get('wind_speed'))
    metrics['scores']['precip'] = score_precipitation(env_data.get('precipitation'))
    
    # Calculate composite score
    metrics['composite_score'] = calculate_composite_score(metrics['scores'])
    
    # Calculate confidence based on data availability
    metrics['confidence'] = calculate_confidence(env_data)
    
    # Determine risk levels
    metrics['risk_levels'] = categorize_risk_levels(metrics['scores'])
    
    # Calculate exposure metrics
    metrics['exposure_hours'] = calculate_exposure_hours(env_data)
    
    # Generate insights
    metrics['insights'] = generate_health_insights(metrics['scores'], pollutants, env_data)
    
    return metrics


def extract_pollutant_data(env_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract pollutant concentrations from environmental data.
    
    Parameters
    ----------
    env_data : Dict[str, Any]
        Environmental data from API response
    
    Returns
    -------
    Dict[str, float]
        Pollutant concentrations in standard units
    """
    pollutants = {}
    
    # Extract from Google Air Quality data if available
    google_aq = env_data.get('google_air_quality', {})
    if 'current' in google_aq and 'pollutants' in google_aq['current']:
        for pollutant in google_aq['current']['pollutants']:
            if 'concentration' in pollutant and 'microgramsPerCubicMeter' in pollutant['concentration']:
                name = pollutant.get('code', '').lower()
                value = pollutant['concentration']['microgramsPerCubicMeter']
                
                if name == 'pm25':
                    pollutants['pm25_ugm3'] = value
                elif name == 'pm10':
                    pollutants['pm10_ugm3'] = value
                elif name == 'o3':
                    pollutants['o3_ppb'] = value * 1000  # Convert to ppb
                elif name == 'no2':
                    pollutants['no2_ugm3'] = value
                elif name == 'so2':
                    pollutants['so2_ugm3'] = value
                elif name == 'co':
                    pollutants['co_ppm'] = value / 1000  # Convert to ppm
    
    return pollutants


def score_pm25(pm25_ugm3: Optional[float]) -> int:
    """
    Calculate PM2.5 health score (0-100, higher = worse).
    
    Parameters
    ----------
    pm25_ugm3 : Optional[float]
        PM2.5 concentration in µg/m³
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if pm25_ugm3 is None:
        return 0
    
    # Use 24-hour guideline for scoring
    rel = pm25_ugm3 / WHO_PM25_24H
    raw_score = min(100, rel * 100)
    
    # Apply penalty for very high concentrations
    if pm25_ugm3 > US_PM25_24H_AQI100:
        raw_score = min(100, raw_score * 1.2)
    
    return int(raw_score)


def score_o3(o3_ppb: Optional[float]) -> int:
    """
    Calculate Ozone health score (0-100, higher = worse).
    
    Parameters
    ----------
    o3_ppb : Optional[float]
        O3 concentration in ppb
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if o3_ppb is None:
        return 0
    
    rel = o3_ppb / O3_8H_AQI100
    raw_score = min(100, rel * 100)
    
    # Shape the curve for better health impact representation
    if raw_score > 50:
        raw_score = min(100, 50 + (raw_score - 50) * 1.5)
    
    return int(raw_score)


def score_no2(no2_ugm3: Optional[float]) -> int:
    """
    Calculate NO2 health score (0-100, higher = worse).
    
    Parameters
    ----------
    no2_ugm3 : Optional[float]
        NO2 concentration in µg/m³
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if no2_ugm3 is None:
        return 0
    
    rel = no2_ugm3 / NO2_ANNUAL_HEALTH
    return int(min(100, rel * 100))


def score_so2(so2_ugm3: Optional[float]) -> int:
    """
    Calculate SO2 health score (0-100, higher = worse).
    
    Parameters
    ----------
    so2_ugm3 : Optional[float]
        SO2 concentration in µg/m³
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if so2_ugm3 is None:
        return 0
    
    rel = so2_ugm3 / SO2_24H_HEALTH
    return int(min(100, rel * 100))


def score_co(co_ppm: Optional[float]) -> int:
    """
    Calculate CO health score (0-100, higher = worse).
    
    Parameters
    ----------
    co_ppm : Optional[float]
        CO concentration in ppm
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if co_ppm is None:
        return 0
    
    rel = co_ppm / CO_24H_HEALTH_PPM
    return int(min(100, rel * 100))


def score_uv(uv_index: Optional[float], uv_max: Optional[float] = None) -> int:
    """
    Calculate UV exposure health score (0-100, higher = worse).
    
    Parameters
    ----------
    uv_index : Optional[float]
        Current UV index
    uv_max : Optional[float]
        Daily maximum UV index
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if uv_index is None:
        return 0
    
    # Base score on UV index
    if uv_index >= UV_VERY_HIGH:
        base_score = 80
    elif uv_index >= UV_PROTECT_THRESHOLD:
        base_score = min(60, (uv_index - UV_PROTECT_THRESHOLD) * 12)
    else:
        base_score = 0
    
    # Add bonus for very high UV days
    if uv_max and uv_max >= UV_VERY_HIGH:
        base_score = min(100, base_score + 20)
    
    return int(base_score)


def score_temperature(temp_c: Optional[float]) -> int:
    """
    Calculate temperature health score (0-100, higher = worse).
    
    Parameters
    ----------
    temp_c : Optional[float]
        Temperature in Celsius
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if temp_c is None:
        return 0
    
    score = 0
    
    # Heat stress
    if temp_c >= HEAT_STRESS_CUTOFF_C:
        score = min(100, (temp_c - HEAT_STRESS_CUTOFF_C) * 10)
    elif temp_c > TEMP_COMFORT_MAX_C:
        score = min(50, (temp_c - TEMP_COMFORT_MAX_C) * 5)
    
    # Cold stress
    elif temp_c <= COLD_STRESS_CUTOFF_C:
        score = min(100, (COLD_STRESS_CUTOFF_C - temp_c) * 8)
    elif temp_c < TEMP_COMFORT_MIN_C:
        score = min(50, (TEMP_COMFORT_MIN_C - temp_c) * 4)
    
    return int(score)


def score_humidity_dew(humidity: Optional[float], dewpoint_c: Optional[float] = None) -> int:
    """
    Calculate humidity and dew point health score (0-100, higher = worse).
    
    Parameters
    ----------
    humidity : Optional[float]
        Relative humidity in %
    dewpoint_c : Optional[float]
        Dew point in Celsius
    
    Returns
    -------
    int
        Health score (0-100)
    """
    score = 0
    
    if humidity is not None:
        if humidity < RH_LOW:
            score += (RH_LOW - humidity) * 2
        elif humidity > RH_HIGH:
            score += (humidity - RH_HIGH) * 2
    
    if dewpoint_c is not None:
        dewpoint_f = dewpoint_c * 9/5 + 32
        if dewpoint_f >= DEWPOINT_OPPRESSIVE_F:
            score += (dewpoint_f - DEWPOINT_OPPRESSIVE_F) * 3
    
    return int(min(100, score))


def score_wind(wind_speed: Optional[float]) -> int:
    """
    Calculate wind health score (0-100, higher = worse).
    
    Parameters
    ----------
    wind_speed : Optional[float]
        Wind speed in m/s (converted to km/h internally)
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if wind_speed is None:
        return 0
    
    wind_kmh = wind_speed * 3.6  # Convert m/s to km/h
    
    if wind_kmh >= WIND_HAZARD_KMH:
        return min(100, (wind_kmh - WIND_HAZARD_KMH) * 5)
    elif wind_kmh >= WIND_DUSTY_KMH:
        return min(50, (wind_kmh - WIND_DUSTY_KMH) * 2)
    
    return 0


def score_precipitation(precip_mm: Optional[float]) -> int:
    """
    Calculate precipitation health score (0-100, higher = worse).
    
    Parameters
    ----------
    precip_mm : Optional[float]
        Precipitation in mm
    
    Returns
    -------
    int
        Health score (0-100)
    """
    if precip_mm is None:
        return 0
    
    if precip_mm >= HEAVY_RAIN_MM_DAY:
        return min(100, (precip_mm - HEAVY_RAIN_MM_DAY) * 2)
    
    return 0


def calculate_composite_score(scores: Dict[str, int]) -> int:
    """
    Calculate weighted composite health score.
    
    Parameters
    ----------
    scores : Dict[str, int]
        Individual health scores
    
    Returns
    -------
    int
        Composite health score (0-100)
    """
    weighted_sum = 0
    total_weight = 0
    
    for factor, weight in COMPOSITE_WEIGHTS.items():
        if factor in scores:
            weighted_sum += scores[factor] * weight
            total_weight += weight
    
    if total_weight == 0:
        return 0
    
    base_score = weighted_sum / total_weight
    
    # Severity kicker: if any subscore >= 80, add penalty
    max_subscore = max(scores.values()) if scores else 0
    if max_subscore >= 80:
        base_score = min(100, base_score + 0.2 * (max_subscore - 80))
    
    return int(base_score)


def calculate_confidence(env_data: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on data availability.
    
    Parameters
    ----------
    env_data : Dict[str, Any]
        Environmental data
    
    Returns
    -------
    float
        Confidence score (0-1)
    """
    factors = []
    
    # Check data availability
    if env_data.get('uv_index') is not None:
        factors.append(1.0)
    if env_data.get('temperature') is not None:
        factors.append(1.0)
    if env_data.get('humidity') is not None:
        factors.append(1.0)
    if env_data.get('air_quality_index') is not None:
        factors.append(1.0)
    if env_data.get('wind_speed') is not None:
        factors.append(1.0)
    if env_data.get('precipitation') is not None:
        factors.append(1.0)
    
    # Check for errors
    errors = env_data.get('errors', [])
    if errors:
        factors = [f * 0.7 for f in factors]  # Reduce confidence if errors present
    
    return sum(factors) / 6.0 if factors else 0.0


def categorize_risk_levels(scores: Dict[str, int]) -> Dict[str, str]:
    """
    Categorize health scores into risk levels.
    
    Parameters
    ----------
    scores : Dict[str, int]
        Health scores
    
    Returns
    -------
    Dict[str, str]
        Risk level categories
    """
    risk_levels = {}
    
    for factor, score in scores.items():
        if score >= 80:
            risk_levels[factor] = "Very High Risk"
        elif score >= 60:
            risk_levels[factor] = "High Risk"
        elif score >= 40:
            risk_levels[factor] = "Moderate Risk"
        elif score >= 20:
            risk_levels[factor] = "Low Risk"
        else:
            risk_levels[factor] = "Minimal Risk"
    
    return risk_levels


def calculate_exposure_hours(env_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Calculate exposure hours for various risk factors.
    
    Parameters
    ----------
    env_data : Dict[str, Any]
        Environmental data
    
    Returns
    -------
    Dict[str, int]
        Exposure hours for different risk factors
    """
    exposure = {}
    
    # UV exposure hours (assuming 1 hour per data point)
    uv_index = env_data.get('uv_index', 0)
    if uv_index >= UV_PROTECT_THRESHOLD:
        exposure['uv_protection_needed'] = 1
    else:
        exposure['uv_protection_needed'] = 0
    
    # Heat exposure hours
    temp = env_data.get('temperature', 0)
    if temp >= HEAT_STRESS_CUTOFF_C:
        exposure['heat_stress'] = 1
    else:
        exposure['heat_stress'] = 0
    
    # Cold exposure hours
    if temp <= COLD_STRESS_CUTOFF_C:
        exposure['cold_stress'] = 1
    else:
        exposure['cold_stress'] = 0
    
    return exposure


def generate_health_insights(scores: Dict[str, int], pollutants: Dict[str, float], env_data: Dict[str, Any]) -> List[str]:
    """
    Generate health insights based on scores and environmental data.
    
    Parameters
    ----------
    scores : Dict[str, int]
        Health scores
    pollutants : Dict[str, float]
        Pollutant concentrations
    env_data : Dict[str, Any]
        Environmental data
    
    Returns
    -------
    List[str]
        Health insights and recommendations
    """
    insights = []
    
    # PM2.5 insights
    if scores.get('pm25', 0) >= 60:
        pm25_val = pollutants.get('pm25_ugm3', 0)
        insights.append(f"PM2.5 levels elevated ({pm25_val:.1f} µg/m³). Consider reducing outdoor activities and using air purifiers indoors.")
    
    # Ozone insights
    if scores.get('o3', 0) >= 60:
        o3_val = pollutants.get('o3_ppb', 0)
        insights.append(f"Ozone levels high ({o3_val:.1f} ppb). Afternoon outdoor activities may worsen breathing; morning exercise is safer.")
    
    # UV insights
    if scores.get('uv', 0) >= 60:
        uv_val = env_data.get('uv_index', 0)
        insights.append(f"High UV exposure (UV Index {uv_val:.1f}). Use sun protection, seek shade, and avoid midday sun exposure.")
    
    # Temperature insights
    if scores.get('temp', 0) >= 60:
        temp_val = env_data.get('temperature', 0)
        if temp_val > TEMP_COMFORT_MAX_C:
            insights.append(f"High temperature ({temp_val:.1f}°C). Stay hydrated, seek air conditioning, and avoid strenuous outdoor activities.")
        else:
            insights.append(f"Low temperature ({temp_val:.1f}°C). Dress warmly and be aware of cold stress risks.")
    
    # Humidity insights
    if scores.get('humidity_dew', 0) >= 60:
        humidity_val = env_data.get('humidity', 0)
        insights.append(f"Humidity extremes detected ({humidity_val:.1f}%). High humidity impairs cooling; low humidity can cause respiratory irritation.")
    
    # Overall composite score insight
    composite = scores.get('composite_score', 0)
    if composite >= 80:
        insights.append("Overall environmental health risk is very high. Consider limiting outdoor exposure and taking protective measures.")
    elif composite >= 60:
        insights.append("Moderate to high environmental health risk. Be cautious with outdoor activities and monitor symptoms.")
    elif composite >= 40:
        insights.append("Some environmental health concerns present. Consider protective measures for sensitive individuals.")
    else:
        insights.append("Environmental conditions are generally favorable for health.")
    
    return insights


def aggregate_health_metrics_by_period(health_data: List[Dict[str, Any]], period: str = 'daily') -> List[Dict[str, Any]]:
    """
    Aggregate health metrics by time period.
    
    Parameters
    ----------
    health_data : List[Dict[str, Any]]
        Health data with timestamps
    period : str
        Aggregation period ('daily', 'weekly', 'monthly')
    
    Returns
    -------
    List[Dict[str, Any]]
        Aggregated health metrics
    """
    if not health_data:
        return []
    
    # Convert to DataFrame for easier aggregation
    df_data = []
    for entry in health_data:
        if 'health_metrics' in entry:
            row = {
                'date_str': entry['date_str'],
                'lat': entry['lat'],
                'lon': entry['lon']
            }
            row.update(entry['health_metrics']['scores'])
            row['composite_score'] = entry['health_metrics']['composite_score']
            row['confidence'] = entry['health_metrics']['confidence']
            df_data.append(row)
    
    if not df_data:
        return []
    
    df = pd.DataFrame(df_data)
    df['date'] = pd.to_datetime(df['date_str'])
    
    # Group by period
    if period == 'daily':
        grouped = df.groupby(df['date'].dt.date)
    elif period == 'weekly':
        grouped = df.groupby(df['date'].dt.to_period('W'))
    elif period == 'monthly':
        grouped = df.groupby(df['date'].dt.to_period('M'))
    else:
        return df_data
    
    # Aggregate metrics
    aggregated = []
    for period_key, group in grouped:
        period_data = {
            'period': str(period_key),
            'period_type': period,
            'count': len(group),
            'avg_composite_score': group['composite_score'].mean(),
            'max_composite_score': group['composite_score'].max(),
            'avg_confidence': group['confidence'].mean(),
            'scores': {
                'pm25': group['pm25'].mean() if 'pm25' in group.columns else 0,
                'o3': group['o3'].mean() if 'o3' in group.columns else 0,
                'uv': group['uv'].mean() if 'uv' in group.columns else 0,
                'temp': group['temp'].mean() if 'temp' in group.columns else 0,
                'humidity_dew': group['humidity_dew'].mean() if 'humidity_dew' in group.columns else 0,
                'wind': group['wind'].mean() if 'wind' in group.columns else 0,
                'precip': group['precip'].mean() if 'precip' in group.columns else 0
            }
        }
        aggregated.append(period_data)
    
    return aggregated


# Export functions
__all__ = [
    "calculate_health_metrics",
    "calculate_entry_health_metrics",
    "aggregate_health_metrics_by_period",
    "COMPOSITE_WEIGHTS",
    "WHO_PM25_ANNUAL",
    "WHO_PM25_24H",
    "UV_PROTECT_THRESHOLD"
]
