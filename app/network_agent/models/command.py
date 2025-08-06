"""Network agent command history models."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class CommandHistory(Base):
    """Model for storing network agent command history."""
    
    __tablename__ = "command_history"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Session and user information
    session_id = Column(PostgresUUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Command information
    user_query = Column(Text, nullable=False)
    command_type = Column(String(50), nullable=False)  # 'natural_language', 'direct_command', 'device_discovery'
    
    # Device information (if applicable)
    device_id = Column(PostgresUUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=True)
    device_name = Column(String(255), nullable=True)  # Fallback if device not in DB
    
    # Command execution details
    executed_command = Column(Text, nullable=True)  # Actual command executed
    execution_status = Column(String(50), default="pending", nullable=False)  # pending, success, error, timeout
    
    # Response information
    agent_response = Column(Text, nullable=True)
    raw_output = Column(Text, nullable=True)  # Raw command output
    parsed_output = Column(Text, nullable=True)  # Parsed/formatted output
    
    # Performance metrics
    execution_time_ms = Column(Float, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("AgentSession", back_populates="commands")
    device = relationship("DeviceInfo", back_populates="command_history")
    
    def __repr__(self):
        return f"<CommandHistory {self.id}: {self.command_type} on {self.device_name}>"
    
    @property
    def was_successful(self) -> bool:
        """Check if command execution was successful."""
        return self.execution_status == "success"
    
    @property
    def total_time_ms(self) -> Optional[float]:
        """Get total time from execution to response."""
        if self.execution_time_ms and self.response_time_ms:
            return self.execution_time_ms + self.response_time_ms
        return None


class AgentConfig(Base):
    """Model for storing network agent configuration."""
    
    __tablename__ = "agent_config"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # None for global config
    
    # Agent behavior settings
    default_timeout = Column(Integer, default=30, nullable=False)  # seconds
    max_retries = Column(Integer, default=3, nullable=False)
    auto_suggest_commands = Column(String(10), default="true", nullable=False)  # true/false
    
    # Device connection settings
    connection_timeout = Column(Integer, default=10, nullable=False)  # seconds
    command_timeout = Column(Integer, default=30, nullable=False)  # seconds
    
    # Response formatting
    response_format = Column(String(50), default="formatted", nullable=False)  # raw, formatted, both
    include_debug_info = Column(String(10), default="false", nullable=False)  # true/false
    
    # History settings
    max_history_entries = Column(Integer, default=100, nullable=False)
    auto_cleanup_days = Column(Integer, default=30, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        user_type = "global" if self.user_id is None else f"user {self.user_id}"
        return f"<AgentConfig {self.id}: {user_type}>"