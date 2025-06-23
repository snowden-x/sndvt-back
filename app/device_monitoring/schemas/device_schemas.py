"""
Pydantic schemas for Device Monitoring API
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum

class DeviceTypeEnum(str, Enum):
    """Device type enumeration"""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    ACCESS_POINT = "access_point"
    SERVER = "server"
    GENERIC = "generic"

class ProtocolEnum(str, Enum):
    """Supported protocols"""
    SNMP = "snmp"
    SSH = "ssh"
    REST = "rest"
    TELNET = "telnet"

# Device Credentials Schema
class DeviceCredentialsRequest(BaseModel):
    """Device credentials for API requests"""
    snmp_community: Optional[str] = None
    snmp_version: str = Field(default="2c", pattern="^(1|2c|3)$")
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    api_token: Optional[str] = None
    api_key: Optional[str] = None

class DeviceCredentialsResponse(BaseModel):
    """Device credentials for API responses (sensitive data masked)"""
    snmp_community: Optional[str] = None
    snmp_version: str = "2c"
    username: Optional[str] = None
    has_password: bool = False
    has_ssh_key: bool = False
    has_api_token: bool = False
    has_api_key: bool = False

# Device CRUD Schemas
class DeviceCreateRequest(BaseModel):
    """Schema for creating a new device"""
    name: str = Field(..., min_length=1, max_length=100, description="Device name")
    host: str = Field(..., description="Device hostname or IP address")
    device_type: DeviceTypeEnum = Field(default=DeviceTypeEnum.GENERIC, description="Device type")
    enabled_protocols: List[ProtocolEnum] = Field(default=[ProtocolEnum.SNMP], description="Enabled protocols")
    credentials: Optional[DeviceCredentialsRequest] = None
    timeout: int = Field(default=10, ge=1, le=60, description="Connection timeout in seconds")
    retry_count: int = Field(default=3, ge=1, le=10, description="Number of retry attempts")
    description: Optional[str] = Field(None, max_length=500, description="Device description")
    
    @validator('host')
    def validate_host(cls, v):
        """Validate host format"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Host cannot be empty')
        return v.strip()

class DeviceUpdateRequest(BaseModel):
    """Schema for updating an existing device"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Device name")
    host: Optional[str] = Field(None, description="Device hostname or IP address")
    device_type: Optional[DeviceTypeEnum] = Field(None, description="Device type")
    enabled_protocols: Optional[List[ProtocolEnum]] = Field(None, description="Enabled protocols")
    credentials: Optional[DeviceCredentialsRequest] = None
    timeout: Optional[int] = Field(None, ge=1, le=60, description="Connection timeout in seconds")
    retry_count: Optional[int] = Field(None, ge=1, le=10, description="Number of retry attempts")
    description: Optional[str] = Field(None, max_length=500, description="Device description")
    
    @validator('host')
    def validate_host(cls, v):
        """Validate host format"""
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Host cannot be empty')
        return v.strip() if v else None

class DeviceResponse(BaseModel):
    """Schema for device API responses"""
    id: str
    name: str
    host: str
    device_type: DeviceTypeEnum
    enabled_protocols: List[str]
    credentials: DeviceCredentialsResponse
    timeout: int
    retry_count: int
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class DeviceListResponse(BaseModel):
    """Schema for device list responses"""
    id: str
    name: str
    host: str
    device_type: DeviceTypeEnum
    enabled_protocols: List[str]
    description: Optional[str] = None
    status: Optional[str] = None  # online, offline, unknown

# Discovery Schemas
class DiscoveryRequest(BaseModel):
    """Schema for network discovery requests"""
    network: str = Field(..., description="Network range to scan (e.g., 192.168.1.0/24)")
    scan_type: str = Field(default="ping", pattern="^(ping|port|full)$", description="Type of scan to perform")
    snmp_communities: Optional[List[str]] = Field(default=["public"], description="SNMP communities to try")
    ports: Optional[List[int]] = Field(None, description="Custom ports to scan")
    timeout: int = Field(default=2, ge=1, le=10, description="Scan timeout in seconds")
    max_concurrent: int = Field(default=50, ge=1, le=200, description="Maximum concurrent operations")
    
    @validator('network')
    def validate_network(cls, v):
        """Validate network format"""
        import ipaddress
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            raise ValueError('Invalid network format. Use CIDR notation (e.g., 192.168.1.0/24)')
        return v

class DiscoveredDeviceInfo(BaseModel):
    """Information about a discovered device"""
    ip: str
    hostname: Optional[str] = None
    response_time: Optional[float] = None
    open_ports: List[int] = []
    suggested_protocols: List[str] = []
    system_description: Optional[str] = None
    device_type: Optional[str] = None
    snmp_community: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

class DiscoveryResponse(BaseModel):
    """Schema for discovery operation responses"""
    scan_id: str
    network: str
    scan_type: str
    status: str  # running, completed, failed
    started_at: str
    completed_at: Optional[str] = None
    total_hosts: int
    scanned_hosts: int
    discovered_devices: List[DiscoveredDeviceInfo] = []
    error_message: Optional[str] = None

class DiscoveryResultResponse(BaseModel):
    """Schema for discovery results"""
    scan_id: str
    devices: List[DiscoveredDeviceInfo]
    summary: Dict[str, Any]

# Bulk Operations
class BulkDeviceCreateRequest(BaseModel):
    """Schema for bulk device creation"""
    devices: List[DeviceCreateRequest] = Field(..., min_items=1, max_items=100)

class BulkDeviceCreateResponse(BaseModel):
    """Schema for bulk device creation response"""
    created: List[DeviceResponse] = []
    failed: List[Dict[str, Any]] = []
    summary: Dict[str, int]

# Device Configuration Export/Import
class DeviceConfigExport(BaseModel):
    """Schema for exporting device configurations"""
    devices: Dict[str, Dict[str, Any]]
    global_settings: Dict[str, Any]
    export_timestamp: str
    version: str = "1.0"

class DeviceConfigImport(BaseModel):
    """Schema for importing device configurations"""
    devices: Dict[str, Dict[str, Any]]
    global_settings: Optional[Dict[str, Any]] = None
    merge_strategy: str = Field(default="replace", pattern="^(replace|merge|skip_existing)$")

# Advanced Discovery Schemas
class CustomDiscoveryRule(BaseModel):
    """Custom discovery rule"""
    name: str
    description: Optional[str] = None
    port_patterns: List[int] = []
    snmp_oids: List[str] = []
    device_type_hints: List[str] = []
    protocol_suggestions: List[str] = []

class AdvancedDiscoveryRequest(BaseModel):
    """Advanced discovery request with custom rules"""
    network: str
    custom_rules: List[CustomDiscoveryRule] = []
    deep_scan: bool = Field(default=False, description="Perform deep scanning including SNMP walks")
    save_results: bool = Field(default=True, description="Save results for later retrieval")
    auto_add_devices: bool = Field(default=False, description="Automatically add discovered devices")
    scan_name: Optional[str] = Field(None, description="Name for this scan")

# Scan Management
class ScanHistoryResponse(BaseModel):
    """Historical scan information"""
    scan_id: str
    scan_name: Optional[str] = None
    network: str
    scan_type: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    device_count: int
    created_by: Optional[str] = None 