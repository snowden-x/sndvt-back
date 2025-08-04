"""Pydantic models for playbook management."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PlaybookStatus(str, Enum):
    """Status of playbook execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlaybookType(str, Enum):
    """Types of playbooks."""
    NETWORK_BACKUP = "network_backup"
    HEALTH_CHECK = "health_check"
    TROUBLESHOOTING = "troubleshooting"
    CONFIGURATION = "configuration"
    MAINTENANCE = "maintenance"


class PlaybookExecuteRequest(BaseModel):
    """Request model for playbook execution."""
    playbook_name: str = Field(..., description="Name of the playbook to execute")
    inventory: Optional[str] = Field(None, description="Inventory file or hosts")
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Variables to pass to playbook")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags to run")
    limit: Optional[str] = Field(None, description="Limit hosts to run on")
    ai_reasoning: Optional[str] = Field(None, description="AI reasoning for this execution")


class PlaybookResult(BaseModel):
    """Result model for playbook execution."""
    execution_id: str = Field(..., description="Unique execution ID")
    playbook_name: str = Field(..., description="Name of the executed playbook")
    status: PlaybookStatus = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="When execution started")
    completed_at: Optional[datetime] = Field(None, description="When execution completed")
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    success_count: int = Field(default=0, description="Number of successful tasks")
    failure_count: int = Field(default=0, description="Number of failed tasks")
    skipped_count: int = Field(default=0, description="Number of skipped tasks")
    output: Optional[str] = Field(None, description="Playbook output")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    variables_used: Dict[str, Any] = Field(default_factory=dict, description="Variables used in execution")


class PlaybookInfo(BaseModel):
    """Information about available playbooks."""
    name: str = Field(..., description="Playbook name")
    path: str = Field(..., description="Path to playbook file")
    description: str = Field(..., description="Description of what the playbook does")
    type: PlaybookType = Field(..., description="Type of playbook")
    tags: List[str] = Field(default_factory=list, description="Available tags")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Default variables")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")
    safety_level: str = Field(default="safe", description="Safety level (safe, caution, dangerous)")


class PlaybookValidateRequest(BaseModel):
    """Request model for playbook validation."""
    playbook_name: str = Field(..., description="Name of the playbook to validate")
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Variables to validate")
    inventory: Optional[str] = Field(None, description="Inventory to validate against")


class SafetyCheck(BaseModel):
    """Result of safety validation."""
    is_safe: bool = Field(..., description="Whether the playbook is safe to run")
    warnings: List[str] = Field(default_factory=list, description="Safety warnings")
    recommendations: List[str] = Field(default_factory=list, description="Safety recommendations")
    risk_level: str = Field(default="low", description="Risk level (low, medium, high)")
    affected_hosts: List[str] = Field(default_factory=list, description="Hosts that will be affected") 