import os
import uvicorn
import json
import time
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from device_monitor.api import router as device_router
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM as Ollama
from langchain_text_splitters import CharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain.prompts import PromptTemplate
from typing import AsyncGenerator, Dict, Any
import asyncio
from contextlib import asynccontextmanager

# --- Configuration ---
# Path to the directory containing network documentation
DOCS_DIR = "network_docs" 
# Directory to persist the ChromaDB vector store
PERSIST_DIR = "chroma_db"
# Name of the local Ollama models to use
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"  # This model specifically supports embeddings
OLLAMA_LLM_MODEL = "gemma3:4b"  # This model for text generation

# Performance optimization settings
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "-1")  # Keep model loaded indefinitely
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))  # Lower for more focused responses
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.8"))  # Top-p sampling
OLLAMA_TOP_K = int(os.getenv("OLLAMA_TOP_K", "40"))  # Top-k sampling
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))  # Max tokens to generate
OLLAMA_CONTEXT_SIZE = int(os.getenv("OLLAMA_CONTEXT_SIZE", "4096"))  # Consistent context size

# Enhanced prompt template with better structure and efficiency
CUSTOM_PROMPT = """You are a Senior Network Engineer AI Assistant. Follow these guidelines for optimal responses:

RESPONSE STRUCTURE:
1. Give a direct, concise answer first
2. Provide technical details if needed
3. Include actionable steps when applicable

CONTEXT RULES:
- If documentation context is provided below, prioritize it over general knowledge
- If no relevant context, rely on your networking expertise
- Always indicate your information source

EFFICIENCY GUIDELINES:
- Be precise and avoid unnecessary verbosity
- Use bullet points for lists and steps
- Include specific commands, IPs, or configurations when relevant
- If analyzing logs/configs, highlight key findings first

DOCUMENTATION CONTEXT:
{context}

QUESTION: {question}

RESPONSE:"""

# Efficient prompt for general knowledge (no documentation context)
GENERAL_PROMPT = """You are a Senior Network Engineer AI Assistant. Provide expert networking guidance.

RESPONSE GUIDELINES:
- Give direct, actionable answers
- Use bullet points for clarity
- Include specific commands/configurations when relevant
- Be concise but comprehensive

QUESTION: {query}

RESPONSE:"""

# Global variables
qa_chain = None
llm = None

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    """Request model for a user query."""
    query: str

class WebSocketMessage(BaseModel):
    """Model for WebSocket messages."""
    query: str
    timestamp: str

class StreamingEvent(BaseModel):
    """Model for streaming events."""
    event: str
    data: Dict[str, Any]

async def preload_and_warm_model():
    """
    Preload the model and warm it up with a simple query to ensure it's ready.
    This eliminates cold start delays.
    """
    print("🔥 Preloading and warming up the model...")
    start_time = time.time()
    
    try:
        # Create a simple warm-up query
        warmup_query = "Hello, are you ready?"
        
        # Use the global LLM to warm up
        response = ""
        async for chunk in llm.astream(warmup_query):
            response += chunk
        
        elapsed = time.time() - start_time
        print(f"✅ Model warmed up successfully in {elapsed:.2f}s")
        print(f"🔥 Model is now ready and will stay loaded (keep_alive={OLLAMA_KEEP_ALIVE})")
        
        # Verify model is loaded
        import subprocess
        result = subprocess.run(["ollama", "ps"], capture_output=True, text=True)
        if result.returncode == 0 and OLLAMA_LLM_MODEL in result.stdout:
            print(f"✅ Confirmed: {OLLAMA_LLM_MODEL} is loaded in memory")
        else:
            print(f"⚠️ Warning: {OLLAMA_LLM_MODEL} not found in loaded models")
            print("   This may cause cold start delays on first request")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not warm up model: {e}")

def create_or_load_knowledge_base():
    """
    Loads documents, creates embeddings, and initializes a Chroma vector store.
    If the vector store already exists, it loads it from disk.
    """
    print("--- Initializing Knowledge Base ---")
    
    # Initialize embeddings with the embedding-specific model
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL)
    
    if os.path.exists(PERSIST_DIR):
        print("Loading existing knowledge base...")
        vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
        print("--- Knowledge base loaded successfully! ---")
        return vectorstore
    
    print("Creating new knowledge base...")
    if not os.path.exists(DOCS_DIR):
        print("Warning: No documents directory found. The assistant will rely on general knowledge only.")
        return None

    documents = []
    for filename in os.listdir(DOCS_DIR):
        filepath = os.path.join(DOCS_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        
        try:
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(filepath)
            else: # Assume .txt, .md, etc.
                loader = TextLoader(filepath, encoding='utf-8')
            
            documents.extend(loader.load())
            print(f"Loaded document: {filename}")
        except Exception as e:
            print(f"Warning: Error loading document {filename}: {e}")

    if not documents:
        print("Warning: No documents loaded. The assistant will rely on general knowledge only.")
        return None

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)
    print(f"Split documents into {len(texts)} chunks.")

    print("Creating vector store...")
    vectorstore = Chroma.from_documents(
        documents=texts, 
        embedding=embeddings, 
        persist_directory=PERSIST_DIR
    )
    print("--- Knowledge base created successfully! ---")
    return vectorstore

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initializes all the necessary components for the AI assistant on app startup.
    """
    global qa_chain, llm
    print("--- Server starting up ---")
    print(f"🚀 Performance Settings:")
    print(f"   Keep Alive: {OLLAMA_KEEP_ALIVE}")
    print(f"   Temperature: {OLLAMA_TEMPERATURE}")
    print(f"   Top-P: {OLLAMA_TOP_P}")
    print(f"   Top-K: {OLLAMA_TOP_K}")
    print(f"   Max Tokens: {OLLAMA_NUM_PREDICT}")
    print(f"   Context Size: {OLLAMA_CONTEXT_SIZE}")
    
    try:
        vectorstore = create_or_load_knowledge_base()
        
        # Initialize Ollama with performance optimizations
        print("🤖 Initializing Ollama with performance optimizations...")
        llm = Ollama(
            model=OLLAMA_LLM_MODEL,
            temperature=OLLAMA_TEMPERATURE,
            top_p=OLLAMA_TOP_P,
            top_k=OLLAMA_TOP_K,
            num_predict=OLLAMA_NUM_PREDICT,
            # Note: keep_alive is handled via environment variable OLLAMA_KEEP_ALIVE
            # which is set by the start_optimized.py script.
        )
        
        # Preload and warm up the model
        await preload_and_warm_model()
        
        # Initialize QA chain with custom prompt if vectorstore exists
        if vectorstore:
            # Create the prompt template
            qa_prompt = PromptTemplate(
                template=CUSTOM_PROMPT,
                input_variables=["context", "question"]
            )
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(search_kwargs={"k": 2}),
                return_source_documents=True,
                chain_type_kwargs={"prompt": qa_prompt}
            )
        else:
            # If no vectorstore, create a simple chain with optimized prompt
            from langchain.chains import LLMChain
            qa_chain = LLMChain(
                llm=llm,
                prompt=PromptTemplate(
                    template=GENERAL_PROMPT,
                    input_variables=["query"]
                )
            )
            
        print("--- QA Chain is ready! ---")
    except Exception as e:
        print(f"FATAL: Failed to initialize QA chain: {e}")
        qa_chain = None
    
    yield
    
    # Cleanup
    print("--- Server shutting down ---")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Network Engineer AI Assistant",
    description="An AI assistant for network engineers, powered by LangChain, Ollama, and ChromaDB with real-time device monitoring.",
    version="1.0.0",
    lifespan=lifespan
)

# Include device monitoring router
app.include_router(device_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def stream_query_response(query: str) -> AsyncGenerator[str, None]:
    """Stream the response from the LLM in real-time."""
    if qa_chain is None:
        yield json.dumps({"error": "QA chain is not initialized"})
        return
    
    # Preprocess query for better results
    query = query.strip()
    if not query:
        yield json.dumps({"error": "Empty query provided"})
        return
    
    # Limit query length to prevent issues
    MAX_QUERY_LENGTH = 500
    if len(query) > MAX_QUERY_LENGTH:
        query = query[:MAX_QUERY_LENGTH] + "..."
        print(f"⚠️ Query truncated to {MAX_QUERY_LENGTH} characters")
    
    print(f"🚀 Starting streaming response for: {query[:50]}...")
    stream_start_time = time.time()
    
    try:
        if isinstance(qa_chain, RetrievalQA):
            # For retrieval QA, we need to handle streaming differently
            print("📚 Using RetrievalQA with streaming")
            
            # Get relevant documents first (with timeout to prevent hanging)
            retrieval_start_time = time.time()
            retriever = qa_chain.retriever
            try:
                docs = await asyncio.wait_for(retriever.ainvoke(query), timeout=5.0)
                retrieval_end_time = time.time()
                print(f"⏱️ Document retrieval took: {retrieval_end_time - retrieval_start_time:.2f}s")
                print(f"📄 Retrieved {len(docs)} documents")
            except asyncio.TimeoutError:
                retrieval_end_time = time.time()
                print(f"⏱️ Document retrieval timed out after: {retrieval_end_time - retrieval_start_time:.2f}s")
                print("⚠️ Document retrieval timeout, using general knowledge")
                docs = []
            
            # Prepare context with smart truncation for performance
            MAX_CONTEXT_CHARS = 2500  # Max characters to stuff into the prompt
            context_parts = []
            total_chars = 0
            
            for doc in docs:
                if total_chars + len(doc.page_content) > MAX_CONTEXT_CHARS:
                    remaining_space = MAX_CONTEXT_CHARS - total_chars
                    if remaining_space > 100: # Only add if there's reasonable space
                        context_parts.append(doc.page_content[:remaining_space] + "...")
                    break
                
                context_parts.append(doc.page_content)
                total_chars += len(doc.page_content)

            # Handle empty context gracefully
            if context_parts:
                context = "\n\n".join(context_parts)
                prompt_text = CUSTOM_PROMPT.format(context=context, question=query)
                print(f"📝 Using documentation context ({total_chars} chars)")
            else:
                # Fallback to general knowledge prompt if no useful context
                prompt_text = GENERAL_PROMPT.format(query=query)
                print("🧠 Using general knowledge (no relevant documentation found)")
            
            # Stream the LLM response
            print("🔄 Starting LLM streaming...")
            llm_start_time = time.time()
            first_chunk_received = False
            accumulated_response = ""
            
            async for chunk in llm.astream(prompt_text):
                if not first_chunk_received:
                    first_chunk_time = time.time()
                    print(f"⏱️ Time to first token from LLM: {first_chunk_time - llm_start_time:.2f}s")
                    first_chunk_received = True

                accumulated_response += chunk
                yield json.dumps({
                    "type": "chunk",
                    "content": chunk,
                    "accumulated": accumulated_response
                })
            
            # Send final message with sources
            total_time = time.time() - stream_start_time
            print(f"⏱️ Total stream processing time: {total_time:.2f}s")
            yield json.dumps({
                "type": "complete",
                "content": accumulated_response,
                "sources": [doc.metadata.get('source', 'Unknown') for doc in docs],
                "used_documentation": len(docs) > 0,
                "context_size": total_chars if 'total_chars' in locals() else 0,
                "documents_used": len(docs)
            })
            
        else:
            # Direct LLM streaming
            print("🤖 Using direct LLM streaming")
            accumulated_response = ""
            
            async for chunk in qa_chain.llm.astream(f"Question: {query}\n\nAnswer:"):
                accumulated_response += chunk
                yield json.dumps({
                    "type": "chunk", 
                    "content": chunk,
                    "accumulated": accumulated_response
                })
            
            # Send completion
            yield json.dumps({
                "type": "complete",
                "content": accumulated_response,
                "sources": [],
                "used_documentation": False
            })
            
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
        yield json.dumps({
            "type": "error",
            "error": f"Error processing query: {str(e)}"
        })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming communication."""
    await websocket.accept()
    print("🔌 WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                query = message_data.get("query", "")
                
                if not query.strip():
                    await websocket.send_text(json.dumps({"error": "Empty query received"}))
                    continue
                
                print(f"📨 Processing WebSocket query: {query[:50]}...")
                
                # Stream the response
                async for response_chunk in stream_query_response(query):
                    await websocket.send_text(response_chunk)
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
                await websocket.send_text(json.dumps({"error": f"Error processing message: {str(e)}"}))
                
    except WebSocketDisconnect:
        print("🔌 WebSocket connection closed")
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.post("/ask", summary="Ask the AI Assistant a question with streaming")
async def ask_question(request: QueryRequest):
    """
    Streaming endpoint that returns real-time response chunks.
    """
    if qa_chain is None:
        raise HTTPException(status_code=500, detail="QA chain is not initialized. Check server logs for errors.")
    
    print(f"📨 Received HTTP streaming query: {request.query[:50]}...")
    
    async def generate_sse_response():
        try:
            async for response_chunk in stream_query_response(request.query):
                # Convert to SSE format
                yield f"data: {response_chunk}\n\n"
        except Exception as e:
            print(f"Error during HTTP streaming: {e}")
            error_response = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {error_response}\n\n"

    return StreamingResponse(
        generate_sse_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# --- Main Execution Block ---
if __name__ == "__main__":
    # To run the API server:
    # 1. Make sure you have Ollama installed and running.
    # 2. Make sure you have pulled the model (e.g., `ollama pull gemma3:4b`).
    # 3. Create a directory named 'network_docs' and add your documentation (.txt, .pdf).
    # 4. Run this script: `python main.py`
    # 5. The API will be available at http://127.0.0.1:8000
    # 6. You can access the interactive API docs at http://127.0.0.1:8000/docs
    uvicorn.run(app, host="0.0.0.0", port=8000)
