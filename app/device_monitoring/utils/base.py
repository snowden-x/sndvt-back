"""
Base classes and interfaces for device monitoring
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import time

class DeviceType(Enum):
    """Supported device types"""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    ACCESS_POINT = "access_point"
    SERVER = "server"
    GENERIC = "generic"
    UNKNOWN = "unknown"

class InterfaceStatus(Enum):
    """Interface operational status"""
    UP = "up"
    DOWN = "down"
    ADMIN_DOWN = "admin_down"
    TESTING = "testing"
    UNKNOWN = "unknown"

@dataclass
class DeviceCredentials:
    """Device authentication credentials"""
    snmp_community: Optional[str] = None
    snmp_version: str = "2c"
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    api_token: Optional[str] = None
    api_key: Optional[str] = None

@dataclass
class DeviceConfig:
    """Device configuration"""
    id: str
    name: str
    host: str
    device_type: DeviceType
    credentials: DeviceCredentials
    enabled_protocols: List[str]
    timeout: int = 10
    retry_count: int = 3
    description: Optional[str] = None

@dataclass
class InterfaceInfo:
    """Network interface information"""
    name: str
    description: str
    status: InterfaceStatus
    admin_status: InterfaceStatus
    speed: Optional[int] = None  # Mbps
    mtu: Optional[int] = None
    mac_address: Optional[str] = None
    ip_addresses: List[str] = None
    in_octets: Optional[int] = None
    out_octets: Optional[int] = None
    in_errors: Optional[int] = None
    out_errors: Optional[int] = None
    last_change: Optional[float] = None

    def __post_init__(self):
        if self.ip_addresses is None:
            self.ip_addresses = []

@dataclass
class DeviceHealth:
    """Device health metrics"""
    cpu_usage: Optional[float] = None  # Percentage
    memory_usage: Optional[float] = None  # Percentage
    memory_total: Optional[int] = None  # MB
    memory_used: Optional[int] = None  # MB
    temperature: Optional[float] = None  # Celsius
    uptime: Optional[int] = None  # Seconds
    load_average: Optional[List[float]] = None
    disk_usage: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if self.load_average is None:
            self.load_average = []
        if self.disk_usage is None:
            self.disk_usage = {}

@dataclass
class DeviceStatus:
    """Overall device status"""
    device_id: str
    reachable: bool
    response_time: Optional[float] = None  # ms
    last_seen: Optional[float] = None
    error_message: Optional[str] = None
    health: Optional[DeviceHealth] = None
    interfaces: List[InterfaceInfo] = None
    uptime: Optional[int] = None

    def __post_init__(self):
        if self.interfaces is None:
            self.interfaces = []
        if self.last_seen is None:
            self.last_seen = time.time()

class BaseMonitor(ABC):
    """Abstract base class for device monitors"""
    
    def __init__(self, device_config: DeviceConfig):
        self.device_config = device_config
        self.timeout = device_config.timeout
        self.retry_count = device_config.retry_count
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if device is reachable"""
        pass
    
    @abstractmethod
    async def get_device_info(self) -> Dict[str, Any]:
        """Get basic device information"""
        pass
    
    @abstractmethod
    async def get_interfaces(self) -> List[InterfaceInfo]:
        """Get all interface information"""
        pass
    
    @abstractmethod
    async def get_interface(self, interface_name: str) -> Optional[InterfaceInfo]:
        """Get specific interface information"""
        pass
    
    @abstractmethod
    async def get_health_metrics(self) -> DeviceHealth:
        """Get device health metrics"""
        pass
    
    async def get_device_status(self) -> DeviceStatus:
        """Get comprehensive device status"""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            reachable = await self.test_connection()
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if not reachable:
                return DeviceStatus(
                    device_id=self.device_config.id,
                    reachable=False,
                    response_time=response_time,
                    error_message="Device unreachable"
                )
            
            # Get detailed information
            health = await self.get_health_metrics()
            interfaces = await self.get_interfaces()
            
            return DeviceStatus(
                device_id=self.device_config.id,
                reachable=True,
                response_time=response_time,
                health=health,
                interfaces=interfaces,
                uptime=health.uptime if health else None
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return DeviceStatus(
                device_id=self.device_config.id,
                reachable=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        last_exception = None
        
        for attempt in range(self.retry_count):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_count - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    delay = 2 ** attempt
                    await asyncio.sleep(delay)
        
        # If all retries failed, raise the last exception
        raise last_exception 