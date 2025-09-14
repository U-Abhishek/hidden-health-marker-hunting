# Hidden Health Marker Hunting - Backend API

FastAPI backend for processing Google Timeline and Calendar data to extract health markers.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file (optional):
```bash
cp .env.example .env
```

3. Run the application:
```bash
python -m app.main
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Upload Endpoints

- `POST /upload/timeline` - Upload Google Timeline JSON file
- `POST /upload/calendar` - Upload Google Calendar ICS file  
- `GET /upload/status` - Check status of uploaded files

### General Endpoints

- `GET /` - API information and status
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

## File Upload

The API accepts two types of files:

1. **Google Timeline JSON** - Uploaded to `/upload/timeline`
   - File extension: `.json`
   - Saved as: `app/data/timeline_data.json`

2. **Google Calendar ICS** - Uploaded to `/upload/calendar`
   - File extension: `.ics`
   - Saved as: `app/data/calendar_data.ics`

## Configuration

Environment variables can be set in a `.env` file:

- `APP_NAME` - Application name
- `DEBUG` - Enable debug mode
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)
- `GOOGLE_MAPS_API_KEY` - Google Maps API key (optional)
- `OPENUV_API_KEY` - OpenUV API key (optional)

## Usage Example

```python
import requests

# Upload timeline file
with open('timeline_data.json', 'rb') as f:
    response = requests.post('http://localhost:8000/upload/timeline', files={'file': f})
    print(response.json())

# Check upload status
response = requests.get('http://localhost:8000/upload/status')
print(response.json())
```
