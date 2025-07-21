"""Pydantic models for device discovery."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ScanType(str, Enum):
    """Types of network scans."""
    ping = "ping"
    port = "port"
    full = "full"


class ScanStatus(str, Enum):
    """Status of a discovery scan."""
    running = "running"
    completed = "completed"
    failed = "failed"


class DiscoveryRequest(BaseModel):
    """Request model for starting a discovery scan."""
    network: str = Field(..., description="Network range in CIDR notation (e.g., 192.168.1.0/24)")
    scan_type: ScanType = Field(default=ScanType.ping, description="Type of scan to perform")
    snmp_communities: Optional[List[str]] = Field(default=["public"], description="SNMP communities to test")
    ports: Optional[List[int]] = Field(default=[22, 23, 80, 161, 443], description="Ports to scan")
    timeout: Optional[int] = Field(default=5, description="Timeout in seconds")
    max_concurrent: Optional[int] = Field(default=50, description="Maximum concurrent scans")


class DiscoveredDevice(BaseModel):
    """Model for a discovered device."""
    ip: str = Field(..., description="IP address of the device")
    hostname: Optional[str] = Field(None, description="Hostname if resolved")
    status: str = Field(..., description="Device status (up/down)")
    response_time: Optional[float] = Field(None, description="Response time in milliseconds")
    open_ports: List[int] = Field(default_factory=list, description="Open ports found")
    suggested_protocols: List[str] = Field(default_factory=list, description="Suggested monitoring protocols")
    system_description: Optional[str] = Field(None, description="SNMP system description")
    device_type: Optional[str] = Field(None, description="Detected device type")
    snmp_community: Optional[str] = Field(None, description="Working SNMP community")
    confidence_score: float = Field(default=0.0, description="Confidence in device detection")


class DiscoveryResponse(BaseModel):
    """Response model for discovery scan status and results."""
    scan_id: str = Field(..., description="Unique scan identifier")
    network: str = Field(..., description="Network range being scanned")
    scan_type: ScanType = Field(..., description="Type of scan")
    status: ScanStatus = Field(..., description="Current scan status")
    started_at: datetime = Field(..., description="Scan start time")
    completed_at: Optional[datetime] = Field(None, description="Scan completion time")
    total_hosts: int = Field(default=0, description="Total hosts to scan")
    scanned_hosts: int = Field(default=0, description="Hosts scanned so far")
    discovered_devices: List[DiscoveredDevice] = Field(default_factory=list, description="Discovered devices")
    error_message: Optional[str] = Field(None, description="Error message if scan failed")


class ScanHistoryResponse(BaseModel):
    """Response model for scan history."""
    scan_id: str
    network: str
    scan_type: ScanType
    status: ScanStatus
    started_at: datetime
    completed_at: Optional[datetime]
    device_count: int = Field(description="Number of devices discovered") 