"""
REST API Client for modern network device monitoring
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
import json

from .base import BaseMonitor, DeviceConfig, InterfaceInfo, DeviceHealth, InterfaceStatus

class RESTClient(BaseMonitor):
    """REST API-based device monitor"""
    
    def __init__(self, device_config: DeviceConfig):
        super().__init__(device_config)
        self.base_url = f"https://{device_config.host}"
        self.api_token = device_config.credentials.api_token
        self.api_key = device_config.credentials.api_key
        self.username = device_config.credentials.username
        self.password = device_config.credentials.password
        
        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_token:
            self.headers["Authorization"] = f"Bearer {self.api_token}"
        elif self.api_key:
            self.headers["X-API-Key"] = self.api_key
    
    async def test_connection(self) -> bool:
        """Test REST API connectivity"""
        try:
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                # Try a basic endpoint (varies by device type)
                endpoints_to_try = [
                    "/api/v1/system/status",
                    "/api/system/info", 
                    "/restconf/data/system-state",
                    "/api/status",
                    "/system"
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers,
                            auth=(self.username, self.password) if self.username else None
                        )
                        if response.status_code in [200, 401]:  # 401 means endpoint exists but auth failed
                            return True
                    except:
                        continue
                        
                return False
        except Exception:
            return False
    
    async def get_device_info(self) -> Dict[str, Any]:
        """Get basic device information via REST API"""
        try:
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                # Try common system info endpoints
                endpoints = [
                    "/api/v1/system/info",
                    "/api/system/status",
                    "/restconf/data/system-state/platform"
                ]
                
                for endpoint in endpoints:
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers,
                            auth=(self.username, self.password) if self.username else None
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            return self._parse_system_info(data)
                    except:
                        continue
                
                # If no specific endpoint works, return basic info
                return {
                    'description': f'REST API Device at {self.device_config.host}',
                    'name': self.device_config.name,
                    'uptime': None,
                    'location': 'Unknown',
                    'contact': 'Unknown'
                }
                
        except Exception as e:
            raise Exception(f"Failed to get device info: {e}")
    
    async def get_interfaces(self) -> List[InterfaceInfo]:
        """Get all interface information via REST API"""
        try:
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                # Try common interface endpoints
                endpoints = [
                    "/api/v1/interfaces",
                    "/api/interfaces",
                    "/restconf/data/interfaces-state/interface"
                ]
                
                for endpoint in endpoints:
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers,
                            auth=(self.username, self.password) if self.username else None
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            return self._parse_interfaces(data)
                    except:
                        continue
                
                return []  # Return empty list if no interfaces found
                
        except Exception as e:
            raise Exception(f"Failed to get interfaces: {e}")
    
    async def get_interface(self, interface_name: str) -> Optional[InterfaceInfo]:
        """Get specific interface information"""
        interfaces = await self.get_interfaces()
        for interface in interfaces:
            if interface.name.lower() == interface_name.lower():
                return interface
        return None
    
    async def get_health_metrics(self) -> DeviceHealth:
        """Get device health metrics via REST API"""
        health = DeviceHealth()
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                # Try common health/status endpoints
                endpoints = [
                    "/api/v1/system/health",
                    "/api/system/resources",
                    "/api/monitoring/system",
                    "/restconf/data/system-state"
                ]
                
                for endpoint in endpoints:
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers,
                            auth=(self.username, self.password) if self.username else None
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            parsed_health = self._parse_health_metrics(data)
                            if parsed_health:
                                return parsed_health
                    except:
                        continue
                
        except Exception as e:
            print(f"Warning: Could not get health metrics: {e}")
        
        return health
    
    def _parse_system_info(self, data: Dict) -> Dict[str, Any]:
        """Parse system information from REST API response"""
        # This is a generic parser - would need customization for specific device APIs
        result = {
            'description': 'Unknown',
            'name': 'Unknown',
            'uptime': None,
            'location': 'Unknown',
            'contact': 'Unknown'
        }
        
        # Try to extract common fields
        if isinstance(data, dict):
            result['description'] = data.get('description', data.get('model', data.get('platform', 'Unknown')))
            result['name'] = data.get('hostname', data.get('name', data.get('device_name', 'Unknown')))
            result['uptime'] = data.get('uptime', data.get('uptime_seconds'))
            result['location'] = data.get('location', 'Unknown')
            result['contact'] = data.get('contact', 'Unknown')
        
        return result
    
    def _parse_interfaces(self, data: Dict) -> List[InterfaceInfo]:
        """Parse interface information from REST API response"""
        interfaces = []
        
        # Handle different response formats
        interface_list = []
        if isinstance(data, dict):
            if 'interfaces' in data:
                interface_list = data['interfaces']
            elif 'interface' in data:
                interface_list = data['interface'] if isinstance(data['interface'], list) else [data['interface']]
            elif isinstance(data, list):
                interface_list = data
        elif isinstance(data, list):
            interface_list = data
        
        for iface_data in interface_list:
            if isinstance(iface_data, dict):
                try:
                    interface = InterfaceInfo(
                        name=iface_data.get('name', iface_data.get('interface_name', 'Unknown')),
                        description=iface_data.get('description', iface_data.get('desc', '')),
                        status=self._parse_status(iface_data.get('oper_status', iface_data.get('status', 'unknown'))),
                        admin_status=self._parse_status(iface_data.get('admin_status', iface_data.get('enabled', 'unknown'))),
                        speed=iface_data.get('speed'),
                        mtu=iface_data.get('mtu'),
                        mac_address=iface_data.get('mac_address', iface_data.get('physical_address')),
                        ip_addresses=iface_data.get('ip_addresses', []),
                        in_octets=iface_data.get('rx_bytes', iface_data.get('in_octets')),
                        out_octets=iface_data.get('tx_bytes', iface_data.get('out_octets')),
                        in_errors=iface_data.get('rx_errors', iface_data.get('in_errors')),
                        out_errors=iface_data.get('tx_errors', iface_data.get('out_errors'))
                    )
                    interfaces.append(interface)
                except Exception as e:
                    print(f"Error parsing interface data: {e}")
                    continue
        
        return interfaces
    
    def _parse_health_metrics(self, data: Dict) -> Optional[DeviceHealth]:
        """Parse health metrics from REST API response"""
        if not isinstance(data, dict):
            return None
        
        health = DeviceHealth()
        
        # Try to extract common health metrics
        health.cpu_usage = data.get('cpu_usage', data.get('cpu_percent', data.get('processor_load')))
        health.memory_usage = data.get('memory_usage', data.get('memory_percent'))
        health.memory_total = data.get('memory_total', data.get('total_memory'))
        health.memory_used = data.get('memory_used', data.get('used_memory'))
        health.temperature = data.get('temperature', data.get('temp'))
        health.uptime = data.get('uptime', data.get('uptime_seconds'))
        
        # Handle nested structures
        if 'system' in data:
            sys_data = data['system']
            if isinstance(sys_data, dict):
                health.cpu_usage = health.cpu_usage or sys_data.get('cpu_usage')
                health.memory_usage = health.memory_usage or sys_data.get('memory_usage')
                health.uptime = health.uptime or sys_data.get('uptime')
        
        return health
    
    def _parse_status(self, status_value) -> InterfaceStatus:
        """Parse interface status from REST API response"""
        if not status_value:
            return InterfaceStatus.UNKNOWN
        
        status_str = str(status_value).lower()
        
        if status_str in ['up', 'active', 'enabled', 'true', '1']:
            return InterfaceStatus.UP
        elif status_str in ['down', 'inactive', 'disabled', 'false', '0']:
            return InterfaceStatus.DOWN
        elif status_str in ['admin_down', 'admin-down', 'administratively_down']:
            return InterfaceStatus.ADMIN_DOWN
        elif status_str in ['testing', 'test']:
            return InterfaceStatus.TESTING
        else:
            return InterfaceStatus.UNKNOWN 