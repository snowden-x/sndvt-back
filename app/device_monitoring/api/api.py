"""
FastAPI Router for Device Monitoring Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
from datetime import datetime

from app.device_monitoring.services.service import DeviceMonitoringService
from app.device_monitoring.services.device_manager import DeviceManager
from app.device_monitoring.services.advanced_discovery import AdvancedDiscoveryService
from app.device_monitoring.utils.base import DeviceStatus, InterfaceInfo, DeviceHealth, DeviceConfig, DeviceCredentials, DeviceType
from app.device_monitoring.schemas.device_schemas import (
    DeviceCreateRequest, DeviceUpdateRequest, DeviceResponse, DeviceCredentialsResponse,
    DiscoveryRequest, DiscoveryResponse, DiscoveredDeviceInfo, DiscoveryResultResponse,
    BulkDeviceCreateRequest, BulkDeviceCreateResponse, DeviceConfigExport, DeviceConfigImport,
    AdvancedDiscoveryRequest, ScanHistoryResponse
)

# Initialize services
monitoring_service = DeviceMonitoringService()
device_manager = DeviceManager()
discovery_service = AdvancedDiscoveryService()

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

# Helper functions for device conversion
def convert_device_to_response(device_config: DeviceConfig) -> DeviceResponse:
    """Convert DeviceConfig to API response"""
    return DeviceResponse(
        id=device_config.id,
        name=device_config.name,
        host=device_config.host,
        device_type=device_config.device_type,
        enabled_protocols=device_config.enabled_protocols,
        credentials=DeviceCredentialsResponse(
            snmp_community=device_config.credentials.snmp_community,
            snmp_version=device_config.credentials.snmp_version,
            username=device_config.credentials.username,
            has_password=bool(device_config.credentials.password),
            has_ssh_key=bool(device_config.credentials.ssh_key),
            has_api_token=bool(device_config.credentials.api_token),
            has_api_key=bool(device_config.credentials.api_key)
        ),
        timeout=device_config.timeout,
        retry_count=device_config.retry_count,
        description=device_config.description,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )

def create_device_config_from_request(device_id: str, request: DeviceCreateRequest) -> DeviceConfig:
    """Create DeviceConfig from API request"""
    credentials = DeviceCredentials()
    if request.credentials:
        credentials.snmp_community = request.credentials.snmp_community
        credentials.snmp_version = request.credentials.snmp_version
        credentials.username = request.credentials.username
        credentials.password = request.credentials.password
        credentials.ssh_key = request.credentials.ssh_key
        credentials.api_token = request.credentials.api_token
        credentials.api_key = request.credentials.api_key
    
    return DeviceConfig(
        id=device_id,
        name=request.name,
        host=request.host,
        device_type=DeviceType(request.device_type),
        credentials=credentials,
        enabled_protocols=[proto.value for proto in request.enabled_protocols],
        timeout=request.timeout,
        retry_count=request.retry_count,
        description=request.description
    )

# =============================================================================
# DEVICE CRUD OPERATIONS
# =============================================================================

@router.post("/", response_model=DeviceResponse, status_code=201)
async def create_device(request: DeviceCreateRequest):
    """Create a new device"""
    try:
        # Generate device ID
        device_id = device_manager.generate_device_id(request.name, request.host)
        
        # Create device config
        device_config = create_device_config_from_request(device_id, request)
        
        # Save device
        if device_manager.create_device(device_config):
            # Reload monitoring service to pick up new device
            monitoring_service.reload_devices()
            return convert_device_to_response(device_config)
        else:
            raise HTTPException(status_code=500, detail="Failed to create device")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create device: {str(e)}")

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    """Get a specific device configuration"""
    try:
        device_config = device_manager.get_device(device_id)
        if not device_config:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        return convert_device_to_response(device_config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device: {str(e)}")

@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: str, request: DeviceUpdateRequest):
    """Update an existing device"""
    try:
        # Check if device exists
        if not device_manager.device_exists(device_id):
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Prepare updates
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.host is not None:
            updates['host'] = request.host
        if request.device_type is not None:
            updates['device_type'] = request.device_type.value
        if request.enabled_protocols is not None:
            updates['enabled_protocols'] = [proto.value for proto in request.enabled_protocols]
        if request.timeout is not None:
            updates['timeout'] = request.timeout
        if request.retry_count is not None:
            updates['retry_count'] = request.retry_count
        if request.description is not None:
            updates['description'] = request.description
        if request.credentials is not None:
            updates['credentials'] = {
                'snmp_community': request.credentials.snmp_community,
                'snmp_version': request.credentials.snmp_version,
                'username': request.credentials.username,
                'password': request.credentials.password,
                'ssh_key': request.credentials.ssh_key,
                'api_token': request.credentials.api_token,
                'api_key': request.credentials.api_key
            }
        
        # Update device
        if device_manager.update_device(device_id, updates):
            # Reload monitoring service
            monitoring_service.reload_devices()
            
            # Return updated device
            device_config = device_manager.get_device(device_id)
            return convert_device_to_response(device_config)
        else:
            raise HTTPException(status_code=500, detail="Failed to update device")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update device: {str(e)}")

@router.delete("/{device_id}")
async def delete_device(device_id: str):
    """Delete a device"""
    try:
        if not device_manager.device_exists(device_id):
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        if device_manager.delete_device(device_id):
            # Reload monitoring service
            monitoring_service.reload_devices()
            return {"message": f"Device {device_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete device")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete device: {str(e)}")

@router.post("/bulk", response_model=BulkDeviceCreateResponse)
async def bulk_create_devices(request: BulkDeviceCreateRequest):
    """Create multiple devices at once"""
    try:
        created_devices = []
        failed_devices = []
        
        for device_request in request.devices:
            try:
                # Generate device ID
                device_id = device_manager.generate_device_id(device_request.name, device_request.host)
                
                # Create device config
                device_config = create_device_config_from_request(device_id, device_request)
                
                # Save device
                if device_manager.create_device(device_config):
                    created_devices.append(convert_device_to_response(device_config))
                else:
                    failed_devices.append({
                        'device': device_request.dict(),
                        'error': 'Failed to create device'
                    })
                    
            except Exception as e:
                failed_devices.append({
                    'device': device_request.dict(),
                    'error': str(e)
                })
        
        # Reload monitoring service if any devices were created
        if created_devices:
            monitoring_service.reload_devices()
        
        return BulkDeviceCreateResponse(
            created=created_devices,
            failed=failed_devices,
            summary={
                'total_requested': len(request.devices),
                'successfully_created': len(created_devices),
                'failed': len(failed_devices)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk create devices: {str(e)}")

# =============================================================================
# DEVICE CONFIGURATION IMPORT/EXPORT
# =============================================================================

@router.get("/config/export", response_model=DeviceConfigExport)
async def export_device_config():
    """Export all device configurations"""
    try:
        config_data = device_manager.export_config()
        return DeviceConfigExport(
            devices=config_data['devices'],
            global_settings=config_data['global_settings'],
            export_timestamp=datetime.now().isoformat(),
            version="1.0"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export configuration: {str(e)}")

@router.post("/config/import")
async def import_device_config(request: DeviceConfigImport):
    """Import device configurations"""
    try:
        config_data = {
            'devices': request.devices,
            'global_settings': request.global_settings or {}
        }
        
        if device_manager.import_config(config_data, request.merge_strategy):
            # Reload monitoring service
            monitoring_service.reload_devices()
            
            imported_count = len(request.devices)
            return {
                "message": f"Successfully imported {imported_count} device configurations",
                "merge_strategy": request.merge_strategy,
                "imported_count": imported_count
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to import configuration")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import configuration: {str(e)}")

# =============================================================================
# ADVANCED DISCOVERY OPERATIONS
# =============================================================================

@router.post("/discovery/scan", response_model=DiscoveryResponse)
async def start_discovery_scan(request: DiscoveryRequest):
    """Start a network discovery scan"""
    try:
        scan_id = await discovery_service.start_discovery_scan(
            network=request.network,
            scan_type=request.scan_type,
            snmp_communities=request.snmp_communities,
            ports=request.ports,
            timeout=request.timeout,
            max_concurrent=request.max_concurrent,
            save_results=True
        )
        
        # Get initial scan status
        scan_status = discovery_service.get_scan_status(scan_id)
        
        return DiscoveryResponse(
            scan_id=scan_id,
            network=request.network,
            scan_type=request.scan_type,
            status=scan_status['status'],
            started_at=scan_status['started_at'],
            completed_at=scan_status.get('completed_at'),
            total_hosts=scan_status.get('total_hosts', 0),
            scanned_hosts=scan_status.get('scanned_hosts', 0),
            discovered_devices=[DiscoveredDeviceInfo(**device) for device in scan_status.get('discovered_devices', [])]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start discovery scan: {str(e)}")

@router.get("/discovery/scan/{scan_id}", response_model=DiscoveryResponse)
async def get_scan_status(scan_id: str):
    """Get the status of a discovery scan"""
    try:
        scan_status = discovery_service.get_scan_status(scan_id)
        if not scan_status:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
        
        return DiscoveryResponse(
            scan_id=scan_status['scan_id'],
            network=scan_status['network'],
            scan_type=scan_status['scan_type'],
            status=scan_status['status'],
            started_at=scan_status['started_at'],
            completed_at=scan_status.get('completed_at'),
            total_hosts=scan_status.get('total_hosts', 0),
            scanned_hosts=scan_status.get('scanned_hosts', 0),
            discovered_devices=[DiscoveredDeviceInfo(**device) for device in scan_status.get('discovered_devices', [])],
            error_message=scan_status.get('error_message')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scan status: {str(e)}")

@router.get("/discovery/scan/{scan_id}/results", response_model=DiscoveryResultResponse)
async def get_scan_results(scan_id: str):
    """Get the results of a completed discovery scan"""
    try:
        scan_status = discovery_service.get_scan_status(scan_id)
        if not scan_status:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
        
        devices = [DiscoveredDeviceInfo(**device) for device in scan_status.get('discovered_devices', [])]
        
        # Generate summary
        summary = {
            'total_devices': len(devices),
            'device_types': {},
            'protocols': {},
            'scan_completed': scan_status['status'] == 'completed'
        }
        
        for device in devices:
            # Count device types
            device_type = device.device_type or 'unknown'
            summary['device_types'][device_type] = summary['device_types'].get(device_type, 0) + 1
            
            # Count protocols
            for protocol in device.suggested_protocols:
                summary['protocols'][protocol] = summary['protocols'].get(protocol, 0) + 1
        
        return DiscoveryResultResponse(
            scan_id=scan_id,
            devices=devices,
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scan results: {str(e)}")

@router.post("/discovery/scan/{scan_id}/add-devices")
async def auto_add_discovered_devices(scan_id: str):
    """Automatically add discovered devices to configuration"""
    try:
        result = await discovery_service.auto_add_devices_from_scan(scan_id)
        
        if result['success']:
            # Reload monitoring service if devices were added
            if result['added_devices']:
                monitoring_service.reload_devices()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add discovered devices: {str(e)}")

@router.get("/discovery/history", response_model=List[ScanHistoryResponse])
async def get_scan_history(limit: int = Query(50, ge=1, le=200)):
    """Get discovery scan history"""
    try:
        history = discovery_service.get_scan_history(limit)
        return [ScanHistoryResponse(**scan) for scan in history]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scan history: {str(e)}")

@router.delete("/discovery/scan/{scan_id}")
async def delete_scan_result(scan_id: str):
    """Delete a discovery scan result"""
    try:
        if discovery_service.delete_scan_result(scan_id):
            return {"message": f"Scan result {scan_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete scan result: {str(e)}")

@router.post("/discovery/advanced", response_model=DiscoveryResponse)
async def start_advanced_discovery(request: AdvancedDiscoveryRequest):
    """Start an advanced discovery scan with custom rules"""
    try:
        # For now, treat advanced discovery as a full scan
        # In the future, this could implement custom rules and deep scanning
        scan_id = await discovery_service.start_discovery_scan(
            network=request.network,
            scan_type="full",
            snmp_communities=["public", "private"],  # Default communities
            timeout=5 if request.deep_scan else 2,
            max_concurrent=25 if request.deep_scan else 50,
            scan_name=request.scan_name,
            save_results=request.save_results
        )
        
        # Get initial scan status
        scan_status = discovery_service.get_scan_status(scan_id)
        
        # Auto-add devices if requested
        if request.auto_add_devices:
            # This will be handled after scan completion
            pass
        
        return DiscoveryResponse(
            scan_id=scan_id,
            network=request.network,
            scan_type="full",
            status=scan_status['status'],
            started_at=scan_status['started_at'],
            completed_at=scan_status.get('completed_at'),
            total_hosts=scan_status.get('total_hosts', 0),
            scanned_hosts=scan_status.get('scanned_hosts', 0),
            discovered_devices=[DiscoveredDeviceInfo(**device) for device in scan_status.get('discovered_devices', [])]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start advanced discovery: {str(e)}")

@router.post("/discovery/cleanup")
async def cleanup_old_scan_results(days: int = Query(30, ge=1, le=365)):
    """Clean up old discovery scan results"""
    try:
        discovery_service.cleanup_old_results(days)
        return {"message": f"Cleaned up scan results older than {days} days"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup old results: {str(e)}") 