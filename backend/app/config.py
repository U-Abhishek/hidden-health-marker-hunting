import os

class Settings:
    def __init__(self):

        # Data Directory
        # each file will have a unique name there are 2 files timeline and calendar
        self.timeline_data_file_name = "timeline_data.json"
        self.calendar_data_file_name = "calendar_data.ics"

        # API Keys
        # self.google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        # self.openuv_api_key = os.getenv("OPENUV_API_KEY")

settings = Settings()
