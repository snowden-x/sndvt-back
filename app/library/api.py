"""Library API endpoints."""

import os
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse

from app.core.dependencies import get_current_user
from app.auth.models.user import User
from .models import (
    DocumentInfo, 
    DocumentUploadResponse, 
    DocumentDeleteResponse,
    LibraryStatus,
    RebuildResponse
)
from .services import LibraryService

router = APIRouter(prefix="/library", tags=["Library"])

# Global service instance
library_service: LibraryService = None


def initialize_library_api():
    """Initialize the library API with required services."""
    global library_service
    library_service = LibraryService()


@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents(current_user: User = Depends(get_current_user)):
    """List all documents in the library."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        documents = library_service.list_documents()
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/documents/{filename}", response_model=DocumentInfo)
async def get_document_info(filename: str, current_user: User = Depends(get_current_user)):
    """Get information about a specific document."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        doc_info = library_service.get_document_info(filename)
        if not doc_info:
            raise HTTPException(status_code=404, detail=f"Document {filename} not found")
        return doc_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document info: {str(e)}")


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a document to the library."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file size (10MB limit)
        if len(file_content) > 10 * 1024 * 1024:
            return DocumentUploadResponse(
                success=False,
                message="File too large. Maximum size is 10MB.",
                error="File size exceeds limit"
            )
        
        # Upload document
        doc_info = library_service.upload_document(file_content, file.filename)
        
        return DocumentUploadResponse(
            success=True,
            message=f"Document {file.filename} uploaded successfully",
            document_info=doc_info
        )
        
    except FileExistsError as e:
        return DocumentUploadResponse(
            success=False,
            message=f"Document already exists: {file.filename}",
            error=str(e)
        )
    except ValueError as e:
        return DocumentUploadResponse(
            success=False,
            message=f"Invalid file: {file.filename}",
            error=str(e)
        )
    except Exception as e:
        return DocumentUploadResponse(
            success=False,
            message=f"Failed to upload document: {file.filename}",
            error=str(e)
        )


@router.delete("/documents/{filename}", response_model=DocumentDeleteResponse)
async def delete_document(filename: str, current_user: User = Depends(get_current_user)):
    """Delete a document from the library."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        library_service.delete_document(filename)
        return DocumentDeleteResponse(
            success=True,
            message=f"Document {filename} deleted successfully"
        )
    except FileNotFoundError as e:
        return DocumentDeleteResponse(
            success=False,
            message=f"Document not found: {filename}",
            error=str(e)
        )
    except Exception as e:
        return DocumentDeleteResponse(
            success=False,
            message=f"Failed to delete document: {filename}",
            error=str(e)
        )


@router.get("/documents/{filename}/download")
async def download_document(filename: str, current_user: User = Depends(get_current_user)):
    """Download a document from the library."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        # Check if file exists
        doc_info = library_service.get_document_info(filename)
        if not doc_info:
            raise HTTPException(status_code=404, detail=f"Document {filename} not found")
        
        # Return file
        file_path = library_service.docs_dir / filename
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=doc_info.file_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}")


@router.get("/status", response_model=LibraryStatus)
async def get_library_status(current_user: User = Depends(get_current_user)):
    """Get overall library status."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        status = library_service.get_library_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get library status: {str(e)}")


@router.post("/rebuild", response_model=RebuildResponse)
async def rebuild_knowledge_base(current_user: User = Depends(get_current_user)):
    """Rebuild the knowledge base from all documents."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        response = library_service.rebuild_knowledge_base()
        return response
    except Exception as e:
        return RebuildResponse(
            success=False,
            message="Failed to rebuild knowledge base",
            documents_processed=0,
            chunks_created=0,
            processing_time_seconds=0,
            error=str(e)
        )


@router.post("/clear", response_model=DocumentDeleteResponse)
async def clear_knowledge_base(current_user: User = Depends(get_current_user)):
    """Clear the entire knowledge base."""
    if library_service is None:
        raise HTTPException(status_code=500, detail="Library service not initialized")
    
    try:
        success = library_service.clear_knowledge_base()
        if success:
            return DocumentDeleteResponse(
                success=True,
                message="Knowledge base cleared successfully"
            )
        else:
            return DocumentDeleteResponse(
                success=False,
                message="Failed to clear knowledge base",
                error="Unknown error occurred"
            )
    except Exception as e:
        return DocumentDeleteResponse(
            success=False,
            message="Failed to clear knowledge base",
            error=str(e)
        )
