import os
from typing import Optional

class Settings:
    def __init__(self):
        # Data Directory
        # each file will have a unique name there are 2 files timeline and calendar
        self.timeline_data_file_name = os.getenv("TIMELINE_DATA_FILE", "timeline_data.json")
        self.calendar_data_file_name = os.getenv("CALENDAR_DATA_FILE", "calendar_data.ics")
        
        # Data paths
        self.data_dir = os.getenv("DATA_DIR", "./data")
        self.extracted_data_dir = os.getenv("EXTRACTED_DATA_DIR", "./backend/app/data/extracted_data")

        # API Keys
        self.google_maps_api_key: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY")
        self.openuv_api_key: Optional[str] = os.getenv("OPENUV_API_KEY")
        
        # Application settings
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        
        # CORS settings
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "./logs/app.log")
        
        # External services
        self.nominatim_user_agent = os.getenv("NOMINATIM_USER_AGENT", "HiddenHealthMarkerHunting/1.0")
        
        # Security
        self.secret_key: Optional[str] = os.getenv("SECRET_KEY")
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

settings = Settings()
