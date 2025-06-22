#!/usr/bin/env python3
"""
Optimized startup script for the Network Engineer AI Assistant
Sets performance environment variables and starts the server
"""
import os
import sys
import subprocess
from pathlib import Path

def set_performance_env():
    """Set optimal environment variables for Ollama performance."""
    env_vars = {
        # Keep model loaded indefinitely
        "OLLAMA_KEEP_ALIVE": "-1",
        
        # Performance optimizations
        "OLLAMA_TEMPERATURE": "0.3",      # More focused responses
        "OLLAMA_TOP_P": "0.8",           # Top-p sampling
        "OLLAMA_TOP_K": "40",            # Top-k sampling
        "OLLAMA_NUM_PREDICT": "512",     # Max tokens per response
        "OLLAMA_CONTEXT_SIZE": "4096",   # Consistent context size
        
        # Ollama server optimizations (if running Ollama locally)
        "OLLAMA_MAX_LOADED_MODELS": "3", # Allow multiple models
        "OLLAMA_NUM_PARALLEL": "4",      # Parallel processing
    }
    
    print("🚀 Setting performance environment variables:")
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"   {key}={value}")
    
    print()

def check_ollama_running():
    """Check if Ollama is running."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_models_available():
    """Check if required models are available."""
    required_models = ["gemma3:4b", "nomic-embed-text"]
    available_models = []
    
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    available_models.append(model_name)
    except:
        pass
    
    # Check for models with more flexible matching (handle :latest suffix)
    missing_models = []
    for required_model in required_models:
        found = False
        for available_model in available_models:
            if available_model.startswith(required_model):
                found = True
                break
        if not found:
            missing_models.append(required_model)
    
    if missing_models:
        print("⚠️ Missing required models:")
        for model in missing_models:
            print(f"   - {model}")
        print("\nTo install missing models, run:")
        for model in missing_models:
            print(f"   ollama pull {model}")
        print()
        return False
    
    print("✅ All required models are available")
    return True

def preload_models():
    """Preload models to ensure they're ready."""
    models_to_preload = ["gemma3:4b"]
    
    print("🔥 Preloading models...")
    for model in models_to_preload:
        print(f"   Preloading {model}...")
        try:
            subprocess.run(["ollama", "run", model, "Hello"], 
                         capture_output=True, text=True, timeout=30)
            print(f"   ✅ {model} preloaded")
        except subprocess.TimeoutExpired:
            print(f"   ⚠️ {model} preload timeout (model may still be loading)")
        except Exception as e:
            print(f"   ❌ Failed to preload {model}: {e}")
    print()

def start_server():
    """Start the FastAPI server."""
    print("🌟 Starting Network Engineer AI Assistant server...")
    print("   Server will be available at: http://localhost:8000")
    print("   API docs at: http://localhost:8000/docs")
    print("   Use Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Import and run the main app
        import uvicorn
        from main import app
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

def main():
    """Main startup sequence."""
    print("🤖 Network Engineer AI Assistant - Optimized Startup")
    print("=" * 60)
    
    # Set performance environment variables
    set_performance_env()
    
    # Check if Ollama is running
    if not check_ollama_running():
        print("❌ Ollama is not running!")
        print("Please start Ollama first:")
        print("   Windows: Start Ollama from the system tray")
        print("   Linux/Mac: ollama serve")
        sys.exit(1)
    
    print("✅ Ollama is running")
    
    # Check if required models are available
    if not check_models_available():
        print("❌ Required models are missing. Please install them first.")
        sys.exit(1)
    
    # Preload models for faster startup
    preload_models()
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main() 