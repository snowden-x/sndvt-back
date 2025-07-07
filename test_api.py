#!/usr/bin/env python3
"""
Test API Server
Quick test of the device monitoring API with SQLite backend
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.device_monitoring.api.api import router, initialize_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🗄️ Initializing SQLite database...")
    await initialize_database()
    print("✅ Database initialized successfully")
    yield
    # Shutdown (cleanup code would go here)

app = FastAPI(
    title="SNDVT Device Monitoring API",
    description="API for network device monitoring and management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the device monitoring router
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "SNDVT Device Monitoring API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "sqlite"}

if __name__ == "__main__":
    print("🚀 Starting SNDVT Device Monitoring API Server...")
    print("📍 API will be available at: http://localhost:8000")
    print("📊 API docs will be available at: http://localhost:8000/docs")
    print("🗄️ Using SQLite database backend")
    
    uvicorn.run(
        "test_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 