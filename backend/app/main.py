from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import upload_data, extract_data
from config import settings

app = FastAPI(
    title="Hidden Health Marker Hunting API",
    debug=settings.debug
)

# CORS
app.add_middleware(
    CORSMiddleware, 
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(upload_data.router)
app.include_router(extract_data.router)

@app.get("/")
async def root():
    return {"message": "Hidden Health Marker Hunting API", "status": "running"}