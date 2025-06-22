"""
Device Monitoring Service - Main service that coordinates all device monitors
"""

import asyncio
from typing import Dict, List, Optional, Any
import time
from dataclasses import asdict

from .device_manager import DeviceManager
from .snmp_client import SNMPClient
from .rest_client import RESTClient
from .ssh_client import SSHClient
from .base import DeviceConfig, DeviceStatus, InterfaceInfo, DeviceHealth, BaseMonitor

class DeviceMonitoringService:
    """Main service for device monitoring"""
    
    def __init__(self, config_path: str = "device_configs/devices.yaml"):
        self.device_manager = DeviceManager(config_path)
        self.monitors: Dict[str, BaseMonitor] = {}
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = self.device_manager.get_global_setting('cache_ttl', 300)  # 5 minutes default
        self.max_concurrent = self.device_manager.get_global_setting('max_concurrent_queries', 10)
        
        # Initialize monitors for all devices
        self._initialize_monitors()
    
    def _initialize_monitors(self):
        """Initialize monitors for all configured devices"""
        for device_id, device_config in self.device_manager.get_all_devices().items():
            self.monitors[device_id] = self._create_monitor(device_config)
    
    def _create_monitor(self, device_config: DeviceConfig) -> BaseMonitor:
        """Create appropriate monitor based on device protocols"""
        # Prioritize protocols: SNMP > REST > SSH
        if 'snmp' in device_config.enabled_protocols:
            return SNMPClient(device_config)
        elif 'rest' in device_config.enabled_protocols:
            return RESTClient(device_config)
        elif 'ssh' in device_config.enabled_protocols:
            return SSHClient(device_config)
        else:
            # Default to SNMP if no specific protocol is configured
            return SNMPClient(device_config)
    
    def _is_cache_valid(self, device_id: str, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if device_id not in self.cache:
            return False
        
        cache_entry = self.cache[device_id].get(cache_key)
        if not cache_entry:
            return False
        
        return (time.time() - cache_entry['timestamp']) < self.cache_ttl
    
    def _get_from_cache(self, device_id: str, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if self._is_cache_valid(device_id, cache_key):
            return self.cache[device_id][cache_key]['data']
        return None
    
    def _set_cache(self, device_id: str, cache_key: str, data: Any):
        """Store data in cache"""
        if device_id not in self.cache:
            self.cache[device_id] = {}
        
        self.cache[device_id][cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    async def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        """Get comprehensive device status"""
        if device_id not in self.monitors:
            return None
        
        # Check cache first
        cached_status = self._get_from_cache(device_id, 'status')
        if cached_status:
            return DeviceStatus(**cached_status)
        
        try:
            monitor = self.monitors[device_id]
            status = await monitor.get_device_status()
            
            # Cache the result
            self._set_cache(device_id, 'status', asdict(status))
            
            return status
        except Exception as e:
            print(f"Error getting status for device {device_id}: {e}")
            return DeviceStatus(
                device_id=device_id,
                reachable=False,
                error_message=str(e)
            )
    
    async def get_device_interfaces(self, device_id: str) -> List[InterfaceInfo]:
        """Get all interfaces for a device"""
        if device_id not in self.monitors:
            return []
        
        # Check cache first
        cached_interfaces = self._get_from_cache(device_id, 'interfaces')
        if cached_interfaces:
            return [InterfaceInfo(**iface) for iface in cached_interfaces]
        
        try:
            monitor = self.monitors[device_id]
            interfaces = await monitor.get_interfaces()
            
            # Cache the result
            self._set_cache(device_id, 'interfaces', [asdict(iface) for iface in interfaces])
            
            return interfaces
        except Exception as e:
            print(f"Error getting interfaces for device {device_id}: {e}")
            return []
    
    async def get_device_interface(self, device_id: str, interface_name: str) -> Optional[InterfaceInfo]:
        """Get specific interface for a device"""
        if device_id not in self.monitors:
            return None
        
        try:
            monitor = self.monitors[device_id]
            return await monitor.get_interface(interface_name)
        except Exception as e:
            print(f"Error getting interface {interface_name} for device {device_id}: {e}")
            return None
    
    async def get_device_health(self, device_id: str) -> Optional[DeviceHealth]:
        """Get device health metrics"""
        if device_id not in self.monitors:
            return None
        
        # Check cache first
        cached_health = self._get_from_cache(device_id, 'health')
        if cached_health:
            return DeviceHealth(**cached_health)
        
        try:
            monitor = self.monitors[device_id]
            health = await monitor.get_health_metrics()
            
            # Cache the result
            self._set_cache(device_id, 'health', asdict(health))
            
            return health
        except Exception as e:
            print(f"Error getting health for device {device_id}: {e}")
            return DeviceHealth()
    
    async def test_device_connection(self, device_id: str) -> bool:
        """Test if device is reachable"""
        if device_id not in self.monitors:
            return False
        
        try:
            monitor = self.monitors[device_id]
            return await monitor.test_connection()
        except Exception as e:
            print(f"Error testing connection to device {device_id}: {e}")
            return False
    
    async def get_multiple_device_status(self, device_ids: List[str]) -> Dict[str, DeviceStatus]:
        """Get status for multiple devices concurrently"""
        # Limit concurrent operations
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def get_status_with_semaphore(device_id: str) -> tuple[str, DeviceStatus]:
            async with semaphore:
                status = await self.get_device_status(device_id)
                return device_id, status
        
        # Execute all queries concurrently
        tasks = [get_status_with_semaphore(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        status_dict = {}
        for result in results:
            if isinstance(result, Exception):
                print(f"Error in concurrent status query: {result}")
                continue
            
            device_id, status = result
            if status:
                status_dict[device_id] = status
        
        return status_dict
    
    async def get_all_device_status(self) -> Dict[str, DeviceStatus]:
        """Get status for all configured devices"""
        device_ids = list(self.monitors.keys())
        return await self.get_multiple_device_status(device_ids)
    
    def get_device_list(self) -> List[Dict[str, Any]]:
        """Get list of all configured devices"""
        devices = []
        for device_id, device_config in self.device_manager.get_all_devices().items():
            devices.append({
                'id': device_id,
                'name': device_config.name,
                'host': device_config.host,
                'type': device_config.device_type.value,
                'protocols': device_config.enabled_protocols,
                'description': device_config.description
            })
        return devices
    
    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        """Get device configuration"""
        return self.device_manager.get_device(device_id)
    
    def reload_devices(self):
        """Reload device configurations"""
        self.device_manager.reload_config()
        self.monitors.clear()
        self.cache.clear()
        self._initialize_monitors()
    
    def clear_cache(self, device_id: Optional[str] = None):
        """Clear cache for specific device or all devices"""
        if device_id:
            self.cache.pop(device_id, None)
        else:
            self.cache.clear()
    
    async def ping_device(self, device_id: str) -> Dict[str, Any]:
        """Ping a device to test basic connectivity"""
        device_config = self.get_device_config(device_id)
        if not device_config:
            return {'success': False, 'error': 'Device not found'}
        
        try:
            # Simple ping test
            import subprocess
            import platform
            
            # Use appropriate ping command based on OS
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', '1', device_config.host]
            else:
                cmd = ['ping', '-c', '1', device_config.host]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'success': result.returncode == 0,
                'response_time': response_time,
                'output': result.stdout if result.returncode == 0 else result.stderr
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def discover_devices(self, subnet: str, snmp_communities: List[str] = None) -> List[Dict[str, Any]]:
        """Discover devices on a network subnet"""
        from .discovery import NetworkDiscovery
        
        discovery = NetworkDiscovery(
            max_concurrent=self.max_concurrent,
            timeout=5
        )
        
        try:
            devices = await discovery.discover_network(subnet, snmp_communities)
            return devices
        finally:
            discovery.close() 