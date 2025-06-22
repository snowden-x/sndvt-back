#!/usr/bin/env python3
"""
Network Discovery Script
Discovers devices on the network and optionally adds them to configuration
"""

import asyncio
import sys
import yaml
import os
from typing import List, Dict, Any
from device_monitor.discovery import NetworkDiscovery

def get_user_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default value"""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    value = input(full_prompt).strip()
    return value if value else (default or "")

def get_yes_no(prompt: str, default: bool = None) -> bool:
    """Get yes/no input from user"""
    if default is True:
        full_prompt = f"{prompt} [Y/n]: "
    elif default is False:
        full_prompt = f"{prompt} [y/N]: "
    else:
        full_prompt = f"{prompt} [y/n]: "
    
    while True:
        value = input(full_prompt).strip().lower()
        
        if value in ['y', 'yes']:
            return True
        elif value in ['n', 'no']:
            return False
        elif default is not None and value == "":
            return default
        else:
            print("❌ Please enter 'y' for yes or 'n' for no.")

def select_devices_to_add(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Let user select which devices to add to configuration"""
    if not devices:
        return []
    
    print(f"\n📋 SELECT DEVICES TO ADD ({len(devices)} discovered)")
    print("=" * 60)
    
    selected_devices = []
    
    for i, device in enumerate(devices, 1):
        print(f"\n{i}. {device['ip']} ({device.get('hostname', 'Unknown')})")
        print(f"   Type: {device['device_type']}")
        print(f"   Protocols: {', '.join(device['suggested_protocols'])}")
        
        if device.get('system_description'):
            desc = device['system_description'][:80] + "..." if len(device['system_description']) > 80 else device['system_description']
            print(f"   Description: {desc}")
        
        if get_yes_no("Add this device to configuration?", True):
            selected_devices.append(device)
    
    return selected_devices

def customize_device_config(device: Dict[str, Any]) -> Dict[str, Any]:
    """Allow user to customize device configuration"""
    print(f"\n⚙️ CUSTOMIZE DEVICE: {device['ip']}")
    print("=" * 50)
    
    # Generate default device ID
    hostname = device.get('hostname', '').replace('.', '-').replace('_', '-')
    if hostname and hostname != 'Unknown hostname':
        default_id = f"{hostname}-{device['ip'].replace('.', '-')}"
    else:
        default_id = f"device-{device['ip'].replace('.', '-')}"
    
    # Clean up device ID
    import re
    default_id = re.sub(r'[^a-zA-Z0-9\-]', '', default_id).lower()
    
    # Get device configuration
    device_id = get_user_input("Device ID", default_id)
    device_name = get_user_input("Device Name", device.get('hostname', device['ip']))
    
    # Device type selection
    device_types = ["router", "switch", "firewall", "access_point", "server", "generic"]
    current_type = device.get('device_type', 'generic')
    
    print(f"\nCurrent device type: {current_type}")
    if not get_yes_no("Change device type?", False):
        device_type = current_type
    else:
        print("\nSelect device type:")
        for i, dtype in enumerate(device_types, 1):
            marker = " (current)" if dtype == current_type else ""
            print(f"  {i}. {dtype}{marker}")
        
        while True:
            try:
                choice = int(input(f"Enter choice [1-{len(device_types)}]: "))
                if 1 <= choice <= len(device_types):
                    device_type = device_types[choice - 1]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(device_types)}")
            except ValueError:
                print("Please enter a valid number")
    
    # Protocol selection
    suggested_protocols = device.get('suggested_protocols', ['snmp'])
    print(f"\nSuggested protocols: {', '.join(suggested_protocols)}")
    
    if get_yes_no("Use suggested protocols?", True):
        protocols = suggested_protocols
    else:
        protocols = []
        available_protocols = ['snmp', 'ssh', 'rest']
        for protocol in available_protocols:
            if get_yes_no(f"Enable {protocol.upper()}?", protocol in suggested_protocols):
                protocols.append(protocol)
    
    # Build credentials
    credentials = {}
    if 'snmp' in protocols:
        credentials['snmp_version'] = '2c'
        if device.get('snmp_community'):
            credentials['snmp_community'] = device['snmp_community']
        else:
            community = get_user_input("SNMP Community", "public")
            credentials['snmp_community'] = community
    
    # Description
    default_desc = device.get('system_description', f"Auto-discovered {device_type}")[:100]
    description = get_user_input("Description", default_desc)
    
    return {
        'id': device_id,
        'name': device_name,
        'host': device['ip'],
        'device_type': device_type,
        'description': description,
        'enabled_protocols': protocols,
        'credentials': credentials,
        'timeout': 10,
        'retry_count': 3
    }

def load_existing_config(config_path: str) -> Dict:
    """Load existing device configuration"""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            print(f"⚠️ Warning: Could not load existing config: {e}")
    
    return {
        'devices': {},
        'global_settings': {
            'default_timeout': 10,
            'default_retry_count': 3,
            'cache_ttl': 300,
            'max_concurrent_queries': 10,
            'snmp_default_port': 161,
            'ssh_default_port': 22,
            'rest_default_port': 443
        }
    }

def save_config(config: Dict, config_path: str):
    """Save configuration to file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False, indent=2)
        
        print(f"✅ Configuration saved to {config_path}")
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        sys.exit(1)

async def main():
    """Main discovery function"""
    print("🌐 Network Discovery Tool")
    print("=" * 60)
    print("This tool will discover devices on your network and help you add them to monitoring.")
    print()
    
    # Get network to scan
    while True:
        network = get_user_input("Network to scan (e.g., 192.168.1.0/24, 10.0.0.0/16)")
        if network:
            break
        print("❌ Please enter a valid network range")
    
    # Get SNMP communities
    communities_input = get_user_input("SNMP communities to try (comma-separated)", "public,private")
    snmp_communities = [c.strip() for c in communities_input.split(',') if c.strip()]
    
    # Advanced settings
    max_concurrent = 50
    timeout = 2
    
    if get_yes_no("Configure advanced scan settings?", False):
        try:
            max_concurrent = int(get_user_input("Max concurrent scans", "50"))
            timeout = int(get_user_input("Timeout per scan (seconds)", "2"))
        except ValueError:
            print("⚠️ Invalid values, using defaults")
    
    # Start discovery
    print(f"\n🚀 Starting network discovery...")
    print(f"Network: {network}")
    print(f"SNMP Communities: {', '.join(snmp_communities)}")
    print(f"Max Concurrent: {max_concurrent}")
    print(f"Timeout: {timeout}s")
    print()
    
    discovery = NetworkDiscovery(max_concurrent=max_concurrent, timeout=timeout)
    
    try:
        devices = await discovery.discover_network(network, snmp_communities)
        
        if not devices:
            print("❌ No devices discovered")
            return
        
        # Show results
        discovery.print_discovery_results(devices)
        
        # Ask if user wants to add devices to configuration
        if not get_yes_no(f"\nAdd discovered devices to monitoring configuration?", True):
            print("Discovery complete. No devices added to configuration.")
            return
        
        # Let user select devices to add
        if get_yes_no("Select individual devices to add?", True):
            selected_devices = select_devices_to_add(devices)
        else:
            selected_devices = devices
        
        if not selected_devices:
            print("No devices selected. Exiting.")
            return
        
        # Customize device configurations
        device_configs = []
        
        if get_yes_no(f"Customize configuration for {len(selected_devices)} devices?", False):
            for device in selected_devices:
                config = customize_device_config(device)
                device_configs.append(config)
        else:
            # Use auto-generated configs
            auto_config = discovery.generate_device_configs(selected_devices)
            device_configs = list(auto_config['devices'].values())
            
            # Add device IDs
            for i, config in enumerate(device_configs):
                config['id'] = list(auto_config['devices'].keys())[i]
        
        # Load existing configuration and merge
        config_path = "device_configs/devices.yaml"
        config = load_existing_config(config_path)
        
        # Add new devices
        added_count = 0
        for device_config in device_configs:
            device_id = device_config.pop('id')
            
            if device_id in config.get('devices', {}):
                if get_yes_no(f"Device '{device_id}' already exists. Overwrite?", False):
                    config['devices'][device_id] = device_config
                    added_count += 1
            else:
                if 'devices' not in config:
                    config['devices'] = {}
                config['devices'][device_id] = device_config
                added_count += 1
        
        if added_count > 0:
            # Save configuration
            save_config(config, config_path)
            
            print(f"\n✅ Successfully added {added_count} devices to configuration!")
            print("\nNext steps:")
            print("1. Start or restart the monitoring service")
            print("2. Test device connections:")
            print("   python test_device_monitoring.py")
            print("3. Set up environment variables for sensitive credentials")
        else:
            print("❌ No devices were added to configuration")
    
    finally:
        discovery.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Discovery cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1) 