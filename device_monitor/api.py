"""
FastAPI Router for Device Monitoring Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio

from .service import DeviceMonitoringService
from .base import DeviceStatus, InterfaceInfo, DeviceHealth

# Initialize the monitoring service
monitoring_service = DeviceMonitoringService()

# Create the API router
router = APIRouter(prefix="/devices", tags=["Device Monitoring"])

# Pydantic models for API responses
class DeviceStatusResponse(BaseModel):
    device_id: str
    reachable: bool
    response_time: Optional[float] = None
    last_seen: Optional[float] = None
    error_message: Optional[str] = None
    health: Optional[Dict[str, Any]] = None
    interfaces: Optional[List[Dict[str, Any]]] = None
    uptime: Optional[int] = None

class InterfaceResponse(BaseModel):
    name: str
    description: str
    status: str
    admin_status: str
    speed: Optional[int] = None
    mtu: Optional[int] = None
    mac_address: Optional[str] = None
    ip_addresses: List[str] = []
    in_octets: Optional[int] = None
    out_octets: Optional[int] = None
    in_errors: Optional[int] = None
    out_errors: Optional[int] = None
    last_change: Optional[float] = None

class HealthResponse(BaseModel):
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    memory_total: Optional[int] = None
    memory_used: Optional[int] = None
    temperature: Optional[float] = None
    uptime: Optional[int] = None
    load_average: List[float] = []
    disk_usage: Dict[str, float] = {}

class DeviceListResponse(BaseModel):
    id: str
    name: str
    host: str
    type: str
    protocols: List[str]
    description: Optional[str] = None

class PingResponse(BaseModel):
    success: bool
    response_time: Optional[float] = None
    error: Optional[str] = None
    output: Optional[str] = None

def convert_device_status(status: DeviceStatus) -> DeviceStatusResponse:
    """Convert DeviceStatus to API response model"""
    return DeviceStatusResponse(
        device_id=status.device_id,
        reachable=status.reachable,
        response_time=status.response_time,
        last_seen=status.last_seen,
        error_message=status.error_message,
        health=status.health.__dict__ if status.health else None,
        interfaces=[iface.__dict__ for iface in status.interfaces] if status.interfaces else None,
        uptime=status.uptime
    )

def convert_interface(interface: InterfaceInfo) -> InterfaceResponse:
    """Convert InterfaceInfo to API response model"""
    return InterfaceResponse(
        name=interface.name,
        description=interface.description,
        status=interface.status.value,
        admin_status=interface.admin_status.value,
        speed=interface.speed,
        mtu=interface.mtu,
        mac_address=interface.mac_address,
        ip_addresses=interface.ip_addresses,
        in_octets=interface.in_octets,
        out_octets=interface.out_octets,
        in_errors=interface.in_errors,
        out_errors=interface.out_errors,
        last_change=interface.last_change
    )

def convert_health(health: DeviceHealth) -> HealthResponse:
    """Convert DeviceHealth to API response model"""
    return HealthResponse(
        cpu_usage=health.cpu_usage,
        memory_usage=health.memory_usage,
        memory_total=health.memory_total,
        memory_used=health.memory_used,
        temperature=health.temperature,
        uptime=health.uptime,
        load_average=health.load_average,
        disk_usage=health.disk_usage
    )

@router.get("/", response_model=List[DeviceListResponse])
async def list_devices():
    """Get list of all configured devices"""
    try:
        devices = monitoring_service.get_device_list()
        return [DeviceListResponse(**device) for device in devices]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device list: {str(e)}")

@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(device_id: str):
    """Get comprehensive device status"""
    try:
        status = await monitoring_service.get_device_status(device_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        return convert_device_status(status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device status: {str(e)}")

@router.get("/{device_id}/interfaces", response_model=List[InterfaceResponse])
async def get_device_interfaces(device_id: str):
    """Get all interfaces for a device"""
    try:
        interfaces = await monitoring_service.get_device_interfaces(device_id)
        return [convert_interface(iface) for iface in interfaces]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device interfaces: {str(e)}")

@router.get("/{device_id}/interfaces/{interface_name}", response_model=InterfaceResponse)
async def get_device_interface(device_id: str, interface_name: str):
    """Get specific interface information"""
    try:
        interface = await monitoring_service.get_device_interface(device_id, interface_name)
        if not interface:
            raise HTTPException(status_code=404, detail=f"Interface {interface_name} not found on device {device_id}")
        
        return convert_interface(interface)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get interface: {str(e)}")

@router.get("/{device_id}/health", response_model=HealthResponse)
async def get_device_health(device_id: str):
    """Get device health metrics"""
    try:
        health = await monitoring_service.get_device_health(device_id)
        if not health:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        return convert_health(health)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device health: {str(e)}")

@router.post("/{device_id}/ping", response_model=PingResponse)
async def ping_device(device_id: str):
    """Ping a device to test connectivity"""
    try:
        result = await monitoring_service.ping_device(device_id)
        return PingResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ping device: {str(e)}")

@router.get("/{device_id}/test")
async def test_device_connection(device_id: str):
    """Test device connection using configured protocol"""
    try:
        result = await monitoring_service.test_device_connection(device_id)
        return {"device_id": device_id, "reachable": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test device connection: {str(e)}")

@router.get("/status/all")
async def get_all_device_status(
    device_ids: Optional[List[str]] = Query(None, description="Specific device IDs to query")
):
    """Get status for multiple devices concurrently"""
    try:
        if device_ids:
            status_dict = await monitoring_service.get_multiple_device_status(device_ids)
        else:
            status_dict = await monitoring_service.get_all_device_status()
        
        # Convert to response format
        result = {}
        for device_id, status in status_dict.items():
            result[device_id] = convert_device_status(status).__dict__
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device status: {str(e)}")

@router.post("/reload")
async def reload_device_configs():
    """Reload device configurations from file"""
    try:
        monitoring_service.reload_devices()
        return {"message": "Device configurations reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload configurations: {str(e)}")

@router.delete("/cache")
async def clear_cache(device_id: Optional[str] = Query(None, description="Device ID to clear cache for")):
    """Clear cache for specific device or all devices"""
    try:
        monitoring_service.clear_cache(device_id)
        if device_id:
            return {"message": f"Cache cleared for device {device_id}"}
        else:
            return {"message": "Cache cleared for all devices"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.get("/discovery/{subnet}")
async def discover_devices(
    subnet: str, 
    snmp_communities: Optional[List[str]] = Query(None, description="SNMP communities to try")
):
    """Discover devices on a network subnet"""
    try:
        devices = await monitoring_service.discover_devices(subnet, snmp_communities)
        return {
            "subnet": subnet, 
            "discovered_devices": devices,
            "count": len(devices)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover devices: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for the monitoring service"""
    try:
        device_count = len(monitoring_service.get_device_list())
        return {
            "status": "healthy",
            "service": "device_monitoring",
            "configured_devices": device_count,
            "cache_ttl": monitoring_service.cache_ttl,
            "max_concurrent": monitoring_service.max_concurrent
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        } 