"""Library-related Pydantic models."""

from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class DocumentInfo(BaseModel):
    """Model for document information."""
    filename: str
    file_size: int
    file_type: str
    upload_date: datetime
    last_modified: datetime
    is_processed: bool
    chunk_count: Optional[int] = None


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    success: bool
    message: str
    document_info: Optional[DocumentInfo] = None
    error: Optional[str] = None


class DocumentDeleteResponse(BaseModel):
    """Response model for document deletion."""
    success: bool
    message: str
    error: Optional[str] = None


class LibraryStatus(BaseModel):
    """Model for library status information."""
    total_documents: int
    total_size_bytes: int
    processed_documents: int
    unprocessed_documents: int
    vector_store_status: str
    last_rebuild: Optional[datetime] = None


class RebuildResponse(BaseModel):
    """Response model for knowledge base rebuild."""
    success: bool
    message: str
    documents_processed: int
    chunks_created: int
    processing_time_seconds: float
    error: Optional[str] = None
