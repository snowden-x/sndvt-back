#!/usr/bin/env python3
"""
Network Discovery Script
Discovers devices on the network and saves them to the database
"""

import asyncio
import sys
import os
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

from typing import List, Dict, Any
from device_monitoring.services.discovery import NetworkDiscovery
from device_monitoring.models.database import DatabaseManager, Device

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
        print(f"   Protocols: {', '.join(device['protocols'])}")
        
        if device.get('snmp_details', {}).get('system_description'):
            desc = device['snmp_details']['system_description'][:80] + "..." if len(device['snmp_details']['system_description']) > 80 else device['snmp_details']['system_description']
            print(f"   Description: {desc}")
        
        if get_yes_no("Add this device to database?", True):
            selected_devices.append(device)
    
    return selected_devices

def customize_device_config(device: Dict[str, Any]) -> Device:
    """Allow user to customize device configuration"""
    print(f"\n⚙️ CUSTOMIZE DEVICE: {device['ip']}")
    print("=" * 50)
    
    # Generate default device ID
    hostname = device.get('hostname', '').replace('.', '-').replace('_', '-')
    if hostname and hostname != 'Unknown' and hostname != device['ip']:
        default_id = f"{hostname}-{device['ip'].replace('.', '-')}"
    else:
        default_id = f"device-{device['ip'].replace('.', '-')}"
    
    # Clean up device ID
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
    suggested_protocols = device.get('protocols', ['snmp'])
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
        if device.get('snmp_details', {}).get('community'):
            credentials['snmp_community'] = device['snmp_details']['community']
        else:
            community = get_user_input("SNMP Community", "public")
            credentials['snmp_community'] = community
    
    # Description
    default_desc = device.get('snmp_details', {}).get('system_description', f"Auto-discovered {device_type}")[:100]
    description = get_user_input("Description", default_desc)
    
    return Device(
        id=device_id,
        name=device_name,
        host=device['ip'],
        device_type=device_type,
        description=description,
        enabled_protocols=protocols,
        credentials=credentials,
        timeout=10,
        retry_count=3,
        enabled=True
    )

async def main():
    """Main discovery function"""
    print("🌐 Network Discovery Tool")
    print("=" * 60)
    print("This tool will discover devices on your network and save them to the database.")
    print()
    
    # Initialize database
    db = DatabaseManager()
    await db.initialize()
    print("✅ Database initialized")
    
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
        
        # Save discovery results to database
        await db.save_discovery_result(network, devices)
        print(f"💾 Discovery results saved to database")
        
        # Ask if user wants to add devices to monitoring
        if not get_yes_no(f"\nAdd discovered devices to monitoring database?", True):
            print("Discovery complete. No devices added to monitoring.")
            return
        
        # Let user select devices to add
        if get_yes_no("Select individual devices to add?", True):
            selected_devices = select_devices_to_add(devices)
        else:
            selected_devices = devices
        
        if not selected_devices:
            print("No devices selected. Exiting.")
            return
        
        # Add selected devices to database
        added_count = 0
        skipped_count = 0
        
        for device_data in selected_devices:
            print(f"\n📝 Processing device: {device_data['ip']}")
            
            # Check if device already exists
            existing_devices = await db.get_all_devices()
            existing_hosts = [d.host for d in existing_devices]
            
            if device_data['ip'] in existing_hosts:
                print(f"⚠️ Device {device_data['ip']} already exists in database")
                if not get_yes_no("Update existing device?", False):
                    skipped_count += 1
                    continue
            
            # Customize device configuration
            if get_yes_no("Customize device configuration?", False):
                device = customize_device_config(device_data)
            else:
                # Use auto-generated configuration
                hostname = device_data.get('hostname', device_data['ip'])
                if hostname == device_data['ip']:
                    device_id = f"device-{device_data['ip'].replace('.', '-')}"
                    device_name = device_data['ip']
                else:
                    device_id = f"{hostname.replace('.', '-')}-{device_data['ip'].replace('.', '-')}"
                    device_name = hostname
                
                device_id = re.sub(r'[^a-zA-Z0-9\-]', '', device_id).lower()
                
                credentials = {}
                if 'snmp' in device_data['protocols']:
                    credentials['snmp_version'] = '2c'
                    credentials['snmp_community'] = device_data.get('snmp_details', {}).get('community', 'public')
                
                device = Device(
                    id=device_id,
                    name=device_name,
                    host=device_data['ip'],
                    device_type=device_data['device_type'],
                    description=device_data.get('snmp_details', {}).get('system_description', f"Auto-discovered {device_data['device_type']}")[:100],
                    enabled_protocols=device_data['protocols'],
                    credentials=credentials,
                    timeout=10,
                    retry_count=3,
                    enabled=True
                )
            
            # Add or update device in database
            if device_data['ip'] in existing_hosts:
                # Update existing device
                existing_device = next(d for d in existing_devices if d.host == device_data['ip'])
                device.id = existing_device.id  # Keep existing ID
                success = await db.update_device(device)
                action = "Updated"
            else:
                # Add new device
                success = await db.add_device(device)
                action = "Added"
            
            if success:
                print(f"✅ {action} device: {device.name} ({device.host})")
                added_count += 1
            else:
                print(f"❌ Failed to {action.lower()} device: {device.host}")
                skipped_count += 1
        
        print(f"\n🎉 Discovery and import complete!")
        print(f"✅ Devices processed: {added_count}")
        if skipped_count > 0:
            print(f"⚠️ Devices skipped: {skipped_count}")
        
        # Show current device count
        all_devices = await db.get_all_devices()
        print(f"📊 Total devices in database: {len(all_devices)}")
        
    except KeyboardInterrupt:
        print("\n❌ Discovery interrupted by user")
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        import traceback
        traceback.print_exc()
    finally:
        discovery.close()

if __name__ == "__main__":
    asyncio.run(main()) 