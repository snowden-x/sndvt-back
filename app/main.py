"""Main FastAPI application with modular structure."""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.ai_assistant.services.knowledge_service import KnowledgeService
from app.ai_assistant.services.model_service import ModelService
from app.ai_assistant.api.chat import router as chat_router, initialize_chat_api
from app.device_discovery.api.discovery import router as discovery_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initializes all the necessary components for the AI assistant on app startup.
    """
    settings = get_settings()
    print("--- Server starting up ---")
    print(f"🚀 Performance Settings:")
    print(f"   Keep Alive: {settings.ollama_keep_alive}")
    print(f"   Temperature: {settings.ollama_temperature}")
    print(f"   Top-P: {settings.ollama_top_p}")
    print(f"   Top-K: {settings.ollama_top_k}")
    print(f"   Max Tokens: {settings.ollama_num_predict}")
    print(f"   Context Size: {settings.ollama_context_size}")
    
    try:
        # Initialize knowledge base
        knowledge_service = KnowledgeService()
        vectorstore = knowledge_service.create_or_load_knowledge_base()
        
        # Initialize model service
        model_service = ModelService()
        await model_service.initialize_llm()
        await model_service.preload_and_warm_model()
        model_service.initialize_qa_chain(vectorstore)
        
        # Initialize chat API with services
        initialize_chat_api(model_service)
        
        print("--- All services initialized successfully! ---")
    except Exception as e:
        print(f"FATAL: Failed to initialize services: {e}")
    
    yield
    
    # Cleanup
    print("--- Server shutting down ---")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(chat_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port) 