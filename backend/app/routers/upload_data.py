"""
Upload Data Router
-----------------
Handles file uploads for Google Timeline (.json) and Calendar (.ics) files.
Saves uploaded files to the data folder with proper validation.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

# Create router
router = APIRouter(prefix="/upload", tags=["upload"])

# Data directory path
DATA_DIR = Path("app/data")
DATA_DIR.mkdir(exist_ok=True)


def validate_json_file(file: UploadFile) -> bool:
    """
    Validate that the uploaded file is a valid JSON file.
    
    Parameters
    ----------
    file : UploadFile
        The uploaded file object
    
    Returns
    -------
    bool
        True if valid JSON file, False otherwise
    """
    if not file.filename:
        return False
    
    # Check file extension
    if not file.filename.lower().endswith('.json'):
        return False
    
    return True


def validate_ics_file(file: UploadFile) -> bool:
    """
    Validate that the uploaded file is a valid ICS file.
    
    Parameters
    ----------
    file : UploadFile
        The uploaded file object
    
    Returns
    -------
    bool
        True if valid ICS file, False otherwise
    """
    if not file.filename:
        return False
    
    # Check file extension
    if not file.filename.lower().endswith('.ics'):
        return False
    
    return True


def save_uploaded_file(file: UploadFile, destination: Path) -> Dict[str, Any]:
    """
    Save uploaded file to destination path.
    
    Parameters
    ----------
    file : UploadFile
        The uploaded file object
    destination : Path
        Destination path to save the file
    
    Returns
    -------
    Dict[str, Any]
        File information including size and path
    """
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = destination.stat().st_size
        
        return {
            "filename": file.filename,
            "saved_path": str(destination),
            "file_size": file_size,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


@router.post("/timeline")
async def upload_timeline_file(
    file: UploadFile = File(..., description="Google Timeline JSON file")
) -> JSONResponse:
    """
    Upload Google Timeline JSON file.
    
    Parameters
    ----------
    file : UploadFile
        The uploaded JSON file containing Google Timeline data
    
    Returns
    -------
    JSONResponse
        Success message with file information
    """
    # Validate file
    if not validate_json_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a JSON file."
        )
    
    # Create destination path
    destination = DATA_DIR / "timeline_data.json"
    
    # Save file
    file_info = save_uploaded_file(file, destination)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Google Timeline file uploaded successfully",
            "file_info": file_info
        }
    )


@router.post("/calendar")
async def upload_calendar_file(
    file: UploadFile = File(..., description="Google Calendar ICS file")
) -> JSONResponse:
    """
    Upload Google Calendar ICS file.
    
    Parameters
    ----------
    file : UploadFile
        The uploaded ICS file containing Google Calendar data
    
    Returns
    -------
    JSONResponse
        Success message with file information
    """
    # Validate file
    if not validate_ics_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload an ICS file."
        )
    
    # Create destination path
    destination = DATA_DIR / "calendar_data.ics"
    
    # Save file
    file_info = save_uploaded_file(file, destination)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Google Calendar file uploaded successfully",
            "file_info": file_info
        }
    )


@router.get("/status")
async def get_upload_status() -> JSONResponse:
    """
    Get status of uploaded files in the data directory.
    
    Returns
    -------
    JSONResponse
        Status of available files in the data directory
    """
    files_status = {}
    
    # Check for timeline file
    timeline_file = DATA_DIR / "timeline_data.json"
    files_status["timeline"] = {
        "exists": timeline_file.exists(),
        "path": str(timeline_file),
        "size": timeline_file.stat().st_size if timeline_file.exists() else 0
    }
    
    # Check for calendar file
    calendar_file = DATA_DIR / "calendar_data.ics"
    files_status["calendar"] = {
        "exists": calendar_file.exists(),
        "path": str(calendar_file),
        "size": calendar_file.stat().st_size if calendar_file.exists() else 0
    }
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Upload status retrieved successfully",
            "files": files_status
        }
    )