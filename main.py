"""
New main entry point using the reorganized modular structure.
Run this file to start the application with the new architecture.
"""

import uvicorn
from app.main import app
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    print("🚀 Starting SNDVT Backend with new modular architecture...")
    print(f"📡 Server will be available at http://{settings.host}:{settings.port}")
    print(f"📚 API documentation at http://{settings.host}:{settings.port}/docs")
    
    uvicorn.run(app, host=settings.host, port=settings.port) 