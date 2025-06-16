import os
import uvicorn
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain.prompts import PromptTemplate
from typing import AsyncGenerator, Dict, Any
import asyncio

# --- Configuration ---
# Path to the directory containing network documentation
DOCS_DIR = "network_docs" 
# Directory to persist the ChromaDB vector store
PERSIST_DIR = "chroma_db"
# Name of the local Ollama models to use
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"  # This model specifically supports embeddings
OLLAMA_LLM_MODEL = "gemma3:4b-it-qat"  # This model for text generation

# Custom prompt template that combines documentation and general knowledge
CUSTOM_PROMPT = """You are an expert Network Engineer AI Assistant. You have access to both documentation and general networking knowledge.

If the question is about specific documentation, prioritize that information. Otherwise, use your general networking expertise to help.

Context from documentation (if relevant):
{context}

Question: {question}

Please provide a detailed, technical, and helpful response. If you're using general knowledge rather than documentation, make that clear.
If analyzing logs or technical output, break down the analysis step by step.

Answer:"""

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Network Engineer AI Assistant",
    description="An AI assistant for network engineers, powered by LangChain, Ollama, and ChromaDB.",
    version="1.0.0"
)

# Global variables
qa_chain = None
llm = None

# --- Pydantic Model for API Request ---
class QueryRequest(BaseModel):
    """Request model for a user query."""
    query: str

class StreamingEvent(BaseModel):
    """Model for streaming events."""
    event: str
    data: Dict[str, Any]

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

@app.on_event("startup")
async def startup_event():
    """
    Initializes all the necessary components for the AI assistant on app startup.
    """
    global qa_chain, llm
    print("--- Server starting up ---")
    
    try:
        vectorstore = create_or_load_knowledge_base()
        llm = Ollama(model=OLLAMA_LLM_MODEL)
        
        # Create custom prompt template
        prompt = PromptTemplate(
            template=CUSTOM_PROMPT,
            input_variables=["context", "question"]
        )
        
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
                retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
                return_source_documents=True,
                chain_type_kwargs={"prompt": qa_prompt}
            )
        else:
            # If no vectorstore, create a simple chain that just uses the LLM
            from langchain.chains import LLMChain
            qa_chain = LLMChain(
                llm=llm,
                prompt=PromptTemplate(
                    template="You are an expert Network Engineer AI Assistant. Please provide a detailed, technical, and helpful response to the following question:\n\nQuestion: {query}\n\nAnswer:",
                    input_variables=["query"]
                )
            )
            
        print("--- QA Chain is ready! ---")
    except Exception as e:
        print(f"FATAL: Failed to initialize QA chain: {e}")
        qa_chain = None

@app.post("/ask", summary="Ask the AI Assistant a question")
async def ask_question(request: QueryRequest):
    """
    Receives a query from the user and returns a streaming response from the AI assistant.
    The AI uses both documentation and general networking knowledge to formulate its answer.
    """
    if qa_chain is None:
        raise HTTPException(status_code=500, detail="QA chain is not initialized. Check server logs for errors.")
    
    print(f"Received query: {request.query}")
    
    async def generate_response():
        try:
            # Run the chain in a background task
            if isinstance(qa_chain, RetrievalQA):
                # Get relevant documents using the new invoke method
                docs = await qa_chain.retriever.ainvoke(request.query)
                sources = []
                for doc in docs:
                    source_info = {
                        "source": doc.metadata.get('source', 'Unknown'),
                        "content_preview": doc.page_content[:200] + "..."
                    }
                    if source_info not in sources:
                        sources.append(source_info)
                
                # Run the LLM with streaming
                context = "\n\n".join(doc.page_content for doc in docs)
                prompt_value = qa_chain.combine_documents_chain.llm_chain.prompt.format(
                    context=context,
                    question=request.query
                )
                
                async for token in llm.astream(prompt_value):
                    event = StreamingEvent(
                        event="chunk",
                        data={"text": token, "done": False}
                    )
                    yield f"data: {json.dumps(event.dict())}\n\n"
                
                # Send the final message with sources
                final_event = StreamingEvent(
                    event="done",
                    data={
                        "sources": sources,
                        "used_documentation": True,
                        "done": True
                    }
                )
                yield f"data: {json.dumps(final_event.dict())}\n\n"
            
            else:
                # Direct LLM chain
                # We can call the LLM directly for a consistent streaming experience
                prompt_value = qa_chain.prompt.format(query=request.query)
                async for token in llm.astream(prompt_value):
                    event = StreamingEvent(
                        event="chunk",
                        data={"text": token, "done": False}
                    )
                    yield f"data: {json.dumps(event.dict())}\n\n"
                
                # Send the final message
                final_event = StreamingEvent(
                    event="done",
                    data={
                        "sources": [],
                        "used_documentation": False,
                        "done": True
                    }
                )
                yield f"data: {json.dumps(final_event.dict())}\n\n"

        except Exception as e:
            print(f"Error during query processing: {e}")
            error_event = StreamingEvent(
                event="error",
                data={"error": str(e), "done": True}
            )
            yield f"data: {json.dumps(error_event.dict())}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )

# --- Main Execution Block ---
if __name__ == "__main__":
    # To run the API server:
    # 1. Make sure you have Ollama installed and running.
    # 2. Make sure you have pulled the model (e.g., `ollama pull gemma3:4b-it-qat`).
    # 3. Create a directory named 'network_docs' and add your documentation (.txt, .pdf).
    # 4. Run this script: `python your_script_name.py`
    # 5. The API will be available at http://127.0.0.1:8000
    # 6. You can access the interactive API docs at http://127.0.0.1:8000/docs
    uvicorn.run(app, host="0.0.0.0", port=8000)
