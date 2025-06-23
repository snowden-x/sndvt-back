"""Chat-related Pydantic models."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Model for a single chat message."""
    id: str
    text: str
    sender: str  # 'user' or 'ai'
    timestamp: Optional[str] = None


class QueryRequest(BaseModel):
    """Request model for a user query."""
    query: str
    conversation_history: Optional[List[ChatMessage]] = []


class WebSocketMessage(BaseModel):
    """Model for WebSocket messages."""
    query: str
    conversation_history: Optional[List[ChatMessage]] = []
    timestamp: Optional[str] = None


class StreamingEvent(BaseModel):
    """Model for streaming events."""
    event: str
    data: Dict[str, Any] 