"""Alert data models for network downtime prediction."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from app.config.database import Base


class Alert(Base):
    """Model for network downtime prediction alerts."""
    
    __tablename__ = "alerts"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Alert content from NetPredict
    timestamp = Column(DateTime, nullable=False)
    probability = Column(Float, nullable=False)
    prediction = Column(Integer, nullable=False)
    cause = Column(String(255), nullable=False)
    device = Column(String(255), nullable=False)
    interface = Column(String(100), nullable=True)
    severity = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    
    # Alert management
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(PostgresUUID(as_uuid=True), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Alert {self.id}: {self.device} - {self.severity}>"
    
    @property
    def is_critical(self) -> bool:
        """Check if alert is critical severity."""
        return self.severity.lower() in ["critical", "high"]
    
    @property
    def age_minutes(self) -> float:
        """Get alert age in minutes."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 60


class AlertSettings(Base):
    """Model for alert system settings."""
    
    __tablename__ = "alert_settings"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), nullable=True)  # None for global settings
    
    # Notification preferences
    email_enabled = Column(Boolean, default=True, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    severity_threshold = Column(String(50), default="medium", nullable=False)
    
    # Auto-acknowledgment settings
    auto_ack_enabled = Column(Boolean, default=False, nullable=False)
    auto_ack_after_minutes = Column(Integer, default=60, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        user_type = "global" if self.user_id is None else f"user {self.user_id}"
        return f"<AlertSettings {self.id}: {user_type}>"