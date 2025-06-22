#!/usr/bin/env python3
"""
Interactive Device Setup Script
Helps users add network devices to the monitoring configuration
"""

import yaml
import os
import sys
from typing import Dict, List, Optional
import ipaddress
import socket

def get_user_input(prompt: str, default: str = None, required: bool = True) -> str:
    """Get user input with optional default value"""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        value = input(full_prompt).strip()
        
        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print("❌ This field is required. Please enter a value.")

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

def get_choice(prompt: str, choices: List[str], default: str = None) -> str:
    """Get a choice from a list of options"""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")
    
    while True:
        try:
            value = input(f"Enter choice [1-{len(choices)}]: ").strip()
            
            if value == "" and default:
                return default
            
            choice_num = int(value)
            if 1 <= choice_num <= len(choices):
                return choices[choice_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("❌ Please enter a valid number")

def validate_ip_address(ip: str) -> bool:
    """Validate if string is a valid IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_hostname(hostname: str) -> bool:
    """Validate if hostname is reachable"""
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False

def test_connectivity(host: str, timeout: int = 5) -> bool:
    """Test basic connectivity to host"""
    try:
        import subprocess
        import platform
        
        # Use appropriate ping command based on OS
        if platform.system().lower() == 'windows':
            cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), host]
        else:
            cmd = ['ping', '-c', '1', '-W', str(timeout), host]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
        return result.returncode == 0
    except Exception:
        return False

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

def collect_device_info() -> Dict:
    """Collect device information from user"""
    print("\n" + "="*60)
    print("📋 DEVICE INFORMATION")
    print("="*60)
    
    # Basic device info
    device_id = get_user_input("Device ID (unique identifier, e.g., 'core-router')")
    device_name = get_user_input("Device Name (display name)", device_id)
    
    # Host information
    while True:
        host = get_user_input("Host (IP address or hostname)")
        
        if validate_ip_address(host):
            print(f"✅ Valid IP address: {host}")
            break
        elif validate_hostname(host):
            print(f"✅ Valid hostname: {host}")
            break
        else:
            print(f"❌ Invalid IP address or hostname: {host}")
            if not get_yes_no("Continue anyway?", False):
                continue
            break
    
    # Test connectivity
    if get_yes_no("Test connectivity to device?", True):
        print(f"🔍 Testing connectivity to {host}...")
        if test_connectivity(host):
            print("✅ Device is reachable")
        else:
            print("❌ Device is not reachable")
            if not get_yes_no("Continue anyway?", False):
                return collect_device_info()
    
    # Device type
    device_types = ["router", "switch", "firewall", "access_point", "server", "generic"]
    device_type = get_choice("Select device type:", device_types, "router")
    
    # Description
    description = get_user_input("Description (optional)", f"{device_name} - {device_type}", False)
    
    return {
        'id': device_id,
        'name': device_name,
        'host': host,
        'device_type': device_type,
        'description': description
    }

def collect_protocol_info() -> Dict:
    """Collect protocol and credential information"""
    print("\n" + "="*60)
    print("🔐 PROTOCOL & CREDENTIALS")
    print("="*60)
    
    protocols = []
    credentials = {}
    
    # SNMP Configuration
    if get_yes_no("Enable SNMP monitoring?", True):
        protocols.append("snmp")
        
        snmp_version = get_choice("SNMP Version:", ["1", "2c", "3"], "2c")
        credentials['snmp_version'] = snmp_version
        
        if snmp_version in ["1", "2c"]:
            community = get_user_input("SNMP Community string", "public")
            credentials['snmp_community'] = community
        else:
            # SNMPv3 - more complex, placeholder for now
            print("⚠️ SNMPv3 configuration not fully implemented yet")
            username = get_user_input("SNMP Username")
            credentials['username'] = username
    
    # SSH Configuration
    if get_yes_no("Enable SSH monitoring?", False):
        protocols.append("ssh")
        
        ssh_username = get_user_input("SSH Username")
        credentials['username'] = ssh_username
        
        auth_method = get_choice("SSH Authentication method:", ["password", "key"], "password")
        
        if auth_method == "password":
            print("💡 Tip: Set password in environment variable for security")
            print(f"   Example: export {credentials.get('username', 'DEVICE').upper()}_PASSWORD=your_password")
        else:
            ssh_key = get_user_input("SSH Key file path", "~/.ssh/id_rsa")
            credentials['ssh_key'] = ssh_key
    
    # REST API Configuration
    if get_yes_no("Enable REST API monitoring?", False):
        protocols.append("rest")
        
        auth_method = get_choice("REST API Authentication:", ["token", "key", "basic"], "token")
        
        if auth_method == "token":
            print("💡 Tip: Set API token in environment variable for security")
            print(f"   Example: export DEVICE_API_TOKEN=your_token")
        elif auth_method == "key":
            print("💡 Tip: Set API key in environment variable for security")
            print(f"   Example: export DEVICE_API_KEY=your_key")
        else:
            if not credentials.get('username'):
                username = get_user_input("REST API Username")
                credentials['username'] = username
            print("💡 Tip: Set password in environment variable for security")
    
    if not protocols:
        print("⚠️ No protocols selected. Defaulting to SNMP.")
        protocols = ["snmp"]
        credentials['snmp_community'] = "public"
        credentials['snmp_version'] = "2c"
    
    return {
        'protocols': protocols,
        'credentials': credentials
    }

def collect_advanced_settings() -> Dict:
    """Collect advanced device settings"""
    print("\n" + "="*60)
    print("⚙️ ADVANCED SETTINGS")
    print("="*60)
    
    if not get_yes_no("Configure advanced settings?", False):
        return {}
    
    settings = {}
    
    # Timeout
    timeout_str = get_user_input("Connection timeout (seconds)", "10", False)
    if timeout_str:
        try:
            settings['timeout'] = int(timeout_str)
        except ValueError:
            print("⚠️ Invalid timeout value, using default")
    
    # Retry count
    retry_str = get_user_input("Retry count", "3", False)
    if retry_str:
        try:
            settings['retry_count'] = int(retry_str)
        except ValueError:
            print("⚠️ Invalid retry count, using default")
    
    return settings

def display_summary(device_info: Dict, protocol_info: Dict, advanced_settings: Dict):
    """Display configuration summary"""
    print("\n" + "="*60)
    print("📋 CONFIGURATION SUMMARY")
    print("="*60)
    
    print(f"Device ID: {device_info['id']}")
    print(f"Name: {device_info['name']}")
    print(f"Host: {device_info['host']}")
    print(f"Type: {device_info['device_type']}")
    print(f"Description: {device_info['description']}")
    print(f"Protocols: {', '.join(protocol_info['protocols'])}")
    
    if protocol_info['credentials']:
        print("Credentials:")
        for key, value in protocol_info['credentials'].items():
            if 'password' in key.lower() or 'token' in key.lower() or 'key' in key.lower():
                print(f"  {key}: [HIDDEN]")
            else:
                print(f"  {key}: {value}")
    
    if advanced_settings:
        print("Advanced Settings:")
        for key, value in advanced_settings.items():
            print(f"  {key}: {value}")

def main():
    """Main function"""
    print("🚀 Network Device Setup Wizard")
    print("="*60)
    print("This wizard will help you add a network device to the monitoring configuration.")
    print()
    
    config_path = "device_configs/devices.yaml"
    
    # Load existing configuration
    config = load_existing_config(config_path)
    
    # Show existing devices
    if config.get('devices'):
        print("📋 Existing devices:")
        for device_id, device_config in config['devices'].items():
            print(f"  - {device_id}: {device_config.get('name', 'Unknown')} ({device_config.get('host', 'Unknown')})")
        print()
    
    # Collect device information
    device_info = collect_device_info()
    
    # Check if device ID already exists
    if device_info['id'] in config.get('devices', {}):
        if not get_yes_no(f"Device '{device_info['id']}' already exists. Overwrite?", False):
            print("❌ Cancelled")
            return
    
    # Collect protocol information
    protocol_info = collect_protocol_info()
    
    # Collect advanced settings
    advanced_settings = collect_advanced_settings()
    
    # Display summary
    display_summary(device_info, protocol_info, advanced_settings)
    
    # Confirm and save
    if not get_yes_no("\nSave this configuration?", True):
        print("❌ Cancelled")
        return
    
    # Build device configuration
    device_config = {
        'name': device_info['name'],
        'host': device_info['host'],
        'device_type': device_info['device_type'],
        'description': device_info['description'],
        'enabled_protocols': protocol_info['protocols'],
        'credentials': protocol_info['credentials']
    }
    
    # Add advanced settings
    device_config.update(advanced_settings)
    
    # Add to configuration
    if 'devices' not in config:
        config['devices'] = {}
    config['devices'][device_info['id']] = device_config
    
    # Save configuration
    save_config(config, config_path)
    
    print("\n" + "="*60)
    print("✅ DEVICE ADDED SUCCESSFULLY!")
    print("="*60)
    print(f"Device '{device_info['id']}' has been added to the configuration.")
    print("\nNext steps:")
    print("1. Start or restart the monitoring service")
    print("2. Test the device connection:")
    print(f"   python test_device_monitoring.py")
    print("3. Set up environment variables for sensitive credentials")
    
    if protocol_info['credentials']:
        print("\n💡 Environment variable examples:")
        device_id_upper = device_info['id'].upper().replace('-', '_')
        if 'snmp_community' in protocol_info['credentials']:
            print(f"   export {device_id_upper}_SNMP_COMMUNITY=your_community")
        if 'username' in protocol_info['credentials']:
            print(f"   export {device_id_upper}_PASSWORD=your_password")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1) 