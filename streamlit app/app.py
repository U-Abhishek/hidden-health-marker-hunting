"""
Hidden Health Marker Hunting - Streamlit App
============================================
A Streamlit application for processing Google Timeline and Calendar data
to extract location-based health markers and environmental exposure patterns.
"""

import streamlit as st
import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Import our data processing services
from services.timeline_extraction import process_timeline_file
from services.calender_extraction import oprate_calendar_data
from services.environmental_extraction import (
    process_timeline_with_environmental_data,
    process_calendar_with_environmental_data,
    save_enriched_data,
    load_enriched_data
)
from services.health_metrics import (
    calculate_health_metrics,
    aggregate_health_metrics_by_period,
    COMPOSITE_WEIGHTS
)

# Page configuration
st.set_page_config(
    page_title="Hidden Health Marker Hunting",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'timeline_data' not in st.session_state:
    st.session_state.timeline_data = None
if 'calendar_data' not in st.session_state:
    st.session_state.calendar_data = None
if 'extracted_timeline' not in st.session_state:
    st.session_state.extracted_timeline = None
if 'extracted_calendar' not in st.session_state:
    st.session_state.extracted_calendar = None
if 'enriched_timeline' not in st.session_state:
    st.session_state.enriched_timeline = None
if 'enriched_calendar' not in st.session_state:
    st.session_state.enriched_calendar = None
if 'google_api_key' not in st.session_state:
    st.session_state.google_api_key = None
if 'openuv_api_key' not in st.session_state:
    st.session_state.openuv_api_key = None
if 'health_metrics_timeline' not in st.session_state:
    st.session_state.health_metrics_timeline = None
if 'health_metrics_calendar' not in st.session_state:
    st.session_state.health_metrics_calendar = None

def create_data_directory():
    """Ensure data directory exists"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir

def save_uploaded_file(uploaded_file, file_type):
    """Save uploaded file to data directory"""
    data_dir = create_data_directory()
    
    if file_type == "timeline":
        file_path = data_dir / "timeline_data.json"
    elif file_type == "calendar":
        file_path = data_dir / "calendar_data.ics"
    else:
        return None
    
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")
        return None

def load_extracted_data():
    """Load previously extracted data if available"""
    extracted_dir = Path("data/extracted_data")
    extracted_dir.mkdir(exist_ok=True)
    
    timeline_file = extracted_dir / "timeline_extracted.json"
    calendar_file = extracted_dir / "calendar_extracted.json"
    
    timeline_data = None
    calendar_data = None
    
    if timeline_file.exists():
        try:
            with open(timeline_file, 'r', encoding='utf-8') as f:
                timeline_data = json.load(f)
        except Exception as e:
            st.error(f"Error loading timeline data: {str(e)}")
    
    if calendar_file.exists():
        try:
            with open(calendar_file, 'r', encoding='utf-8') as f:
                calendar_data = json.load(f)
        except Exception as e:
            st.error(f"Error loading calendar data: {str(e)}")
    
    return timeline_data, calendar_data


def load_enriched_data():
    """Load previously enriched data if available"""
    extracted_dir = Path("data/extracted_data")
    extracted_dir.mkdir(exist_ok=True)
    
    timeline_file = extracted_dir / "timeline_enriched.json"
    calendar_file = extracted_dir / "calendar_enriched.json"
    
    timeline_data = None
    calendar_data = None
    
    if timeline_file.exists():
        try:
            timeline_data = load_enriched_data(str(timeline_file))
        except Exception as e:
            st.error(f"Error loading enriched timeline data: {str(e)}")
    
    if calendar_file.exists():
        try:
            calendar_data = load_enriched_data(str(calendar_file))
        except Exception as e:
            st.error(f"Error loading enriched calendar data: {str(e)}")
    
    return timeline_data, calendar_data


def process_timeline_with_environmental(timeline_file_path, max_requests=20):
    """Process timeline data with environmental information"""
    try:
        enriched_data = process_timeline_with_environmental_data(
            timeline_file_path,
            google_api_key=st.session_state.google_api_key,
            openuv_api_key=st.session_state.openuv_api_key,
            max_requests=max_requests
        )
        
        if enriched_data:
            # Save enriched data
            extracted_dir = Path("data/extracted_data")
            extracted_dir.mkdir(exist_ok=True)
            output_file = extracted_dir / "timeline_enriched.json"
            save_enriched_data(enriched_data, str(output_file), "timeline")
            
            return enriched_data
        else:
            return None
    except Exception as e:
        st.error(f"Error processing timeline with environmental data: {str(e)}")
        return None


def process_calendar_with_environmental(calendar_file_path, max_requests=20):
    """Process calendar data with environmental information"""
    try:
        enriched_data = process_calendar_with_environmental_data(
            calendar_file_path,
            google_api_key=st.session_state.google_api_key,
            openuv_api_key=st.session_state.openuv_api_key,
            max_requests=max_requests
        )
        
        if enriched_data:
            # Save enriched data
            extracted_dir = Path("data/extracted_data")
            extracted_dir.mkdir(exist_ok=True)
            output_file = extracted_dir / "calendar_enriched.json"
            save_enriched_data(enriched_data, str(output_file), "calendar")
            
            return enriched_data
        else:
            return None
    except Exception as e:
        st.error(f"Error processing calendar with environmental data: {str(e)}")
        return None


def process_health_metrics(data, data_type="timeline"):
    """Process environmental data to calculate health metrics"""
    try:
        health_data = calculate_health_metrics(data)
        
        if health_data:
            # Save health metrics data
            extracted_dir = Path("data/extracted_data")
            extracted_dir.mkdir(exist_ok=True)
            output_file = extracted_dir / f"{data_type}_health_metrics.json"
            save_enriched_data(health_data, str(output_file), f"{data_type}_health")
            
            return health_data
        else:
            return None
    except Exception as e:
        st.error(f"Error processing health metrics: {str(e)}")
        return None

def process_timeline_data(file_path):
    """Process timeline data using the service"""
    try:
        daily_location_data = process_timeline_file(str(file_path))
        
        if daily_location_data:
            # Save extracted data
            extracted_dir = Path("data/extracted_data")
            extracted_dir.mkdir(exist_ok=True)
            output_file = extracted_dir / "timeline_extracted.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(daily_location_data, f, indent=2, ensure_ascii=False)
            
            return daily_location_data
        else:
            return None
    except Exception as e:
        st.error(f"Error processing timeline data: {str(e)}")
        return None

def process_calendar_data():
    """Process calendar data using the service"""
    try:
        # Look for calendar JSON files in the data directory
        data_dir = Path("data")
        calendar_files = []
        
        for file in data_dir.glob("*.json"):
            if 'calendar' in file.name.lower():
                calendar_files.append(str(file))
        
        if not calendar_files:
            st.error("No calendar JSON files found in data directory")
            return None
        
        all_extracted_data = []
        
        for calendar_file in calendar_files:
            try:
                event_data = oprate_calendar_data(calendar_file)
                if event_data:
                    all_extracted_data.extend(event_data)
                    st.info(f"Extracted {len(event_data)} events from {Path(calendar_file).name}")
            except Exception as e:
                st.warning(f"Error processing {Path(calendar_file).name}: {str(e)}")
                continue
        
        if all_extracted_data:
            # Save extracted data
            extracted_dir = Path("data/extracted_data")
            extracted_dir.mkdir(exist_ok=True)
            output_file = extracted_dir / "calendar_extracted.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_extracted_data, f, indent=2, ensure_ascii=False)
            
            return all_extracted_data
        else:
            return None
    except Exception as e:
        st.error(f"Error processing calendar data: {str(e)}")
        return None

def create_location_map(data, title):
    """Create a map visualization of location data"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    # Create the map
    fig = px.scatter_mapbox(
        df,
        lat='lat',
        lon='lon',
        hover_data=['date_str'],
        title=title,
        mapbox_style='open-street-map',
        zoom=2
    )
    
    fig.update_layout(
        height=600,
        margin={"r": 0, "t": 30, "l": 0, "b": 0}
    )
    
    return fig

def create_timeline_chart(data, title):
    """Create a timeline chart showing data over time"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date_str'])
    df = df.sort_values('date')
    
    # Count entries per date
    daily_counts = df.groupby('date').size().reset_index(name='count')
    
    fig = px.line(
        daily_counts,
        x='date',
        y='count',
        title=title,
        labels={'count': 'Number of Location Entries', 'date': 'Date'}
    )
    
    fig.update_layout(height=400)
    return fig


def create_environmental_metrics_chart(data, title):
    """Create charts for environmental metrics over time"""
    if not data:
        return None
    
    # Extract environmental data
    env_data = []
    for entry in data:
        if 'environmental_data' in entry:
            env_entry = entry['environmental_data'].copy()
            env_entry['date_str'] = entry['date_str']
            env_entry['lat'] = entry['lat']
            env_entry['lon'] = entry['lon']
            env_data.append(env_entry)
    
    if not env_data:
        return None
    
    df = pd.DataFrame(env_data)
    df['date'] = pd.to_datetime(df['date_str'])
    df = df.sort_values('date')
    
    # Create subplots for different metrics
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('UV Index', 'Air Quality Index', 'Temperature (°C)', 'Humidity (%)'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # UV Index
    if 'uv_index' in df.columns:
        uv_data = df.dropna(subset=['uv_index'])
        if not uv_data.empty:
            fig.add_trace(
                go.Scatter(x=uv_data['date'], y=uv_data['uv_index'], 
                          mode='lines+markers', name='UV Index', line=dict(color='orange')),
                row=1, col=1
            )
    
    # Air Quality Index
    if 'air_quality_index' in df.columns:
        aqi_data = df.dropna(subset=['air_quality_index'])
        if not aqi_data.empty:
            fig.add_trace(
                go.Scatter(x=aqi_data['date'], y=aqi_data['air_quality_index'], 
                          mode='lines+markers', name='AQI', line=dict(color='red')),
                row=1, col=2
            )
    
    # Temperature
    if 'temperature' in df.columns:
        temp_data = df.dropna(subset=['temperature'])
        if not temp_data.empty:
            fig.add_trace(
                go.Scatter(x=temp_data['date'], y=temp_data['temperature'], 
                          mode='lines+markers', name='Temperature', line=dict(color='blue')),
                row=2, col=1
            )
    
    # Humidity
    if 'humidity' in df.columns:
        humidity_data = df.dropna(subset=['humidity'])
        if not humidity_data.empty:
            fig.add_trace(
                go.Scatter(x=humidity_data['date'], y=humidity_data['humidity'], 
                          mode='lines+markers', name='Humidity', line=dict(color='green')),
                row=2, col=2
            )
    
    fig.update_layout(height=600, title_text=title, showlegend=False)
    return fig


def create_environmental_map(data, title):
    """Create a map with environmental data color-coded by UV index or air quality"""
    if not data:
        return None
    
    # Extract environmental data
    env_data = []
    for entry in data:
        if 'environmental_data' in entry:
            env_entry = entry['environmental_data'].copy()
            env_entry['lat'] = entry['lat']
            env_entry['lon'] = entry['lon']
            env_entry['date_str'] = entry['date_str']
            env_data.append(env_entry)
    
    if not env_data:
        return None
    
    df = pd.DataFrame(env_data)
    
    # Use UV index for coloring if available, otherwise use air quality
    color_column = None
    color_scale = None
    
    if 'uv_index' in df.columns and not df['uv_index'].isna().all():
        color_column = 'uv_index'
        color_scale = 'Oranges'
    elif 'air_quality_index' in df.columns and not df['air_quality_index'].isna().all():
        color_column = 'air_quality_index'
        color_scale = 'Reds'
    
    if color_column:
        fig = px.scatter_mapbox(
            df,
            lat='lat',
            lon='lon',
            color=color_column,
            hover_data=['date_str', 'uv_index', 'air_quality_index', 'temperature'],
            title=title,
            mapbox_style='open-street-map',
            zoom=2,
            color_continuous_scale=color_scale
        )
    else:
        fig = px.scatter_mapbox(
            df,
            lat='lat',
            lon='lon',
            hover_data=['date_str'],
            title=title,
            mapbox_style='open-street-map',
            zoom=2
        )
    
    fig.update_layout(
        height=600,
        margin={"r": 0, "t": 30, "l": 0, "b": 0}
    )
    
    return fig


def create_health_metrics_chart(data, title):
    """Create charts for health metrics over time"""
    if not data:
        return None
    
    # Extract health metrics data
    health_data = []
    for entry in data:
        if 'health_metrics' in entry:
            health_entry = entry['health_metrics'].copy()
            health_entry['date_str'] = entry['date_str']
            health_entry['lat'] = entry['lat']
            health_entry['lon'] = entry['lon']
            health_data.append(health_entry)
    
    if not health_data:
        return None
    
    df = pd.DataFrame(health_data)
    df['date'] = pd.to_datetime(df['date_str'])
    df = df.sort_values('date')
    
    # Create subplots for different health scores
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Composite Health Score', 'Air Quality Scores', 'UV & Temperature Scores', 
                       'Humidity & Wind Scores', 'Risk Level Distribution', 'Confidence Score'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Composite Health Score
    if 'composite_score' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['composite_score'], 
                      mode='lines+markers', name='Composite Score', line=dict(color='red', width=3)),
            row=1, col=1
        )
        # Add risk level thresholds
        fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.5, row=1, col=1)
        fig.add_hline(y=60, line_dash="dash", line_color="orange", opacity=0.5, row=1, col=1)
        fig.add_hline(y=40, line_dash="dash", line_color="yellow", opacity=0.5, row=1, col=1)
    
    # Air Quality Scores
    if 'scores' in df.columns:
        scores_df = pd.json_normalize(df['scores'])
        if 'pm25' in scores_df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=scores_df['pm25'], 
                          mode='lines+markers', name='PM2.5', line=dict(color='brown')),
                row=1, col=2
            )
        if 'o3' in scores_df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=scores_df['o3'], 
                          mode='lines+markers', name='O3', line=dict(color='purple')),
                row=1, col=2
            )
    
    # UV & Temperature Scores
    if 'scores' in df.columns:
        scores_df = pd.json_normalize(df['scores'])
        if 'uv' in scores_df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=scores_df['uv'], 
                          mode='lines+markers', name='UV', line=dict(color='orange')),
                row=2, col=1
            )
        if 'temp' in scores_df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=scores_df['temp'], 
                          mode='lines+markers', name='Temperature', line=dict(color='blue')),
                row=2, col=1
            )
    
    # Humidity & Wind Scores
    if 'scores' in df.columns:
        scores_df = pd.json_normalize(df['scores'])
        if 'humidity_dew' in scores_df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=scores_df['humidity_dew'], 
                          mode='lines+markers', name='Humidity', line=dict(color='green')),
                row=2, col=2
            )
        if 'wind' in scores_df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=scores_df['wind'], 
                          mode='lines+markers', name='Wind', line=dict(color='cyan')),
                row=2, col=2
            )
    
    # Risk Level Distribution (bar chart)
    if 'risk_levels' in df.columns:
        risk_df = pd.json_normalize(df['risk_levels'])
        risk_counts = {}
        for col in risk_df.columns:
            risk_counts[col] = risk_df[col].value_counts().to_dict()
        
        # Create stacked bar chart for risk levels
        risk_levels = ['Minimal Risk', 'Low Risk', 'Moderate Risk', 'High Risk', 'Very High Risk']
        colors = ['green', 'yellow', 'orange', 'red', 'darkred']
        
        for i, level in enumerate(risk_levels):
            counts = [risk_counts.get(col, {}).get(level, 0) for col in risk_df.columns]
            fig.add_trace(
                go.Bar(x=list(risk_df.columns), y=counts, name=level, 
                      marker_color=colors[i], showlegend=False),
                row=3, col=1
            )
    
    # Confidence Score
    if 'confidence' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['confidence'] * 100, 
                      mode='lines+markers', name='Confidence %', line=dict(color='gray')),
            row=3, col=2
        )
    
    fig.update_layout(height=900, title_text=title, showlegend=True)
    return fig


def create_health_insights_display(data):
    """Create a display of health insights and recommendations"""
    if not data:
        return None
    
    insights = []
    for entry in data:
        if 'health_metrics' in entry and 'insights' in entry['health_metrics']:
            for insight in entry['health_metrics']['insights']:
                insights.append({
                    'date': entry['date_str'],
                    'insight': insight,
                    'composite_score': entry['health_metrics'].get('composite_score', 0)
                })
    
    if not insights:
        return None
    
    # Sort by composite score (highest risk first)
    insights.sort(key=lambda x: x['composite_score'], reverse=True)
    
    return insights


def create_health_summary_cards(data):
    """Create summary cards for health metrics"""
    if not data:
        return None
    
    # Calculate summary statistics
    composite_scores = []
    risk_counts = {'Minimal Risk': 0, 'Low Risk': 0, 'Moderate Risk': 0, 'High Risk': 0, 'Very High Risk': 0}
    factor_scores = {'pm25': [], 'o3': [], 'uv': [], 'temp': [], 'humidity_dew': [], 'wind': [], 'precip': []}
    
    for entry in data:
        if 'health_metrics' in entry:
            composite_scores.append(entry['health_metrics'].get('composite_score', 0))
            
            # Count risk levels
            risk_levels = entry['health_metrics'].get('risk_levels', {})
            for factor, level in risk_levels.items():
                if level in risk_counts:
                    risk_counts[level] += 1
            
            # Collect factor scores
            scores = entry['health_metrics'].get('scores', {})
            for factor in factor_scores:
                if factor in scores:
                    factor_scores[factor].append(scores[factor])
    
    if not composite_scores:
        return None
    
    summary = {
        'avg_composite_score': sum(composite_scores) / len(composite_scores),
        'max_composite_score': max(composite_scores),
        'min_composite_score': min(composite_scores),
        'risk_distribution': risk_counts,
        'factor_averages': {factor: sum(scores) / len(scores) if scores else 0 
                           for factor, scores in factor_scores.items()},
        'total_entries': len(data)
    }
    
    return summary

# Main app
def main():
    # Header
    st.markdown('<h1 class="main-header">🔍 Hidden Health Marker Hunting</h1>', unsafe_allow_html=True)
    st.markdown("### Process Google Timeline and Calendar data to extract location-based health markers")
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", [
        "Data Upload",
        "Data Processing", 
        "Environmental Analysis",
        "Health Metrics",
        "Visualization",
        "Data Export"
    ])
    
    # API Keys section in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("API Configuration")
    st.session_state.google_api_key = st.sidebar.text_input(
        "Google Maps API Key (for air quality)", 
        value=st.session_state.google_api_key or "",
        type="password",
        help="Required for air quality data. Get from Google Cloud Console."
    )
    st.session_state.openuv_api_key = st.sidebar.text_input(
        "OpenUV API Key (optional)", 
        value=st.session_state.openuv_api_key or "",
        type="password",
        help="Optional for additional UV data. Get from openuv.io"
    )
    
    # Load existing data on app start
    if st.session_state.extracted_timeline is None and st.session_state.extracted_calendar is None:
        timeline_data, calendar_data = load_extracted_data()
        if timeline_data:
            st.session_state.extracted_timeline = timeline_data
        if calendar_data:
            st.session_state.extracted_calendar = calendar_data
    
    # Load enriched data if available
    if st.session_state.enriched_timeline is None and st.session_state.enriched_calendar is None:
        enriched_timeline, enriched_calendar = load_enriched_data()
        if enriched_timeline:
            st.session_state.enriched_timeline = enriched_timeline
        if enriched_calendar:
            st.session_state.enriched_calendar = enriched_calendar
    
    if page == "Data Upload":
        st.markdown('<div class="section-header">📁 Data Upload</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Google Timeline Data")
            st.info("Upload your Google Timeline JSON export file")
            
            uploaded_timeline = st.file_uploader(
                "Choose a timeline JSON file",
                type=['json'],
                key="timeline_upload"
            )
            
            if uploaded_timeline is not None:
                if st.button("Save Timeline File"):
                    file_path = save_uploaded_file(uploaded_timeline, "timeline")
                    if file_path:
                        st.success(f"Timeline file saved successfully!")
                        st.session_state.timeline_data = str(file_path)
        
        with col2:
            st.subheader("Google Calendar Data")
            st.info("Upload your Google Calendar ICS export file")
            
            uploaded_calendar = st.file_uploader(
                "Choose a calendar ICS file", 
                type=['ics'],
                key="calendar_upload"
            )
            
            if uploaded_calendar is not None:
                if st.button("Save Calendar File"):
                    file_path = save_uploaded_file(uploaded_calendar, "calendar")
                    if file_path:
                        st.success(f"Calendar file saved successfully!")
                        st.session_state.calendar_data = str(file_path)
        
        # Show file status
        st.markdown('<div class="section-header">📊 File Status</div>', unsafe_allow_html=True)
        
        timeline_file = Path("data/timeline_data.json")
        calendar_file = Path("data/calendar_data.ics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if timeline_file.exists():
                size = timeline_file.stat().st_size
                st.success(f"✅ Timeline file ready ({size:,} bytes)")
            else:
                st.warning("⚠️ No timeline file uploaded")
        
        with col2:
            if calendar_file.exists():
                size = calendar_file.stat().st_size
                st.success(f"✅ Calendar file ready ({size:,} bytes)")
            else:
                st.warning("⚠️ No calendar file uploaded")
    
    elif page == "Data Processing":
        st.markdown('<div class="section-header">⚙️ Data Processing</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Process Timeline Data")
            if Path("data/timeline_data.json").exists():
                if st.button("Extract Timeline Locations", type="primary"):
                    with st.spinner("Processing timeline data..."):
                        timeline_data = process_timeline_data(Path("data/timeline_data.json"))
                        if timeline_data:
                            st.session_state.extracted_timeline = timeline_data
                            st.success(f"✅ Extracted {len(timeline_data)} location entries from timeline data!")
                        else:
                            st.error("❌ Failed to extract timeline data")
            else:
                st.warning("Please upload a timeline file first")
        
        with col2:
            st.subheader("Process Calendar Data")
            if Path("data/calendar_data.ics").exists():
                st.info("Note: Calendar processing requires the ICS file to be converted to JSON first. Please use the calendar conversion tool in the main project.")
                if st.button("Extract Calendar Locations"):
                    with st.spinner("Processing calendar data..."):
                        calendar_data = process_calendar_data()
                        if calendar_data:
                            st.session_state.extracted_calendar = calendar_data
                            st.success(f"✅ Extracted {len(calendar_data)} location entries from calendar data!")
                        else:
                            st.error("❌ Failed to extract calendar data")
            else:
                st.warning("Please upload a calendar file first")
        
        # Show processing status
        st.markdown('<div class="section-header">📈 Processing Status</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.extracted_timeline:
                st.success(f"✅ Timeline data processed: {len(st.session_state.extracted_timeline)} entries")
            else:
                st.info("ℹ️ Timeline data not processed yet")
        
        with col2:
            if st.session_state.extracted_calendar:
                st.success(f"✅ Calendar data processed: {len(st.session_state.extracted_calendar)} entries")
            else:
                st.info("ℹ️ Calendar data not processed yet")
    
    elif page == "Environmental Analysis":
        st.markdown('<div class="section-header">🌍 Environmental Analysis</div>', unsafe_allow_html=True)
        st.markdown("Extract UV index, air quality, and weather data for your locations")
        
        # Check if API keys are configured
        if not st.session_state.google_api_key:
            st.warning("⚠️ Google Maps API key is required for environmental analysis. Please configure it in the sidebar.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Process Timeline with Environmental Data")
            if Path("data/timeline_data.json").exists():
                max_requests = st.number_input(
                    "Max API requests (to avoid rate limits)", 
                    min_value=1, 
                    max_value=100, 
                    value=20,
                    help="Lower numbers are safer for API limits"
                )
                
                if st.button("Extract Environmental Data from Timeline", type="primary"):
                    if not st.session_state.google_api_key:
                        st.error("Please configure Google Maps API key first")
                    else:
                        with st.spinner("Processing timeline with environmental data (this may take a few minutes)..."):
                            enriched_data = process_timeline_with_environmental(
                                "data/timeline_data.json", 
                                max_requests=max_requests
                            )
                            if enriched_data:
                                st.session_state.enriched_timeline = enriched_data
                                st.success(f"✅ Extracted environmental data for {len(enriched_data)} timeline entries!")
                            else:
                                st.error("❌ Failed to extract environmental data from timeline")
            else:
                st.warning("Please upload and process a timeline file first")
        
        with col2:
            st.subheader("Process Calendar with Environmental Data")
            if Path("data/calendar_data.ics").exists():
                max_requests = st.number_input(
                    "Max API requests (to avoid rate limits)", 
                    min_value=1, 
                    max_value=100, 
                    value=20,
                    help="Lower numbers are safer for API limits",
                    key="calendar_max_requests"
                )
                
                if st.button("Extract Environmental Data from Calendar", type="primary"):
                    if not st.session_state.google_api_key:
                        st.error("Please configure Google Maps API key first")
                    else:
                        with st.spinner("Processing calendar with environmental data (this may take a few minutes)..."):
                            enriched_data = process_calendar_with_environmental(
                                "data/calendar_data.ics", 
                                max_requests=max_requests
                            )
                            if enriched_data:
                                st.session_state.enriched_calendar = enriched_data
                                st.success(f"✅ Extracted environmental data for {len(enriched_data)} calendar entries!")
                            else:
                                st.error("❌ Failed to extract environmental data from calendar")
            else:
                st.warning("Please upload and process a calendar file first")
        
        # Show processing status
        st.markdown('<div class="section-header">📊 Environmental Data Status</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.enriched_timeline:
                st.success(f"✅ Timeline environmental data: {len(st.session_state.enriched_timeline)} entries")
                # Show sample metrics
                if st.session_state.enriched_timeline:
                    sample = st.session_state.enriched_timeline[0]
                    if 'environmental_data' in sample:
                        env = sample['environmental_data']
                        st.info(f"Sample: UV Index: {env.get('uv_index', 'N/A')}, AQI: {env.get('air_quality_index', 'N/A')}")
            else:
                st.info("ℹ️ Timeline environmental data not processed yet")
        
        with col2:
            if st.session_state.enriched_calendar:
                st.success(f"✅ Calendar environmental data: {len(st.session_state.enriched_calendar)} entries")
                # Show sample metrics
                if st.session_state.enriched_calendar:
                    sample = st.session_state.enriched_calendar[0]
                    if 'environmental_data' in sample:
                        env = sample['environmental_data']
                        st.info(f"Sample: UV Index: {env.get('uv_index', 'N/A')}, AQI: {env.get('air_quality_index', 'N/A')}")
            else:
                st.info("ℹ️ Calendar environmental data not processed yet")
    
    elif page == "Health Metrics":
        st.markdown('<div class="section-header">🏥 Health Metrics Analysis</div>', unsafe_allow_html=True)
        st.markdown("Calculate health risk scores based on WHO guidelines and environmental exposure patterns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Process Timeline Health Metrics")
            if st.session_state.enriched_timeline:
                if st.button("Calculate Health Metrics for Timeline", type="primary"):
                    with st.spinner("Calculating health metrics for timeline data..."):
                        health_data = process_health_metrics(st.session_state.enriched_timeline, "timeline")
                        if health_data:
                            st.session_state.health_metrics_timeline = health_data
                            st.success(f"✅ Calculated health metrics for {len(health_data)} timeline entries!")
                        else:
                            st.error("❌ Failed to calculate health metrics for timeline")
            else:
                st.warning("Please process timeline data with environmental information first")
        
        with col2:
            st.subheader("Process Calendar Health Metrics")
            if st.session_state.enriched_calendar:
                if st.button("Calculate Health Metrics for Calendar", type="primary"):
                    with st.spinner("Calculating health metrics for calendar data..."):
                        health_data = process_health_metrics(st.session_state.enriched_calendar, "calendar")
                        if health_data:
                            st.session_state.health_metrics_calendar = health_data
                            st.success(f"✅ Calculated health metrics for {len(health_data)} calendar entries!")
                        else:
                            st.error("❌ Failed to calculate health metrics for calendar")
            else:
                st.warning("Please process calendar data with environmental information first")
        
        # Show health metrics status
        st.markdown('<div class="section-header">📊 Health Metrics Status</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.health_metrics_timeline:
                st.success(f"✅ Timeline health metrics: {len(st.session_state.health_metrics_timeline)} entries")
                # Show sample health score
                if st.session_state.health_metrics_timeline:
                    sample = st.session_state.health_metrics_timeline[0]
                    if 'health_metrics' in sample:
                        health = sample['health_metrics']
                        st.info(f"Sample: Composite Score: {health.get('composite_score', 'N/A')}, Confidence: {health.get('confidence', 0):.1%}")
            else:
                st.info("ℹ️ Timeline health metrics not calculated yet")
        
        with col2:
            if st.session_state.health_metrics_calendar:
                st.success(f"✅ Calendar health metrics: {len(st.session_state.health_metrics_calendar)} entries")
                # Show sample health score
                if st.session_state.health_metrics_calendar:
                    sample = st.session_state.health_metrics_calendar[0]
                    if 'health_metrics' in sample:
                        health = sample['health_metrics']
                        st.info(f"Sample: Composite Score: {health.get('composite_score', 'N/A')}, Confidence: {health.get('confidence', 0):.1%}")
            else:
                st.info("ℹ️ Calendar health metrics not calculated yet")
        
        # Health Metrics Guidelines
        st.markdown('<div class="section-header">📋 Health Scoring Guidelines</div>', unsafe_allow_html=True)
        
        with st.expander("Health Risk Scoring System (0-100 scale)"):
            st.markdown("""
            **Risk Levels:**
            - 0-20: Minimal Risk
            - 21-40: Low Risk  
            - 41-60: Moderate Risk
            - 61-80: High Risk
            - 81-100: Very High Risk
            
            **Scoring Factors:**
            - **PM2.5**: Based on WHO 24-hour guideline (15 µg/m³)
            - **Ozone (O3)**: Based on WHO 8-hour guideline (50 ppb)
            - **UV Index**: Protection needed above 3, very high above 8
            - **Temperature**: Heat stress above 32°C, cold stress below 0°C
            - **Humidity**: Optimal 30-60%, extremes penalized
            - **Wind**: Dust risk above 30 km/h, hazard above 60 km/h
            - **Precipitation**: Heavy rain risk above 50mm/day
            
            **Composite Score**: Weighted average with PM2.5 (30%), UV (20%), Temperature (12%) having highest weights.
            """)
        
        # Show health insights if available
        if st.session_state.health_metrics_timeline or st.session_state.health_metrics_calendar:
            st.markdown('<div class="section-header">💡 Health Insights & Recommendations</div>', unsafe_allow_html=True)
            
            all_health_data = []
            if st.session_state.health_metrics_timeline:
                all_health_data.extend(st.session_state.health_metrics_timeline)
            if st.session_state.health_metrics_calendar:
                all_health_data.extend(st.session_state.health_metrics_calendar)
            
            if all_health_data:
                insights = create_health_insights_display(all_health_data)
                if insights:
                    # Show top 5 most concerning insights
                    for i, insight in enumerate(insights[:5]):
                        risk_color = "red" if insight['composite_score'] >= 80 else "orange" if insight['composite_score'] >= 60 else "yellow"
                        st.markdown(f"""
                        <div style="border-left: 4px solid {risk_color}; padding-left: 10px; margin: 10px 0;">
                            <strong>{insight['date']}</strong> (Score: {insight['composite_score']})<br>
                            {insight['insight']}
                        </div>
                        """, unsafe_allow_html=True)
                
                # Show health summary
                summary = create_health_summary_cards(all_health_data)
                if summary:
                    st.markdown("### Health Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Avg Composite Score", f"{summary['avg_composite_score']:.1f}")
                    with col2:
                        st.metric("Max Composite Score", f"{summary['max_composite_score']:.1f}")
                    with col3:
                        st.metric("Total Entries", f"{summary['total_entries']}")
                    with col4:
                        high_risk = summary['risk_distribution'].get('High Risk', 0) + summary['risk_distribution'].get('Very High Risk', 0)
                        st.metric("High Risk Days", f"{high_risk}")
    
    elif page == "Visualization":
        st.markdown('<div class="section-header">🗺️ Data Visualization</div>', unsafe_allow_html=True)
        
        # Check if we have any data to visualize
        has_basic_data = st.session_state.extracted_timeline or st.session_state.extracted_calendar
        has_env_data = st.session_state.enriched_timeline or st.session_state.enriched_calendar
        has_health_data = st.session_state.health_metrics_timeline or st.session_state.health_metrics_calendar
        
        if has_basic_data or has_env_data or has_health_data:
            # Toggle between different visualization types
            viz_options = ["Basic Location Data"]
            if has_env_data:
                viz_options.append("Environmental Data")
            if has_health_data:
                viz_options.append("Health Metrics")
            
            viz_type = st.radio(
                "Visualization Type",
                viz_options,
                horizontal=True
            )
            
            if viz_type == "Basic Location Data" and has_basic_data:
                # Basic location visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.extracted_timeline:
                        st.subheader("Timeline Location Map")
                        timeline_map = create_location_map(st.session_state.extracted_timeline, "Google Timeline Locations")
                        if timeline_map:
                            st.plotly_chart(timeline_map, use_container_width=True)
                        
                        # Timeline chart
                        timeline_chart = create_timeline_chart(st.session_state.extracted_timeline, "Timeline Entries Over Time")
                        if timeline_chart:
                            st.plotly_chart(timeline_chart, use_container_width=True)
                    else:
                        st.info("No timeline data available for visualization")
                
                with col2:
                    if st.session_state.extracted_calendar:
                        st.subheader("Calendar Location Map")
                        calendar_map = create_location_map(st.session_state.extracted_calendar, "Calendar Event Locations")
                        if calendar_map:
                            st.plotly_chart(calendar_map, use_container_width=True)
                        
                        # Calendar chart
                        calendar_chart = create_timeline_chart(st.session_state.extracted_calendar, "Calendar Events Over Time")
                        if calendar_chart:
                            st.plotly_chart(calendar_chart, use_container_width=True)
                    else:
                        st.info("No calendar data available for visualization")
                
                # Combined data if both are available
                if st.session_state.extracted_timeline and st.session_state.extracted_calendar:
                    st.markdown('<div class="section-header">🔄 Combined Data</div>', unsafe_allow_html=True)
                    
                    combined_data = st.session_state.extracted_timeline + st.session_state.extracted_calendar
                    combined_map = create_location_map(combined_data, "All Location Data Combined")
                    
                    if combined_map:
                        st.plotly_chart(combined_map, use_container_width=True)
            
            elif viz_type == "Environmental Data" and has_env_data:
                # Environmental data visualizations
                st.markdown('<div class="section-header">🌍 Environmental Metrics Over Time</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.enriched_timeline:
                        st.subheader("Timeline Environmental Data")
                        env_timeline_chart = create_environmental_metrics_chart(
                            st.session_state.enriched_timeline, 
                            "Timeline Environmental Metrics"
                        )
                        if env_timeline_chart:
                            st.plotly_chart(env_timeline_chart, use_container_width=True)
                        
                        # Environmental map for timeline
                        env_timeline_map = create_environmental_map(
                            st.session_state.enriched_timeline, 
                            "Timeline Locations with Environmental Data"
                        )
                        if env_timeline_map:
                            st.plotly_chart(env_timeline_map, use_container_width=True)
                    else:
                        st.info("No timeline environmental data available")
                
                with col2:
                    if st.session_state.enriched_calendar:
                        st.subheader("Calendar Environmental Data")
                        env_calendar_chart = create_environmental_metrics_chart(
                            st.session_state.enriched_calendar, 
                            "Calendar Environmental Metrics"
                        )
                        if env_calendar_chart:
                            st.plotly_chart(env_calendar_chart, use_container_width=True)
                        
                        # Environmental map for calendar
                        env_calendar_map = create_environmental_map(
                            st.session_state.enriched_calendar, 
                            "Calendar Locations with Environmental Data"
                        )
                        if env_calendar_map:
                            st.plotly_chart(env_calendar_map, use_container_width=True)
                    else:
                        st.info("No calendar environmental data available")
                
                # Combined environmental data
                if st.session_state.enriched_timeline and st.session_state.enriched_calendar:
                    st.markdown('<div class="section-header">🔄 Combined Environmental Data</div>', unsafe_allow_html=True)
                    
                    combined_env_data = st.session_state.enriched_timeline + st.session_state.enriched_calendar
                    combined_env_chart = create_environmental_metrics_chart(
                        combined_env_data, 
                        "All Environmental Data Combined"
                    )
                    if combined_env_chart:
                        st.plotly_chart(combined_env_chart, use_container_width=True)
                    
                    combined_env_map = create_environmental_map(
                        combined_env_data, 
                        "All Locations with Environmental Data"
                    )
                    if combined_env_map:
                        st.plotly_chart(combined_env_map, use_container_width=True)
            
            elif viz_type == "Health Metrics" and has_health_data:
                # Health metrics visualizations
                st.markdown('<div class="section-header">🏥 Health Metrics Visualization</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.health_metrics_timeline:
                        st.subheader("Timeline Health Metrics")
                        health_timeline_chart = create_health_metrics_chart(
                            st.session_state.health_metrics_timeline, 
                            "Timeline Health Risk Scores"
                        )
                        if health_timeline_chart:
                            st.plotly_chart(health_timeline_chart, use_container_width=True)
                    else:
                        st.info("No timeline health metrics available")
                
                with col2:
                    if st.session_state.health_metrics_calendar:
                        st.subheader("Calendar Health Metrics")
                        health_calendar_chart = create_health_metrics_chart(
                            st.session_state.health_metrics_calendar, 
                            "Calendar Health Risk Scores"
                        )
                        if health_calendar_chart:
                            st.plotly_chart(health_calendar_chart, use_container_width=True)
                    else:
                        st.info("No calendar health metrics available")
                
                # Combined health metrics
                if st.session_state.health_metrics_timeline and st.session_state.health_metrics_calendar:
                    st.markdown('<div class="section-header">🔄 Combined Health Metrics</div>', unsafe_allow_html=True)
                    
                    combined_health_data = st.session_state.health_metrics_timeline + st.session_state.health_metrics_calendar
                    combined_health_chart = create_health_metrics_chart(
                        combined_health_data, 
                        "All Health Risk Data Combined"
                    )
                    if combined_health_chart:
                        st.plotly_chart(combined_health_chart, use_container_width=True)
                
                # Health insights display
                all_health_data = []
                if st.session_state.health_metrics_timeline:
                    all_health_data.extend(st.session_state.health_metrics_timeline)
                if st.session_state.health_metrics_calendar:
                    all_health_data.extend(st.session_state.health_metrics_calendar)
                
                if all_health_data:
                    st.markdown('<div class="section-header">💡 Health Insights Timeline</div>', unsafe_allow_html=True)
                    insights = create_health_insights_display(all_health_data)
                    if insights:
                        # Create a timeline of insights
                        for insight in insights[:10]:  # Show top 10
                            risk_color = "red" if insight['composite_score'] >= 80 else "orange" if insight['composite_score'] >= 60 else "yellow"
                            st.markdown(f"""
                            <div style="border-left: 4px solid {risk_color}; padding: 10px; margin: 5px 0; background-color: #f8f9fa;">
                                <strong>{insight['date']}</strong> - Health Score: {insight['composite_score']}/100<br>
                                {insight['insight']}
                            </div>
                            """, unsafe_allow_html=True)
        
        else:
            st.warning("Please process some data first to see visualizations")
    
    elif page == "Data Export":
        st.markdown('<div class="section-header">💾 Data Export</div>', unsafe_allow_html=True)
        
        # Check what data is available
        has_basic_data = st.session_state.extracted_timeline or st.session_state.extracted_calendar
        has_env_data = st.session_state.enriched_timeline or st.session_state.enriched_calendar
        has_health_data = st.session_state.health_metrics_timeline or st.session_state.health_metrics_calendar
        
        if has_basic_data or has_env_data or has_health_data:
            # Toggle between different export types
            export_options = ["Basic Location Data"]
            if has_env_data:
                export_options.append("Environmental Data")
            if has_health_data:
                export_options.append("Health Metrics")
            
            export_type = st.radio(
                "Export Type",
                export_options,
                horizontal=True
            )
            
            if export_type == "Basic Location Data" and has_basic_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.extracted_timeline:
                        st.subheader("Timeline Data")
                        timeline_df = pd.DataFrame(st.session_state.extracted_timeline)
                        st.dataframe(timeline_df)
                        
                        csv_data = timeline_df.to_csv(index=False)
                        st.download_button(
                            label="Download Timeline Data as CSV",
                            data=csv_data,
                            file_name=f"timeline_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No timeline data available for export")
                
                with col2:
                    if st.session_state.extracted_calendar:
                        st.subheader("Calendar Data")
                        calendar_df = pd.DataFrame(st.session_state.extracted_calendar)
                        st.dataframe(calendar_df)
                        
                        csv_data = calendar_df.to_csv(index=False)
                        st.download_button(
                            label="Download Calendar Data as CSV",
                            data=csv_data,
                            file_name=f"calendar_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No calendar data available for export")
                
                # Combined basic data export
                if st.session_state.extracted_timeline and st.session_state.extracted_calendar:
                    st.markdown("### Combined Basic Data Export")
                    combined_data = st.session_state.extracted_timeline + st.session_state.extracted_calendar
                    combined_df = pd.DataFrame(combined_data)
                    st.dataframe(combined_df)
                    
                    csv_data = combined_df.to_csv(index=False)
                    st.download_button(
                        label="Download All Basic Data as CSV",
                        data=csv_data,
                        file_name=f"all_location_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            elif export_type == "Environmental Data" and has_env_data:
                st.markdown("### Environmental Data Export")
                st.info("This includes location data with UV index, air quality, temperature, humidity, and other environmental metrics.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.enriched_timeline:
                        st.subheader("Timeline Environmental Data")
                        
                        # Flatten environmental data for better CSV export
                        timeline_export_data = []
                        for entry in st.session_state.enriched_timeline:
                            export_entry = {
                                'lat': entry['lat'],
                                'lon': entry['lon'],
                                'date_str': entry['date_str']
                            }
                            if 'environmental_data' in entry:
                                env = entry['environmental_data']
                                export_entry.update({
                                    'uv_index': env.get('uv_index'),
                                    'uv_index_max': env.get('uv_index_max'),
                                    'temperature': env.get('temperature'),
                                    'humidity': env.get('humidity'),
                                    'air_quality_index': env.get('air_quality_index'),
                                    'air_quality_level': env.get('air_quality_level'),
                                    'precipitation': env.get('precipitation'),
                                    'cloud_cover': env.get('cloud_cover'),
                                    'wind_speed': env.get('wind_speed'),
                                    'data_sources': ', '.join(env.get('data_sources', [])),
                                    'errors': ', '.join(env.get('errors', []))
                                })
                            timeline_export_data.append(export_entry)
                        
                        timeline_df = pd.DataFrame(timeline_export_data)
                        st.dataframe(timeline_df)
                        
                        csv_data = timeline_df.to_csv(index=False)
                        st.download_button(
                            label="Download Timeline Environmental Data as CSV",
                            data=csv_data,
                            file_name=f"timeline_environmental_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No timeline environmental data available for export")
                
                with col2:
                    if st.session_state.enriched_calendar:
                        st.subheader("Calendar Environmental Data")
                        
                        # Flatten environmental data for better CSV export
                        calendar_export_data = []
                        for entry in st.session_state.enriched_calendar:
                            export_entry = {
                                'lat': entry['lat'],
                                'lon': entry['lon'],
                                'date_str': entry['date_str']
                            }
                            if 'environmental_data' in entry:
                                env = entry['environmental_data']
                                export_entry.update({
                                    'uv_index': env.get('uv_index'),
                                    'uv_index_max': env.get('uv_index_max'),
                                    'temperature': env.get('temperature'),
                                    'humidity': env.get('humidity'),
                                    'air_quality_index': env.get('air_quality_index'),
                                    'air_quality_level': env.get('air_quality_level'),
                                    'precipitation': env.get('precipitation'),
                                    'cloud_cover': env.get('cloud_cover'),
                                    'wind_speed': env.get('wind_speed'),
                                    'data_sources': ', '.join(env.get('data_sources', [])),
                                    'errors': ', '.join(env.get('errors', []))
                                })
                            calendar_export_data.append(export_entry)
                        
                        calendar_df = pd.DataFrame(calendar_export_data)
                        st.dataframe(calendar_df)
                        
                        csv_data = calendar_df.to_csv(index=False)
                        st.download_button(
                            label="Download Calendar Environmental Data as CSV",
                            data=csv_data,
                            file_name=f"calendar_environmental_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No calendar environmental data available for export")
                
                # Combined environmental data export
                if st.session_state.enriched_timeline and st.session_state.enriched_calendar:
                    st.markdown("### Combined Environmental Data Export")
                    
                    combined_env_data = st.session_state.enriched_timeline + st.session_state.enriched_calendar
                    combined_export_data = []
                    for entry in combined_env_data:
                        export_entry = {
                            'lat': entry['lat'],
                            'lon': entry['lon'],
                            'date_str': entry['date_str']
                        }
                        if 'environmental_data' in entry:
                            env = entry['environmental_data']
                            export_entry.update({
                                'uv_index': env.get('uv_index'),
                                'uv_index_max': env.get('uv_index_max'),
                                'temperature': env.get('temperature'),
                                'humidity': env.get('humidity'),
                                'air_quality_index': env.get('air_quality_index'),
                                'air_quality_level': env.get('air_quality_level'),
                                'precipitation': env.get('precipitation'),
                                'cloud_cover': env.get('cloud_cover'),
                                'wind_speed': env.get('wind_speed'),
                                'data_sources': ', '.join(env.get('data_sources', [])),
                                'errors': ', '.join(env.get('errors', []))
                            })
                        combined_export_data.append(export_entry)
                    
                    combined_df = pd.DataFrame(combined_export_data)
                    st.dataframe(combined_df)
                    
                    csv_data = combined_df.to_csv(index=False)
                    st.download_button(
                        label="Download All Environmental Data as CSV",
                        data=csv_data,
                        file_name=f"all_environmental_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            elif export_type == "Health Metrics" and has_health_data:
                st.markdown("### Health Metrics Export")
                st.info("This includes location data with health risk scores, insights, and recommendations based on WHO guidelines.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.health_metrics_timeline:
                        st.subheader("Timeline Health Metrics")
                        
                        # Flatten health metrics data for better CSV export
                        timeline_export_data = []
                        for entry in st.session_state.health_metrics_timeline:
                            export_entry = {
                                'lat': entry['lat'],
                                'lon': entry['lon'],
                                'date_str': entry['date_str']
                            }
                            if 'health_metrics' in entry:
                                health = entry['health_metrics']
                                export_entry.update({
                                    'composite_score': health.get('composite_score', 0),
                                    'confidence': health.get('confidence', 0),
                                    'pm25_score': health.get('scores', {}).get('pm25', 0),
                                    'o3_score': health.get('scores', {}).get('o3', 0),
                                    'uv_score': health.get('scores', {}).get('uv', 0),
                                    'temp_score': health.get('scores', {}).get('temp', 0),
                                    'humidity_score': health.get('scores', {}).get('humidity_dew', 0),
                                    'wind_score': health.get('scores', {}).get('wind', 0),
                                    'precip_score': health.get('scores', {}).get('precip', 0),
                                    'pm25_risk': health.get('risk_levels', {}).get('pm25', 'N/A'),
                                    'o3_risk': health.get('risk_levels', {}).get('o3', 'N/A'),
                                    'uv_risk': health.get('risk_levels', {}).get('uv', 'N/A'),
                                    'temp_risk': health.get('risk_levels', {}).get('temp', 'N/A'),
                                    'insights': '; '.join(health.get('insights', []))
                                })
                            timeline_export_data.append(export_entry)
                        
                        timeline_df = pd.DataFrame(timeline_export_data)
                        st.dataframe(timeline_df)
                        
                        csv_data = timeline_df.to_csv(index=False)
                        st.download_button(
                            label="Download Timeline Health Metrics as CSV",
                            data=csv_data,
                            file_name=f"timeline_health_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No timeline health metrics available for export")
                
                with col2:
                    if st.session_state.health_metrics_calendar:
                        st.subheader("Calendar Health Metrics")
                        
                        # Flatten health metrics data for better CSV export
                        calendar_export_data = []
                        for entry in st.session_state.health_metrics_calendar:
                            export_entry = {
                                'lat': entry['lat'],
                                'lon': entry['lon'],
                                'date_str': entry['date_str']
                            }
                            if 'health_metrics' in entry:
                                health = entry['health_metrics']
                                export_entry.update({
                                    'composite_score': health.get('composite_score', 0),
                                    'confidence': health.get('confidence', 0),
                                    'pm25_score': health.get('scores', {}).get('pm25', 0),
                                    'o3_score': health.get('scores', {}).get('o3', 0),
                                    'uv_score': health.get('scores', {}).get('uv', 0),
                                    'temp_score': health.get('scores', {}).get('temp', 0),
                                    'humidity_score': health.get('scores', {}).get('humidity_dew', 0),
                                    'wind_score': health.get('scores', {}).get('wind', 0),
                                    'precip_score': health.get('scores', {}).get('precip', 0),
                                    'pm25_risk': health.get('risk_levels', {}).get('pm25', 'N/A'),
                                    'o3_risk': health.get('risk_levels', {}).get('o3', 'N/A'),
                                    'uv_risk': health.get('risk_levels', {}).get('uv', 'N/A'),
                                    'temp_risk': health.get('risk_levels', {}).get('temp', 'N/A'),
                                    'insights': '; '.join(health.get('insights', []))
                                })
                            calendar_export_data.append(export_entry)
                        
                        calendar_df = pd.DataFrame(calendar_export_data)
                        st.dataframe(calendar_df)
                        
                        csv_data = calendar_df.to_csv(index=False)
                        st.download_button(
                            label="Download Calendar Health Metrics as CSV",
                            data=csv_data,
                            file_name=f"calendar_health_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No calendar health metrics available for export")
                
                # Combined health metrics export
                if st.session_state.health_metrics_timeline and st.session_state.health_metrics_calendar:
                    st.markdown("### Combined Health Metrics Export")
                    
                    combined_health_data = st.session_state.health_metrics_timeline + st.session_state.health_metrics_calendar
                    combined_export_data = []
                    for entry in combined_health_data:
                        export_entry = {
                            'lat': entry['lat'],
                            'lon': entry['lon'],
                            'date_str': entry['date_str']
                        }
                        if 'health_metrics' in entry:
                            health = entry['health_metrics']
                            export_entry.update({
                                'composite_score': health.get('composite_score', 0),
                                'confidence': health.get('confidence', 0),
                                'pm25_score': health.get('scores', {}).get('pm25', 0),
                                'o3_score': health.get('scores', {}).get('o3', 0),
                                'uv_score': health.get('scores', {}).get('uv', 0),
                                'temp_score': health.get('scores', {}).get('temp', 0),
                                'humidity_score': health.get('scores', {}).get('humidity_dew', 0),
                                'wind_score': health.get('scores', {}).get('wind', 0),
                                'precip_score': health.get('scores', {}).get('precip', 0),
                                'pm25_risk': health.get('risk_levels', {}).get('pm25', 'N/A'),
                                'o3_risk': health.get('risk_levels', {}).get('o3', 'N/A'),
                                'uv_risk': health.get('risk_levels', {}).get('uv', 'N/A'),
                                'temp_risk': health.get('risk_levels', {}).get('temp', 'N/A'),
                                'insights': '; '.join(health.get('insights', []))
                            })
                        combined_export_data.append(export_entry)
                    
                    combined_df = pd.DataFrame(combined_export_data)
                    st.dataframe(combined_df)
                    
                    csv_data = combined_df.to_csv(index=False)
                    st.download_button(
                        label="Download All Health Metrics as CSV",
                        data=csv_data,
                        file_name=f"all_health_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
        
        else:
            st.warning("Please process some data first to see export options")

if __name__ == "__main__":
    main()
