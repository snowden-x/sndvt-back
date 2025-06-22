"""Application settings and configuration."""

import os
from functools import lru_cache
from typing import List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # --- AI Assistant Configuration ---
    # Path to the directory containing network documentation
    docs_dir: str = "data/network_docs"
    # Directory to persist the ChromaDB vector store
    persist_dir: str = "data/chroma_db"
    # Name of the local Ollama models to use
    ollama_embedding_model: str = "nomic-embed-text"  # Model for embeddings
    ollama_llm_model: str = "gemma3:4b"  # Model for text generation
    
    # Performance optimization settings
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "-1")  # Keep model loaded indefinitely
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))  # Lower for more focused responses
    ollama_top_p: float = float(os.getenv("OLLAMA_TOP_P", "0.8"))  # Top-p sampling
    ollama_top_k: int = int(os.getenv("OLLAMA_TOP_K", "40"))  # Top-k sampling
    ollama_num_predict: int = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))  # Max tokens to generate
    ollama_context_size: int = int(os.getenv("OLLAMA_CONTEXT_SIZE", "4096"))  # Context size
    
    # Query processing settings
    max_query_length: int = 500
    max_context_chars: int = 2500
    
    # --- FastAPI Configuration ---
    app_title: str = "Network Engineer AI Assistant"
    app_description: str = "An AI assistant for network engineers, powered by LangChain, Ollama, and ChromaDB with real-time device monitoring."
    app_version: str = "1.0.0"
    
    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173", 
        "http://localhost:3000"
    ]
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 