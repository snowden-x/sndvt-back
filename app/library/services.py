"""Library service for managing documentation uploads and deletions."""

import os
import shutil
import time
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from app.config import get_settings
from app.ai_assistant.services.knowledge_service import KnowledgeService
from .models import DocumentInfo, LibraryStatus, RebuildResponse


class LibraryService:
    """Service for managing the documentation library."""
    
    def __init__(self):
        self.settings = get_settings()
        self.docs_dir = Path(self.settings.docs_dir)
        self.knowledge_service = KnowledgeService()
        
        # Ensure docs directory exists
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize knowledge service if not already initialized
        if not self.knowledge_service.vectorstore:
            self.knowledge_service.create_or_load_knowledge_base()
        
    def get_document_info(self, filename: str) -> Optional[DocumentInfo]:
        """Get information about a specific document."""
        file_path = self.docs_dir / filename
        
        if not file_path.exists():
            return None
            
        stat = file_path.stat()
        
        return DocumentInfo(
            filename=filename,
            file_size=stat.st_size,
            file_type=self._get_file_type(filename),
            upload_date=datetime.fromtimestamp(stat.st_ctime),
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            is_processed=self._is_document_processed(filename),
            chunk_count=self._get_chunk_count(filename)
        )
        
    def list_documents(self) -> List[DocumentInfo]:
        """List all documents in the library."""
        documents = []
        
        for file_path in self.docs_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                doc_info = self.get_document_info(file_path.name)
                if doc_info:
                    documents.append(doc_info)
                    
        return sorted(documents, key=lambda x: x.upload_date, reverse=True)
        
    def upload_document(self, file_content: bytes, filename: str) -> DocumentInfo:
        """Upload a document to the library and add it to the knowledge base."""
        # Validate filename
        if not self._is_valid_filename(filename):
            raise ValueError(f"Invalid filename: {filename}")
            
        # Check if file already exists
        file_path = self.docs_dir / filename
        if file_path.exists():
            raise FileExistsError(f"Document {filename} already exists")
            
        # Write file
        with open(file_path, 'wb') as f:
            f.write(file_content)
            
        # Add document to knowledge base
        try:
            print(f"📄 Adding document '{filename}' to knowledge base...")
            knowledge_added = self.knowledge_service.add_document_to_knowledge_base(str(file_path), filename)
            
            if not knowledge_added:
                print(f"⚠️ Warning: Failed to add document '{filename}' to knowledge base")
                # Continue even if knowledge base addition fails
        except Exception as e:
            print(f"⚠️ Warning: Error adding document '{filename}' to knowledge base: {e}")
            # Continue even if knowledge base addition fails
            
        # Get document info
        doc_info = self.get_document_info(filename)
        if not doc_info:
            raise RuntimeError(f"Failed to get document info for {filename}")
            
        return doc_info
        
    def delete_document(self, filename: str) -> bool:
        """Delete a document from the library and its embeddings from the knowledge base."""
        file_path = self.docs_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document {filename} not found")
        
        try:
            # First, delete the document from the knowledge base
            print(f"🗑️ Deleting document '{filename}' from knowledge base...")
            knowledge_deleted = self.knowledge_service.delete_document_from_knowledge_base(filename)
            
            if not knowledge_deleted:
                print(f"⚠️ Warning: Failed to delete document '{filename}' from knowledge base")
                # Continue with file deletion even if knowledge base deletion fails
            
            # Then remove the file from disk
            file_path.unlink()
            print(f"✅ Successfully deleted document '{filename}' from library")
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting document '{filename}': {e}")
            raise
        
    def get_library_status(self) -> LibraryStatus:
        """Get overall library status."""
        documents = self.list_documents()
        
        total_size = sum(doc.file_size for doc in documents)
        processed_count = sum(1 for doc in documents if doc.is_processed)
        unprocessed_count = len(documents) - processed_count
        
        # Check vector store status
        vector_store_status = "Unknown"
        if os.path.exists(self.settings.persist_dir):
            vector_store_status = "Available"
        else:
            vector_store_status = "Not initialized"
            
        return LibraryStatus(
            total_documents=len(documents),
            total_size_bytes=total_size,
            processed_documents=processed_count,
            unprocessed_documents=unprocessed_count,
            vector_store_status=vector_store_status,
            last_rebuild=self._get_last_rebuild_time()
        )
        
    def rebuild_knowledge_base(self) -> RebuildResponse:
        """Rebuild the knowledge base from all documents."""
        start_time = time.time()
        
        try:
            # Get current documents
            documents = self.list_documents()
            
            if not documents:
                return RebuildResponse(
                    success=True,
                    message="No documents to process",
                    documents_processed=0,
                    chunks_created=0,
                    processing_time_seconds=time.time() - start_time
                )
                
            # Rebuild knowledge base
            vectorstore = self.knowledge_service.create_or_load_knowledge_base()
            
            if not vectorstore:
                return RebuildResponse(
                    success=False,
                    message="Failed to create knowledge base",
                    documents_processed=0,
                    chunks_created=0,
                    processing_time_seconds=time.time() - start_time,
                    error="No documents could be processed"
                )
                
            # Get chunk count (approximate)
            chunk_count = self._estimate_chunk_count(documents)
            
            processing_time = time.time() - start_time
            
            return RebuildResponse(
                success=True,
                message=f"Knowledge base rebuilt successfully with {len(documents)} documents",
                documents_processed=len(documents),
                chunks_created=chunk_count,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            return RebuildResponse(
                success=False,
                message="Failed to rebuild knowledge base",
                documents_processed=0,
                chunks_created=0,
                processing_time_seconds=time.time() - start_time,
                error=str(e)
            )
            
    def clear_knowledge_base(self) -> bool:
        """Clear the entire knowledge base."""
        try:
            print("🗑️ Clearing knowledge base...")
            success = self.knowledge_service.clear_knowledge_base()
            
            if success:
                print("✅ Successfully cleared knowledge base")
            else:
                print("❌ Failed to clear knowledge base")
                
            return success
            
        except Exception as e:
            print(f"❌ Error clearing knowledge base: {e}")
            return False
            
    def _is_valid_filename(self, filename: str) -> bool:
        """Check if filename is valid."""
        # Basic validation - no path traversal, no special characters
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
            
        # Check file extension
        valid_extensions = {'.txt', '.md', '.pdf', '.doc', '.docx'}
        file_ext = Path(filename).suffix.lower()
        
        return file_ext in valid_extensions
        
    def _get_file_type(self, filename: str) -> str:
        """Get the file type based on extension."""
        ext = Path(filename).suffix.lower()
        type_map = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        return type_map.get(ext, 'application/octet-stream')
        
    def _is_document_processed(self, filename: str) -> bool:
        """Check if document is processed in vector store."""
        try:
            chunk_count = self.knowledge_service.get_document_chunks_count(filename)
            return chunk_count > 0
        except Exception as e:
            print(f"Error checking if document {filename} is processed: {e}")
            return False
        
    def _get_chunk_count(self, filename: str) -> Optional[int]:
        """Get the number of chunks for a document."""
        try:
            return self.knowledge_service.get_document_chunks_count(filename)
        except Exception as e:
            print(f"Error getting chunk count for {filename}: {e}")
            return None
        
    def _get_last_rebuild_time(self) -> Optional[datetime]:
        """Get the last rebuild time."""
        # This could be stored in a metadata file
        # For now, return None
        return None
        
    def _estimate_chunk_count(self, documents: List[DocumentInfo]) -> int:
        """Estimate the total chunk count."""
        # Rough estimation: 1000 chars per chunk
        total_chars = sum(doc.file_size for doc in documents)
        return max(1, total_chars // 1000)
