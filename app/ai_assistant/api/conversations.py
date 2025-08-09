"""API endpoints for managing chat conversations."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config.database import get_db
from app.auth.models.user import User
from app.core.dependencies import get_current_user
from ..models.conversation import Conversation, ConversationMessage
from ..models.chat import ChatMessage
from pydantic import BaseModel


router = APIRouter(prefix="/conversations", tags=["conversations"])


# Pydantic models for API
class ConversationCreate(BaseModel):
    title: str = "New Conversation"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None


class MessageCreate(BaseModel):
    message_type: str  # 'user', 'assistant', 'system'
    content: str
    sources: Optional[List[str]] = None
    message_metadata: Optional[dict] = None


class MessageResponse(BaseModel):
    id: int
    message_type: str
    content: str
    sources: Optional[List[str]] = None
    message_metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    message_count: int

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List conversations for the current user."""
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    
    if not include_archived:
        query = query.filter(Conversation.is_archived == False)
    
    conversations = query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit).all()
    
    # Add message count to each conversation
    result = []
    for conv in conversations:
        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            is_archived=conv.is_archived,
            message_count=len(conv.messages)
        ))
    
    return result


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation."""
    db_conversation = Conversation(
        title=conversation.title,
        user_id=current_user.id
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    return ConversationResponse(
        id=db_conversation.id,
        title=db_conversation.title,
        created_at=db_conversation.created_at,
        updated_at=db_conversation.updated_at,
        is_archived=db_conversation.is_archived,
        message_count=0
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific conversation with all messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_archived=conversation.is_archived,
        messages=[
                    MessageResponse(
            id=msg.id,
            message_type=msg.message_type,
            content=msg.content,
            sources=msg.sources,
            message_metadata=msg.message_metadata,
            created_at=msg.created_at
        ) for msg in conversation.messages
        ]
    )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if conversation_update.title is not None:
        conversation.title = conversation_update.title
    if conversation_update.is_archived is not None:
        conversation.is_archived = conversation_update.is_archived
    
    db.commit()
    db.refresh(conversation)
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_archived=conversation.is_archived,
        message_count=len(conversation.messages)
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message_to_conversation(
    conversation_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a message to a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    db_message = ConversationMessage(
        conversation_id=conversation_id,
        message_type=message.message_type,
        content=message.content,
        sources=message.sources,
        message_metadata=message.message_metadata
    )
    
    db.add(db_message)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_message)
    
    return MessageResponse(
        id=db_message.id,
        message_type=db_message.message_type,
        content=db_message.content,
        sources=db_message.sources,
        message_metadata=db_message.message_metadata,
        created_at=db_message.created_at
    )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages for a specific conversation."""
    # Verify user owns the conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id
    ).order_by(ConversationMessage.created_at).offset(skip).limit(limit).all()
    
    return [
        MessageResponse(
            id=msg.id,
            message_type=msg.message_type,
            content=msg.content,
            sources=msg.sources,
            message_metadata=msg.message_metadata,
            created_at=msg.created_at
        ) for msg in messages
    ]
