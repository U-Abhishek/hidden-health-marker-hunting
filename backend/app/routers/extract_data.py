from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import json
from typing import Dict, List, Any
from datetime import datetime

from services.timeline_extraction import process_timeline_file
from services.calender_extraction import oprate_calendar_data

router = APIRouter(prefix="/extract", tags=["extract"])

# Ensure extracted_data directory exists
EXTRACTED_DATA_DIR = "app/data/extracted_data"
os.makedirs(EXTRACTED_DATA_DIR, exist_ok=True)

@router.post("/timeline")
async def extract_timeline_data():
    """
    Extract timeline data from timeline_data.json and save to extracted_data folder.
    Processes Google Maps timeline data to extract daily location coordinates.
    """
    try:
        timeline_file_path = "app/data/timeline_data.json"
        
        if not os.path.exists(timeline_file_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Timeline file not found at {timeline_file_path}"
            )
        
        # Process timeline data
        daily_location_data = process_timeline_file(timeline_file_path)
        
        if not daily_location_data:
            raise HTTPException(
                status_code=400,
                detail="No timeline data could be extracted from the file"
            )
        
        # Save extracted data
        output_file = os.path.join(EXTRACTED_DATA_DIR, "timeline_extracted.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(daily_location_data, f, indent=2, ensure_ascii=False)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Timeline data extracted successfully",
                "extracted_entries": len(daily_location_data),
                "output_file": output_file,
                "sample_data": daily_location_data[:5] if daily_location_data else []
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting timeline data: {str(e)}"
        )

@router.post("/calendar")
async def extract_calendar_data():
    """
    Extract calendar data from calendar JSON files and save to extracted_data folder.
    Processes calendar events to extract location coordinates and dates.
    """
    try:
        # Look for calendar JSON files in the data directory
        data_dir = "data"
        calendar_files = []
        
        for file in os.listdir(data_dir):
            if file.endswith('.json') and 'calendar' in file.lower():
                calendar_files.append(os.path.join(data_dir, file))
        
        if not calendar_files:
            raise HTTPException(
                status_code=404,
                detail="No calendar JSON files found in data directory"
            )
        
        all_extracted_data = []
        
        for calendar_file in calendar_files:
            try:
                # Process calendar data
                event_data = oprate_calendar_data(calendar_file)
                
                if event_data:
                    all_extracted_data.extend(event_data)
                    print(f"Extracted {len(event_data)} events from {calendar_file}")
                else:
                    print(f"No data extracted from {calendar_file}")
                    
            except Exception as e:
                print(f"Error processing {calendar_file}: {str(e)}")
                continue
        
        if not all_extracted_data:
            raise HTTPException(
                status_code=400,
                detail="No calendar data could be extracted from any files"
            )
        
        # Save extracted data
        output_file = os.path.join(EXTRACTED_DATA_DIR, "calendar_extracted.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_extracted_data, f, indent=2, ensure_ascii=False)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Calendar data extracted successfully",
                "extracted_entries": len(all_extracted_data),
                "processed_files": len(calendar_files),
                "output_file": output_file,
                "sample_data": all_extracted_data[:5] if all_extracted_data else []
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting calendar data: {str(e)}"
        )

@router.get("/status")
async def get_extraction_status():
    """
    Get the status of extracted data files.
    """
    try:
        timeline_file = os.path.join(EXTRACTED_DATA_DIR, "timeline_extracted.json")
        calendar_file = os.path.join(EXTRACTED_DATA_DIR, "calendar_extracted.json")
        
        status = {
            "timeline_data": {
                "exists": os.path.exists(timeline_file),
                "file_path": timeline_file,
                "last_modified": None,
                "entry_count": 0
            },
            "calendar_data": {
                "exists": os.path.exists(calendar_file),
                "file_path": calendar_file,
                "last_modified": None,
                "entry_count": 0
            }
        }
        
        # Check timeline data
        if status["timeline_data"]["exists"]:
            stat = os.stat(timeline_file)
            status["timeline_data"]["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            with open(timeline_file, 'r') as f:
                data = json.load(f)
                status["timeline_data"]["entry_count"] = len(data) if isinstance(data, list) else 0
        
        # Check calendar data
        if status["calendar_data"]["exists"]:
            stat = os.stat(calendar_file)
            status["calendar_data"]["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            with open(calendar_file, 'r') as f:
                data = json.load(f)
                status["calendar_data"]["entry_count"] = len(data) if isinstance(data, list) else 0
        
        return JSONResponse(status_code=200, content=status)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting extraction status: {str(e)}"
        )

