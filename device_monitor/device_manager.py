"""
Device Manager - Handles device configuration loading and management
"""

import yaml
import os
from typing import Dict, List, Optional
from .base import DeviceConfig, DeviceCredentials, DeviceType

class DeviceManager:
    """Manages device configurations and provides device access"""
    
    def __init__(self, config_path: str = "device_configs/devices.yaml"):
        self.config_path = config_path
        self.devices: Dict[str, DeviceConfig] = {}
        self.global_settings: Dict = {}
        self._load_config()
    
    def _load_config(self):
        """Load device configurations from YAML file"""
        try:
            if not os.path.exists(self.config_path):
                print(f"Warning: Device config file not found: {self.config_path}")
                return
            
            with open(self.config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            # Load global settings
            self.global_settings = config_data.get('global_settings', {})
            
            # Load device configurations
            devices_data = config_data.get('devices', {})
            
            for device_id, device_data in devices_data.items():
                try:
                    device_config = self._parse_device_config(device_id, device_data)
                    self.devices[device_id] = device_config
                except Exception as e:
                    print(f"Error parsing device config for {device_id}: {e}")
            
            print(f"Loaded {len(self.devices)} device configurations")
            
        except Exception as e:
            print(f"Error loading device configurations: {e}")
    
    def _parse_device_config(self, device_id: str, device_data: Dict) -> DeviceConfig:
        """Parse a single device configuration"""
        
        # Parse credentials
        creds_data = device_data.get('credentials', {})
        credentials = DeviceCredentials(
            snmp_community=creds_data.get('snmp_community'),
            snmp_version=creds_data.get('snmp_version', '2c'),
            username=creds_data.get('username'),
            password=os.getenv(f"{device_id.upper()}_PASSWORD") or creds_data.get('password'),
            ssh_key=creds_data.get('ssh_key'),
            api_token=os.getenv(f"{device_id.upper()}_API_TOKEN") or creds_data.get('api_token'),
            api_key=os.getenv(f"{device_id.upper()}_API_KEY") or creds_data.get('api_key')
        )
        
        # Parse device type
        device_type_str = device_data.get('device_type', 'generic')
        try:
            device_type = DeviceType(device_type_str)
        except ValueError:
            device_type = DeviceType.GENERIC
        
        return DeviceConfig(
            id=device_id,
            name=device_data.get('name', device_id),
            host=device_data['host'],
            device_type=device_type,
            credentials=credentials,
            enabled_protocols=device_data.get('enabled_protocols', ['snmp']),
            timeout=device_data.get('timeout', self.global_settings.get('default_timeout', 10)),
            retry_count=device_data.get('retry_count', self.global_settings.get('default_retry_count', 3)),
            description=device_data.get('description')
        )
    
    def get_device(self, device_id: str) -> Optional[DeviceConfig]:
        """Get a specific device configuration"""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> Dict[str, DeviceConfig]:
        """Get all device configurations"""
        return self.devices.copy()
    
    def get_devices_by_type(self, device_type: DeviceType) -> List[DeviceConfig]:
        """Get all devices of a specific type"""
        return [device for device in self.devices.values() 
                if device.device_type == device_type]
    
    def get_devices_with_protocol(self, protocol: str) -> List[DeviceConfig]:
        """Get all devices that support a specific protocol"""
        return [device for device in self.devices.values() 
                if protocol in device.enabled_protocols]
    
    def reload_config(self):
        """Reload device configurations from file"""
        self.devices.clear()
        self.global_settings.clear()
        self._load_config()
    
    def add_device(self, device_config: DeviceConfig):
        """Add a device configuration at runtime"""
        self.devices[device_config.id] = device_config
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device configuration"""
        if device_id in self.devices:
            del self.devices[device_id]
            return True
        return False
    
    def get_global_setting(self, key: str, default=None):
        """Get a global setting value"""
        return self.global_settings.get(key, default) 