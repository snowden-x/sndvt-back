"""Application settings and configuration."""

import os
import secrets
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
    ollama_llm_model: str = "gemma3:4b-it-qat"  # Model for text generation
    
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
    
    # --- Authentication Configuration ---
    # JWT Secret key - should be set in environment for production
    secret_key: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    
    # --- NetPredict Integration Configuration ---
    netpredict_api_url: str = os.getenv("NETPREDICT_API_URL", "http://localhost:8002")
    netpredict_timeout: int = int(os.getenv("NETPREDICT_TIMEOUT", "30"))
    netpredict_poll_interval: int = int(os.getenv("NETPREDICT_POLL_INTERVAL", "30"))
    
    # --- Network Agent Integration Configuration ---
    network_agent_api_url: str = os.getenv("NETWORK_AGENT_API_URL", "http://localhost:8001")
    network_agent_timeout: int = int(os.getenv("NETWORK_AGENT_TIMEOUT", "30"))
    ollama_api_url: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    
    # --- Real-time Features Configuration ---
    enable_websockets: bool = os.getenv("ENABLE_WEBSOCKETS", "true").lower() == "true"
    alert_stream_enabled: bool = os.getenv("ALERT_STREAM_ENABLED", "true").lower() == "true"
    
    # --- Logging Configuration ---
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # --- Ollama Model Configuration ---
    ollama_model: str = os.getenv("OLLAMA_MODEL", "mistral")
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 