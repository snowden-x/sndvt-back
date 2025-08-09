"""Knowledge base management service."""

import os
from typing import Optional, List
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
                
                loaded_docs = loader.load()
                # Ensure each document has the filename in metadata
                for doc in loaded_docs:
                    if 'source' not in doc.metadata:
                        doc.metadata['source'] = filename
                    doc.metadata['filename'] = filename
                
                documents.extend(loaded_docs)
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
    
    def delete_document_from_knowledge_base(self, filename: str) -> bool:
        """
        Delete all embeddings for a specific document from the knowledge base.
        
        Args:
            filename: The name of the file to delete from the knowledge base
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.vectorstore:
            print("Warning: No vector store available")
            return False
        
        try:
            print(f"🗑️ Deleting document '{filename}' from knowledge base...")
            
            # Get all documents with the specified filename
            results = self.vectorstore.get(
                where={"filename": filename}
            )
            
            if not results['ids']:
                print(f"⚠️ No embeddings found for document '{filename}'")
                return True  # Consider this a success since there's nothing to delete
            
            # Delete the embeddings
            deleted_count = len(results['ids'])
            self.vectorstore.delete(ids=results['ids'])
            
            print(f"✅ Successfully deleted {deleted_count} embeddings for document '{filename}'")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting document '{filename}' from knowledge base: {e}")
            return False
    
    def add_document_to_knowledge_base(self, filepath: str, filename: str) -> bool:
        """
        Add a single document to the knowledge base.
        
        Args:
            filepath: Full path to the document file
            filename: Name of the file
            
        Returns:
            bool: True if addition was successful, False otherwise
        """
        if not self.vectorstore:
            print("Warning: No vector store available")
            return False
        
        try:
            print(f"📄 Adding document '{filename}' to knowledge base...")
            
            # Load the document
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(filepath)
            else:  # Assume .txt, .md, etc.
                loader = TextLoader(filepath, encoding='utf-8')
            
            documents = loader.load()
            
            # Ensure each document has the filename in metadata
            for doc in documents:
                if 'source' not in doc.metadata:
                    doc.metadata['source'] = filename
                doc.metadata['filename'] = filename
            
            # Split the document into chunks
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            texts = text_splitter.split_documents(documents)
            
            # Add to vector store
            self.vectorstore.add_documents(texts)
            
            print(f"✅ Successfully added {len(texts)} chunks for document '{filename}'")
            return True
            
        except Exception as e:
            print(f"❌ Error adding document '{filename}' to knowledge base: {e}")
            return False
    
    def get_document_chunks_count(self, filename: str) -> int:
        """
        Get the number of chunks for a specific document.
        
        Args:
            filename: The name of the file
            
        Returns:
            int: Number of chunks for the document
        """
        if not self.vectorstore:
            return 0
        
        try:
            results = self.vectorstore.get(
                where={"filename": filename}
            )
            return len(results['ids'])
        except Exception as e:
            print(f"Error getting chunk count for document '{filename}': {e}")
            return 0
    
    def list_documents_in_knowledge_base(self) -> List[str]:
        """
        Get a list of all documents in the knowledge base.
        
        Returns:
            List[str]: List of document filenames
        """
        if not self.vectorstore:
            return []
        
        try:
            # Get all documents
            results = self.vectorstore.get()
            
            # Extract unique filenames from metadata
            filenames = set()
            for metadata in results['metadatas']:
                if metadata and 'filename' in metadata:
                    filenames.add(metadata['filename'])
            
            return list(filenames)
        except Exception as e:
            print(f"Error listing documents in knowledge base: {e}")
            return [] 

    def clear_knowledge_base(self) -> bool:
        """
        Clear all documents from the knowledge base.
        
        Returns:
            bool: True if clearing was successful, False otherwise
        """
        if not self.vectorstore:
            print("Warning: No vector store available")
            return False
        
        try:
            print("🗑️ Clearing entire knowledge base...")
            
            # Get all documents
            results = self.vectorstore.get()
            
            if not results['ids']:
                print("ℹ️ Knowledge base is already empty")
                return True
            
            # Delete all embeddings
            deleted_count = len(results['ids'])
            self.vectorstore.delete(ids=results['ids'])
            
            print(f"✅ Successfully cleared {deleted_count} embeddings from knowledge base")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing knowledge base: {e}")
            return False 