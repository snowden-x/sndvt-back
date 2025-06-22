# Network Engineer AI Assistant

An intelligent assistant for network engineers that combines document-based knowledge with general networking expertise. Built with FastAPI, LangChain, and Ollama.

## Features

- 🤖 Interactive CLI interface
- 📚 Document-based knowledge integration
- 🔄 Real-time streaming responses
- 💡 Clear indication of knowledge sources (documentation vs. general knowledge)
- 📝 Support for various document formats (TXT, PDF)
- 🔍 Semantic search capabilities
- 💻 Network engineering expertise

## Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running
- Required models pulled in Ollama:
  - gemma3:4b-it-qat (for text generation)
  - nomic-embed-text (for embeddings)

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
   ollama pull gemma3:4b-it-qat
   ollama pull nomic-embed-text
   ```

## Directory Structure

```
sndvt-back/
├── main.py           # FastAPI backend server
├── cli.py           # Interactive CLI interface
├── network_docs/    # Directory for network documentation
├── chroma_db/       # Vector store persistence directory
├── requirements.txt # Project dependencies
└── README.md        # This file
```

## Adding Documentation

1. Create a `network_docs` directory if it doesn't exist:
   ```bash
   mkdir network_docs
   ```

2. Add your network documentation files to this directory. Supported formats:
   - Text files (.txt)
   - PDF files (.pdf)
   - Markdown files (.md)

The system will automatically process and index these documents on startup.

## Running the System

1. Start the FastAPI backend server:
   ```bash
   fastapi dev main.py
   ```
   The server will run on http://localhost:8000

2. In a new terminal, start the interactive CLI:
   ```bash
   python cli.py
   ```

### CLI Commands

- Type your questions and press Enter
- Use `exit`, `quit`, or `q` to end the session
- Press Ctrl+C to interrupt the current response

## API Endpoints

- `POST /ask`
  - Accepts JSON body with a "query" field
  - Returns Server-Sent Events (SSE) stream
  - Example:
    ```bash
    curl -X POST http://localhost:8000/ask \
         -H "Content-Type: application/json" \
         -d '{"query": "What is VLAN tagging?"}'
    ```

## Response Format

The assistant clearly indicates the source of information:
- 📚 "Response based on documentation and general knowledge"
- 🧠 "Response based on general network engineering knowledge"

When documentation is used, relevant sources are cited with previews.

## Environment Variables (Optional)

You can customize the following settings:
- `DOCS_DIR`: Path to documentation directory (default: "network_docs")
- `PERSIST_DIR`: ChromaDB persistence directory (default: "chroma_db")
- `OLLAMA_EMBEDDING_MODEL`: Model for embeddings (default: "nomic-embed-text")
- `OLLAMA_LLM_MODEL`: Model for text generation (default: "gemma3:4b-it-qat")

## Troubleshooting

1. **Ollama Connection Issues**
   - Ensure Ollama is running: `ollama serve`
   - Check if models are pulled: `ollama list`

2. **Document Loading Issues**
   - Verify file permissions
   - Check file formats are supported
   - Ensure files are not corrupted

3. **Memory Issues**
   - Consider reducing chunk size in `main.py`
   - Limit the number of concurrent requests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Insert License Information] 
