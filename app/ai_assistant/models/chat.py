"""Chat-related Pydantic models."""

from typing import Dict, Any
from pydantic import BaseModel


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