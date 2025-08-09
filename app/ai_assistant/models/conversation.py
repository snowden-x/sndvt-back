"""Conversation and message models for chat persistence."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.config.database import Base


class Conversation(Base):
    """Model for chat conversations."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, default="New Conversation")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Relationship to messages
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    # Relationship to user
    user = relationship("User")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', user_id={self.user_id})>"


class ConversationMessage(Base):
    """Model for individual messages within conversations."""
    
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_type = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # Store sources as JSON array
    message_metadata = Column(JSON, nullable=True)  # Store additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<ConversationMessage(id={self.id}, type='{self.message_type}', conversation_id={self.conversation_id})>"
