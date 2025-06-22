"""Knowledge base management service."""

import os
from typing import Optional
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_chroma import Chroma
from langchain_text_splitters import CharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

from app.config import get_settings


class KnowledgeService:
    """Service for managing the knowledge base and vector store."""
    
    def __init__(self):
        self.settings = get_settings()
        self.vectorstore: Optional[Chroma] = None
        
    def create_or_load_knowledge_base(self) -> Optional[Chroma]:
        """
        Loads documents, creates embeddings, and initializes a Chroma vector store.
        If the vector store already exists, it loads it from disk.
        """
        print("--- Initializing Knowledge Base ---")
        
        # Initialize embeddings with the embedding-specific model
        embeddings = OllamaEmbeddings(model=self.settings.ollama_embedding_model)
        
        if os.path.exists(self.settings.persist_dir):
            print("Loading existing knowledge base...")
            self.vectorstore = Chroma(persist_directory=self.settings.persist_dir, embedding_function=embeddings)
            print("--- Knowledge base loaded successfully! ---")
            return self.vectorstore
        
        print("Creating new knowledge base...")
        if not os.path.exists(self.settings.docs_dir):
            print("Warning: No documents directory found. The assistant will rely on general knowledge only.")
            return None

        documents = []
        for filename in os.listdir(self.settings.docs_dir):
            filepath = os.path.join(self.settings.docs_dir, filename)
            if not os.path.isfile(filepath):
                continue
            
            try:
                if filename.endswith(".pdf"):
                    loader = PyPDFLoader(filepath)
                else:  # Assume .txt, .md, etc.
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
        self.vectorstore = Chroma.from_documents(
            documents=texts, 
            embedding=embeddings, 
            persist_directory=self.settings.persist_dir
        )
        print("--- Knowledge base created successfully! ---")
        return self.vectorstore
        
    def get_vectorstore(self) -> Optional[Chroma]:
        """Get the current vector store."""
        return self.vectorstore 