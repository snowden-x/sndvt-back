"""
Device Manager - Handles device configuration loading and management
"""

import yaml
import os
from typing import Dict, List, Optional, Any
from app.device_monitoring.utils.base import DeviceConfig, DeviceCredentials, DeviceType

class DeviceManager:
    """Manages device configurations and provides device access"""
    
    def __init__(self, config_path: str = "config/device_configs/devices.yaml"):
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
    
    def create_device(self, device_config: DeviceConfig) -> bool:
        """Create a new device configuration and save to file"""
        try:
            # Add device to memory
            self.devices[device_config.id] = device_config
            
            # Save to file
            self._save_config()
            return True
        except Exception as e:
            print(f"Error creating device {device_config.id}: {e}")
            return False
    
    def update_device(self, device_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing device configuration"""
        try:
            if device_id not in self.devices:
                return False
            
            device = self.devices[device_id]
            
            # Update device fields
            if 'name' in updates:
                device.name = updates['name']
            if 'host' in updates:
                device.host = updates['host']
            if 'device_type' in updates:
                from app.device_monitoring.utils.base import DeviceType
                device.device_type = DeviceType(updates['device_type'])
            if 'enabled_protocols' in updates:
                device.enabled_protocols = updates['enabled_protocols']
            if 'timeout' in updates:
                device.timeout = updates['timeout']
            if 'retry_count' in updates:
                device.retry_count = updates['retry_count']
            if 'description' in updates:
                device.description = updates['description']
            if 'credentials' in updates:
                creds = updates['credentials']
                device.credentials.snmp_community = creds.get('snmp_community', device.credentials.snmp_community)
                device.credentials.snmp_version = creds.get('snmp_version', device.credentials.snmp_version)
                device.credentials.username = creds.get('username', device.credentials.username)
                device.credentials.password = creds.get('password', device.credentials.password)
                device.credentials.ssh_key = creds.get('ssh_key', device.credentials.ssh_key)
                device.credentials.api_token = creds.get('api_token', device.credentials.api_token)
                device.credentials.api_key = creds.get('api_key', device.credentials.api_key)
            
            # Save to file
            self._save_config()
            return True
        except Exception as e:
            print(f"Error updating device {device_id}: {e}")
            return False
    
    def delete_device(self, device_id: str) -> bool:
        """Delete a device configuration and save to file"""
        try:
            if device_id not in self.devices:
                return False
            
            del self.devices[device_id]
            
            # Save to file
            self._save_config()
            return True
        except Exception as e:
            print(f"Error deleting device {device_id}: {e}")
            return False
    
    def _save_config(self):
        """Save current device configurations to YAML file"""
        try:
            # Prepare data for saving
            config_data = {
                'global_settings': self.global_settings,
                'devices': {}
            }
            
            # Convert device configs to dict format
            for device_id, device in self.devices.items():
                config_data['devices'][device_id] = {
                    'name': device.name,
                    'host': device.host,
                    'device_type': device.device_type.value,
                    'enabled_protocols': device.enabled_protocols,
                    'timeout': device.timeout,
                    'retry_count': device.retry_count,
                    'description': device.description,
                    'credentials': {
                        'snmp_community': device.credentials.snmp_community,
                        'snmp_version': device.credentials.snmp_version,
                        'username': device.credentials.username,
                        'password': device.credentials.password,
                        'ssh_key': device.credentials.ssh_key,
                        'api_token': device.credentials.api_token,
                        'api_key': device.credentials.api_key
                    }
                }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Write to file
            with open(self.config_path, 'w') as file:
                yaml.dump(config_data, file, default_flow_style=False, indent=2)
            
            print(f"Device configurations saved to {self.config_path}")
            
        except Exception as e:
            print(f"Error saving device configurations: {e}")
            raise
    
    def device_exists(self, device_id: str) -> bool:
        """Check if a device exists"""
        return device_id in self.devices
    
    def generate_device_id(self, name: str, host: str) -> str:
        """Generate a unique device ID"""
        # Create base ID from name and host
        base_id = f"{name.lower().replace(' ', '-')}-{host.replace('.', '-')}"
        
        # Ensure uniqueness
        device_id = base_id
        counter = 1
        while device_id in self.devices:
            device_id = f"{base_id}-{counter}"
            counter += 1
        
        return device_id
    
    def export_config(self) -> Dict[str, Any]:
        """Export all device configurations"""
        return {
            'devices': {device_id: {
                'name': device.name,
                'host': device.host,
                'device_type': device.device_type.value,
                'enabled_protocols': device.enabled_protocols,
                'timeout': device.timeout,
                'retry_count': device.retry_count,
                'description': device.description,
                'credentials': {
                    'snmp_community': device.credentials.snmp_community,
                    'snmp_version': device.credentials.snmp_version,
                    'username': device.credentials.username,
                    # Don't export sensitive data
                    'has_password': bool(device.credentials.password),
                    'has_ssh_key': bool(device.credentials.ssh_key),
                    'has_api_token': bool(device.credentials.api_token),
                    'has_api_key': bool(device.credentials.api_key)
                }
            } for device_id, device in self.devices.items()},
            'global_settings': self.global_settings
        }
    
    def import_config(self, config_data: Dict[str, Any], merge_strategy: str = "replace"):
        """Import device configurations"""
        try:
            if merge_strategy == "replace":
                # Clear existing devices
                self.devices.clear()
            
            # Import global settings if provided
            if 'global_settings' in config_data:
                if merge_strategy == "replace":
                    self.global_settings = config_data['global_settings']
                else:
                    self.global_settings.update(config_data['global_settings'])
            
            # Import devices
            devices_data = config_data.get('devices', {})
            for device_id, device_data in devices_data.items():
                if merge_strategy == "skip_existing" and device_id in self.devices:
                    continue
                
                try:
                    device_config = self._parse_device_config(device_id, device_data)
                    self.devices[device_id] = device_config
                except Exception as e:
                    print(f"Error importing device {device_id}: {e}")
            
            # Save to file
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Error importing device configurations: {e}")
            return False 