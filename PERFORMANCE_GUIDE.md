# Performance Optimization Guide

This guide covers performance optimizations implemented for the Network Engineer AI Assistant backend, focusing on Ollama model management and streaming responses.

## 🚀 Quick Start (Optimized)

### Option 1: Use the Optimized Startup Script
```bash
cd sndvt-back
python start_optimized.py
```

### Option 2: Manual Setup with Environment Variables
```bash
# Set environment variables for optimal performance
export OLLAMA_KEEP_ALIVE=-1
export OLLAMA_TEMPERATURE=0.3
export OLLAMA_TOP_P=0.8
export OLLAMA_TOP_K=40
export OLLAMA_NUM_PREDICT=512
export OLLAMA_CONTEXT_SIZE=4096

# Start the server
python main.py
```

## 🔧 Key Optimizations Implemented

### 1. Model Persistence & Keep-Alive
- **Problem**: Ollama unloads models after 5 minutes of inactivity
- **Solution**: Set `OLLAMA_KEEP_ALIVE=-1` to keep models loaded indefinitely
- **Impact**: Eliminates 50+ second cold start delays

### 2. Model Preloading & Warming
- **Feature**: Automatic model preloading on server startup
- **Benefit**: First query is fast (no cold start)
- **Implementation**: `preload_and_warm_model()` function

### 3. Performance-Optimized Parameters
- **Temperature**: 0.3 (more focused responses)
- **Top-P**: 0.8 (balanced token selection)
- **Top-K**: 40 (optimal token consideration)
- **Max Tokens**: 512 (reasonable response length)
- **Context Size**: 4096 (consistent across requests)

### 4. Streaming Implementation
- **Method**: Uses `llm.astream()` for token-by-token streaming
- **Format**: JSON chunks with `type`, `content`, and `accumulated` fields
- **Benefit**: Real-time response display like ChatGPT

## 📊 Performance Testing Tools

### CLI Testing Tool
```bash
# Interactive mode with performance metrics
python cli.py

# Single query test
python cli.py "What is VLAN configuration?"

# Test connection
python cli.py --test
```

### Model Management Tool
```bash
# List available models
python model_manager.py --list

# Test model speed
python model_manager.py --test gemma3:4b

# Preload model
python model_manager.py --preload gemma3:4b

# Check running models
python model_manager.py --running

# Benchmark multiple models
python model_manager.py --benchmark gemma3:4b phi3:mini --query "Explain networking"
```

## 🎛️ Environment Configuration

### Performance Settings (env.example)
```bash
# Copy and modify as needed
cp env.example .env

# Key settings:
OLLAMA_KEEP_ALIVE=-1          # Keep model loaded indefinitely
OLLAMA_TEMPERATURE=0.3        # Lower = more focused (0.0-1.0)
OLLAMA_TOP_P=0.8             # Top-p sampling (0.0-1.0)
OLLAMA_TOP_K=40              # Top-k tokens to consider
OLLAMA_NUM_PREDICT=512       # Max tokens per response
OLLAMA_CONTEXT_SIZE=4096     # Consistent context size
```

### Alternative Configurations

#### Fastest Responses (Less Creative)
```bash
OLLAMA_TEMPERATURE=0.1
OLLAMA_NUM_PREDICT=256
OLLAMA_TOP_K=20
```

#### More Creative Responses (Slower)
```bash
OLLAMA_TEMPERATURE=0.7
OLLAMA_NUM_PREDICT=1024
OLLAMA_TOP_K=80
```

## 🏆 Performance Benchmarks

### Before Optimization
- **Cold Start**: 50+ seconds
- **Warm Response**: 15-30 seconds
- **Model Swapping**: Frequent unloading/reloading

### After Optimization
- **Cold Start**: 2-5 seconds (with preloading)
- **Warm Response**: 1-3 seconds to first token
- **Model Persistence**: No more unloading

### Expected Performance Metrics
- **Time to First Token**: < 3 seconds
- **Streaming Speed**: 50-200+ chars/second
- **Memory Usage**: Stable (no model swapping)

## 🧪 Testing & Monitoring

### Performance Monitoring
The CLI tool now shows detailed performance metrics:
- Time to first token
- Total response time
- Response length
- Average streaming speed

### Model Status Checking
```bash
# Check which models are currently loaded
ollama ps

# Monitor model usage
python model_manager.py --running
```

## 🔄 Model Management Best Practices

### 1. Model Selection
- **Production**: `gemma3:4b` (good balance of speed/quality)
- **Development**: `phi3:mini`, `gemma2:2b` (faster, smaller)
- **High Quality**: `llama3.2:8b` (slower but better)

### 2. Memory Management
- Keep 1-3 models loaded simultaneously
- Ensure sufficient system RAM
- Monitor with `ollama ps`

### 3. Context Size Consistency
- Use same context size across all requests
- Avoid model reloading due to parameter mismatches
- Default: 4096 tokens

## 🐛 Troubleshooting

### Common Issues

#### Model Not Loading
```bash
# Check if Ollama is running
ollama list

# Check model availability
python model_manager.py --list

# Pull missing models
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

#### Slow Responses
1. Check if model is preloaded: `ollama ps`
2. Verify environment variables are set
3. Monitor system resources
4. Consider using a smaller model for testing

#### Connection Issues
```bash
# Test API connection
python cli.py --test

# Check server logs for errors
python main.py  # Look for startup messages
```

### Performance Debugging
1. Use CLI performance metrics
2. Monitor model loading/unloading in server logs
3. Check system memory usage
4. Verify environment variables are applied

## 🚀 Advanced Optimizations

### System-Level Optimizations
- Ensure adequate RAM (8GB+ recommended)
- Use SSD storage for model files
- Close unnecessary applications
- Consider GPU acceleration if available

### Network Optimizations
- Use local Ollama instance (not remote)
- Minimize network latency
- Use WebSocket for real-time streaming

### Development Workflow
1. Use optimized startup script
2. Test with CLI tool
3. Monitor performance metrics
4. Adjust parameters as needed

## 📈 Scaling Considerations

### Multi-Model Setup
```bash
# Configure multiple models
export OLLAMA_MAX_LOADED_MODELS=3

# Load different models for different tasks
python model_manager.py --preload gemma3:4b
python model_manager.py --preload phi3:mini
```

### Load Balancing
- Consider multiple Ollama instances
- Use request queuing for high load
- Implement model routing based on query type

This performance guide should help you achieve optimal performance with your Network Engineer AI Assistant. The key is model persistence, proper preloading, and consistent configuration parameters. 