# Network Engineer AI Assistant

An intelligent assistant for network engineers that combines document-based knowledge with real-time device monitoring. Built with FastAPI, LangChain, and Ollama using a modern modular architecture.

## Features

- 🤖 Interactive CLI interface
- 📚 Document-based knowledge integration
- 🔄 Real-time streaming responses
- 💡 Clear indication of knowledge sources (documentation vs. general knowledge)
- 📝 Support for various document formats (TXT, PDF)
- 🔍 Semantic search capabilities
- 💻 Network engineering expertise
- 📡 Real-time device monitoring (SNMP, SSH, REST)
- 🌐 Network discovery capabilities
- 📊 Device health metrics and interface monitoring

## Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running
- Required models pulled in Ollama:
  - `gemma3:4b` (for text generation)
  - `nomic-embed-text` (for embeddings)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/snowden-x/sndvt-back
   cd sndvt-back
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Pull required Ollama models:
   ```bash
   ollama pull gemma3:4b
   ollama pull nomic-embed-text
   ```

## Directory Structure

```
sndvt-back/
├── app/                           # Main application package
│   ├── main.py                    # FastAPI app initialization
│   ├── config/                    # Configuration management
│   │   └── settings.py            # Centralized settings
│   ├── ai_assistant/              # AI chat assistant module
│   │   ├── api/chat.py           # Chat API endpoints
│   │   ├── models/chat.py        # Pydantic models
│   │   └── services/             # Business logic
│   │       ├── knowledge_service.py  # Knowledge base management
│   │       ├── model_service.py      # AI model management
│   │       └── chat_service.py       # Chat logic
│   ├── device_monitoring/         # Device monitoring module
│   │   ├── api/api.py            # Device monitoring endpoints
│   │   ├── services/             # Monitoring services
│   │   ├── clients/              # SNMP/SSH/REST clients
│   │   └── utils/                # Base classes and utilities
│   └── shared/                    # Shared utilities
├── scripts/                       # Standalone scripts
│   ├── cli.py                    # Interactive CLI interface
│   ├── setup_device.py          # Device setup wizard
│   └── discover_network.py      # Network discovery tool
├── config/                        # Configuration files
│   └── device_configs/           # Device configurations
│       └── devices.yaml
├── data/                          # Data directories
│   ├── network_docs/             # Network documentation
│   └── chroma_db/               # Vector store persistence
├── tests/                         # Test files
├── docs/                          # Documentation
├── start_optimized.py            # Optimized startup script
└── requirements.txt              # Project dependencies
```

## Configuration

The application uses centralized configuration in `app/config/settings.py`. You can customize settings via environment variables or a `.env` file:

```bash
# AI Assistant Configuration
DOCS_DIR=data/network_docs
PERSIST_DIR=data/chroma_db
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=gemma3:4b

# Performance Settings
OLLAMA_KEEP_ALIVE=-1
OLLAMA_TEMPERATURE=0.3
OLLAMA_TOP_P=0.8
OLLAMA_TOP_K=40
OLLAMA_NUM_PREDICT=512
OLLAMA_CONTEXT_SIZE=4096

# Server Settings
HOST=0.0.0.0
PORT=8000
```

## Adding Documentation

1. Add your network documentation files to the `data/network_docs/` directory. Supported formats:
   - Text files (.txt)
   - PDF files (.pdf)
   - Markdown files (.md)

The system will automatically process and index these documents on startup.

## Device Configuration

1. Configure your network devices in `config/device_configs/devices.yaml`:
   ```yaml
   global_settings:
     default_timeout: 10
     default_retry_count: 3
     cache_ttl: 300
     max_concurrent_queries: 10

   devices:
     router1:
       name: "Main Router"
       host: "192.168.1.1"
       device_type: "router"
       enabled_protocols: ["snmp", "ssh"]
       credentials:
         snmp_community: "public"
         username: "admin"
         # Use environment variables for sensitive data
   ```

## Running the System

### Option 1: Optimized Startup (Recommended)
```bash
python start_optimized.py
```
This script:
- Sets optimal performance environment variables
- Checks Ollama availability and models
- Preloads models for faster responses
- Starts the server with proper configuration

### Option 2: Direct Startup
```bash
python -m app.main
```

### Option 3: Development Mode
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at:
- **Main API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Interactive API**: http://localhost:8000/redoc

### Using the CLI
```bash
python scripts/cli.py
```

## API Endpoints

### AI Assistant
- `POST /ask` - Ask the AI assistant with streaming response
- `WebSocket /ws` - Real-time chat via WebSocket

### Device Monitoring
- `GET /devices/` - List all configured devices
- `GET /devices/{device_id}/status` - Get device status
- `GET /devices/{device_id}/interfaces` - Get device interfaces
- `GET /devices/{device_id}/health` - Get device health metrics
- `POST /devices/{device_id}/ping` - Ping a device
- `GET /devices/status/all` - Get status for all devices

### Network Discovery
- `GET /devices/discovery/{subnet}` - Discover devices in subnet

## Response Format

The AI assistant clearly indicates the source of information:
- 📚 "Response based on documentation and general knowledge"
- 🧠 "Response based on general network engineering knowledge"

When documentation is used, relevant sources are cited with previews.

## Development

### Adding New Features

- **AI Assistant features**: Work in `app/ai_assistant/`
- **Device monitoring features**: Work in `app/device_monitoring/`
- **Shared utilities**: Add to `app/shared/`
- **Configuration changes**: Modify `app/config/settings.py`

### Running Tests
```bash
python -m pytest tests/
```

## Troubleshooting

1. **Ollama Connection Issues**
   - Ensure Ollama is running: `ollama serve`
   - Check if models are pulled: `ollama list`
   - Verify models: `gemma3:4b` and `nomic-embed-text`

2. **Import Errors**
   - Ensure you're running from the project root directory
   - Check that all dependencies are installed: `pip install -r requirements.txt`

3. **Device Monitoring Issues**
   - Verify device configurations in `config/device_configs/devices.yaml`
   - Check network connectivity to devices
   - Ensure proper credentials are set

4. **Performance Issues**
   - Use `start_optimized.py` for optimal performance settings
   - Consider adjusting `OLLAMA_KEEP_ALIVE` and other performance variables

## Architecture

The application follows a modular architecture with clear separation of concerns:

- **Configuration Layer**: Centralized settings management
- **AI Assistant Module**: Knowledge base and chat functionality
- **Device Monitoring Module**: Network device monitoring and management
- **API Layer**: RESTful endpoints and WebSocket support
- **Service Layer**: Business logic and external integrations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the modular architecture patterns
4. Add tests for new functionality
5. Update documentation
6. Create a Pull Request

## License

[Insert License Information] 
