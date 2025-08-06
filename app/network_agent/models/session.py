"""Network agent session models."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class AgentSession(Base):
    """Model for network agent chat sessions."""
    
    __tablename__ = "agent_sessions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Session configuration
    session_type = Column(String(50), default="network", nullable=False)  # 'network' or 'general'
    session_name = Column(String(255), nullable=True)
    
    # Session metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    commands = relationship("CommandHistory", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentSession {self.id}: {self.session_type} for user {self.user_id}>"
    
    @property
    def is_active(self) -> bool:
        """Check if session has recent activity (within last hour)."""
        return (datetime.utcnow() - self.last_activity).total_seconds() < 3600


class DeviceInfo(Base):
    """Model for storing discovered network devices."""
    
    __tablename__ = "network_devices"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Device identification
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(100), nullable=True)  # router, switch, firewall, etc.
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    hostname = Column(String(255), nullable=True)
    
    # Device status
    is_reachable = Column(String(50), default="unknown", nullable=False)  # reachable, unreachable, unknown
    last_seen = Column(DateTime, nullable=True)
    
    # Device metadata
    os_type = Column(String(100), nullable=True)  # ios, iosxe, nxos, etc.
    model = Column(String(255), nullable=True)
    serial_number = Column(String(255), nullable=True)
    
    # Discovery metadata
    discovered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    command_history = relationship("CommandHistory", back_populates="device")
    
    def __repr__(self):
        return f"<DeviceInfo {self.device_name} ({self.ip_address})>"