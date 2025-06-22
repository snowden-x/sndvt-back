# Backend Codebase Reorganization Plan

## Current Issues
1. **Monolithic main.py** (472 lines) - Contains both device monitoring and chat assistant
2. **Mixed responsibilities** - Single file handling multiple concerns
3. **No clear separation** between device monitoring and AI chat features
4. **Long files** - Difficult to maintain and understand
5. **No modular structure** - Hard to extend or modify individual components

## Proposed New Structure

```
sndvt-back/
├── app/                           # Main application package
│   ├── __init__.py
│   ├── main.py                    # Slim FastAPI app initialization
│   ├── config/                    # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py            # App settings and environment variables
│   │   └── database.py            # Database configuration (if needed)
│   │
│   ├── core/                      # Core application logic
│   │   ├── __init__.py
│   │   ├── dependencies.py        # FastAPI dependencies
│   │   ├── middleware.py          # Custom middleware
│   │   └── exceptions.py          # Custom exception handlers
│   │
│   ├── device_monitoring/         # Device monitoring module
│   │   ├── __init__.py
│   │   ├── api/                   # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── devices.py         # Device CRUD endpoints
│   │   │   ├── monitoring.py      # Monitoring endpoints
│   │   │   ├── discovery.py       # Network discovery endpoints
│   │   │   └── cache.py           # Cache management endpoints
│   │   ├── models/                # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── device.py          # Device models
│   │   │   ├── interface.py       # Interface models
│   │   │   └── health.py          # Health models
│   │   ├── services/              # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── device_service.py  # Device management
│   │   │   ├── monitoring_service.py # Monitoring logic
│   │   │   ├── discovery_service.py  # Network discovery
│   │   │   └── cache_service.py   # Cache management
│   │   ├── clients/               # External service clients
│   │   │   ├── __init__.py
│   │   │   ├── snmp_client.py     # SNMP client
│   │   │   ├── ssh_client.py      # SSH client
│   │   │   └── rest_client.py     # REST API client
│   │   ├── utils/                 # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── config_loader.py   # Device config loading
│   │   │   └── validators.py      # Input validation
│   │   └── schemas/               # Database schemas (if needed)
│   │       ├── __init__.py
│   │       └── device.py
│   │
│   ├── ai_assistant/              # AI chat assistant module
│   │   ├── __init__.py
│   │   ├── api/                   # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # Chat endpoints
│   │   │   └── knowledge.py       # Knowledge base endpoints
│   │   ├── models/                # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # Chat models
│   │   │   └── knowledge.py       # Knowledge models
│   │   ├── services/              # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── chat_service.py    # Chat logic
│   │   │   ├── knowledge_service.py # Knowledge base
│   │   │   └── model_service.py   # AI model management
│   │   ├── utils/                 # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── document_loader.py # Document processing
│   │   │   ├── text_splitter.py   # Text chunking
│   │   │   └── prompts.py         # Prompt templates
│   │   └── clients/               # External service clients
│   │       ├── __init__.py
│   │       ├── ollama_client.py   # Ollama integration
│   │       └── chroma_client.py   # ChromaDB integration
│   │
│   └── shared/                    # Shared utilities
│       ├── __init__.py
│       ├── logging.py             # Logging configuration
│       ├── metrics.py             # Performance metrics
│       └── health.py              # Health check utilities
│
├── scripts/                       # Standalone scripts
│   ├── setup_device.py            # Device setup wizard
│   ├── discover_network.py        # Network discovery tool
│   └── cli.py                     # CLI tools
│
├── config/                        # Configuration files
│   ├── device_configs/
│   │   └── devices.yaml
│   └── ai_configs/
│       └── prompts.yaml
│
├── tests/                         # Test files
│   ├── __init__.py
│   ├── test_device_monitoring.py
│   ├── test_ai_assistant.py
│   └── conftest.py
│
├── docs/                          # Documentation
│   ├── DEVICE_MONITORING_GUIDE.md
│   ├── FRONTEND_TASKS.md
│   └── API_REFERENCE.md
│
├── data/                          # Data directories
│   ├── network_docs/              # Network documentation
│   └── chroma_db/                 # Vector database
│
├── requirements.txt
├── .env.example
├── main.py                        # Application entry point
└── README.md
```

## Migration Steps

### Step 1: Create Directory Structure
- Create new directory structure
- Move existing files to appropriate locations
- Update import statements

### Step 2: Break Down main.py
- Extract AI assistant logic to `app/ai_assistant/`
- Extract device monitoring setup to `app/device_monitoring/`
- Create slim main.py for app initialization

### Step 3: Modularize Device Monitoring
- Split large `device_monitor/api.py` into focused modules
- Separate business logic from API endpoints
- Create dedicated service classes

### Step 4: Modularize AI Assistant
- Extract knowledge base logic
- Separate chat functionality
- Create model management service

### Step 5: Create Shared Components
- Logging configuration
- Health checks
- Common utilities

### Step 6: Update Configuration
- Environment-based configuration
- Separate configs for different modules
- Configuration validation

## Benefits of New Structure

### 1. **Separation of Concerns**
- Device monitoring and AI assistant are completely separate
- Each module has clear responsibilities
- Easier to understand and maintain

### 2. **Scalability**
- Easy to add new features to specific modules
- Independent development of different components
- Better team collaboration

### 3. **Testability**
- Isolated components are easier to test
- Clear interfaces between modules
- Mock dependencies easily

### 4. **Maintainability**
- Smaller, focused files
- Clear file organization
- Easier debugging and troubleshooting

### 5. **Deployment Flexibility**
- Can deploy modules independently if needed
- Better resource allocation
- Easier monitoring and logging

## Implementation Priority

### High Priority (Week 1)
1. Create directory structure
2. Break down main.py
3. Separate device monitoring from AI assistant

### Medium Priority (Week 2)
4. Modularize device monitoring APIs
5. Extract AI assistant services
6. Create shared utilities

### Low Priority (Week 3)
7. Improve configuration management
8. Add comprehensive logging
9. Update documentation

This reorganization will make the codebase much more maintainable and allow for easier development of both the device monitoring system and the AI assistant features. 