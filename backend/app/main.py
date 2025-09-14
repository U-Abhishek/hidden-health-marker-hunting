from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload_data

app = FastAPI(title="Hidden Health Marker Hunting API")

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Include routers
app.include_router(upload_data.router)

@app.get("/")
async def root():
    return {"message": "Hidden Health Marker Hunting API", "status": "running"}