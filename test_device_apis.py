#!/usr/bin/env python3
"""
Test script for Device Monitoring APIs
Tests the new CRUD operations and discovery features
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000/devices"

def test_device_crud():
    """Test device CRUD operations"""
    print("🧪 Testing Device CRUD Operations...")
    
    # 1. Create a device
    print("\n1. Creating a new device...")
    create_payload = {
        "name": "Test Router",
        "host": "192.168.1.1",
        "device_type": "router",
        "enabled_protocols": ["snmp", "ssh"],
        "credentials": {
            "snmp_community": "public",
            "username": "admin"
        },
        "description": "Test device for API validation"
    }
    
    response = requests.post(f"{BASE_URL}/", json=create_payload)
    if response.status_code == 201:
        device = response.json()
        device_id = device['id']
        print(f"✅ Device created successfully: {device_id}")
        print(f"   Name: {device['name']}")
        print(f"   Host: {device['host']}")
        print(f"   Type: {device['device_type']}")
    else:
        print(f"❌ Failed to create device: {response.status_code}")
        print(response.text)
        return None
    
    # 2. Get the device
    print(f"\n2. Retrieving device {device_id}...")
    response = requests.get(f"{BASE_URL}/{device_id}")
    if response.status_code == 200:
        device = response.json()
        print(f"✅ Device retrieved successfully")
        print(f"   Name: {device['name']}")
        print(f"   Host: {device['host']}")
    else:
        print(f"❌ Failed to retrieve device: {response.status_code}")
    
    # 3. Update the device
    print(f"\n3. Updating device {device_id}...")
    update_payload = {
        "name": "Updated Test Router",
        "description": "Updated description for testing"
    }
    
    response = requests.put(f"{BASE_URL}/{device_id}", json=update_payload)
    if response.status_code == 200:
        device = response.json()
        print(f"✅ Device updated successfully")
        print(f"   New Name: {device['name']}")
        print(f"   New Description: {device['description']}")
    else:
        print(f"❌ Failed to update device: {response.status_code}")
        print(response.text)
    
    # 4. List all devices
    print(f"\n4. Listing all devices...")
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        devices = response.json()
        print(f"✅ Found {len(devices)} devices")
        for device in devices:
            print(f"   - {device['id']}: {device['name']} ({device['host']})")
    else:
        print(f"❌ Failed to list devices: {response.status_code}")
    
    # 5. Delete the device
    print(f"\n5. Deleting device {device_id}...")
    response = requests.delete(f"{BASE_URL}/{device_id}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Device deleted successfully: {result['message']}")
    else:
        print(f"❌ Failed to delete device: {response.status_code}")
        print(response.text)
    
    return device_id

def test_discovery_operations():
    """Test discovery operations"""
    print("\n🔍 Testing Discovery Operations...")
    
    # 1. Start a discovery scan
    print("\n1. Starting discovery scan...")
    discovery_payload = {
        "network": "192.168.1.0/24",
        "scan_type": "ping",
        "timeout": 2,
        "max_concurrent": 10
    }
    
    response = requests.post(f"{BASE_URL}/discovery/scan", json=discovery_payload)
    if response.status_code == 200:
        scan_result = response.json()
        scan_id = scan_result['scan_id']
        print(f"✅ Discovery scan started: {scan_id}")
        print(f"   Network: {scan_result['network']}")
        print(f"   Type: {scan_result['scan_type']}")
        print(f"   Status: {scan_result['status']}")
    else:
        print(f"❌ Failed to start discovery scan: {response.status_code}")
        print(response.text)
        return None
    
    # 2. Check scan status
    print(f"\n2. Checking scan status...")
    max_attempts = 10
    for attempt in range(max_attempts):
        response = requests.get(f"{BASE_URL}/discovery/scan/{scan_id}")
        if response.status_code == 200:
            scan_status = response.json()
            print(f"   Attempt {attempt + 1}: Status = {scan_status['status']}")
            
            if scan_status['status'] == 'completed':
                print(f"✅ Scan completed successfully!")
                print(f"   Discovered devices: {len(scan_status['discovered_devices'])}")
                for device in scan_status['discovered_devices']:
                    print(f"     - {device['ip']} (RT: {device.get('response_time', 'N/A')}ms)")
                break
            elif scan_status['status'] == 'failed':
                print(f"❌ Scan failed: {scan_status.get('error_message', 'Unknown error')}")
                break
            else:
                time.sleep(2)  # Wait before next check
        else:
            print(f"❌ Failed to get scan status: {response.status_code}")
            break
    else:
        print(f"⏰ Scan still running after {max_attempts} attempts")
    
    # 3. Get scan results
    print(f"\n3. Getting scan results...")
    response = requests.get(f"{BASE_URL}/discovery/scan/{scan_id}/results")
    if response.status_code == 200:
        results = response.json()
        print(f"✅ Scan results retrieved")
        print(f"   Total devices: {results['summary']['total_devices']}")
        if 'device_types' in results['summary']:
            print(f"   Device types: {results['summary']['device_types']}")
        if 'protocols' in results['summary']:
            print(f"   Protocols: {results['summary']['protocols']}")
    else:
        print(f"❌ Failed to get scan results: {response.status_code}")
    
    # 4. Get scan history
    print(f"\n4. Getting scan history...")
    response = requests.get(f"{BASE_URL}/discovery/history")
    if response.status_code == 200:
        history = response.json()
        print(f"✅ Found {len(history)} scans in history")
        for scan in history[:3]:  # Show first 3
            print(f"   - {scan['scan_id'][:8]}... ({scan['network']}) - {scan['status']}")
    else:
        print(f"❌ Failed to get scan history: {response.status_code}")
    
    return scan_id

def test_bulk_operations():
    """Test bulk operations"""
    print("\n📦 Testing Bulk Operations...")
    
    # 1. Bulk create devices
    print("\n1. Bulk creating devices...")
    bulk_payload = {
        "devices": [
            {
                "name": "Bulk Device 1",
                "host": "192.168.1.10",
                "device_type": "switch",
                "enabled_protocols": ["snmp"]
            },
            {
                "name": "Bulk Device 2",
                "host": "192.168.1.11",
                "device_type": "router",
                "enabled_protocols": ["ssh", "snmp"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/bulk", json=bulk_payload)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Bulk creation completed")
        print(f"   Created: {result['summary']['successfully_created']}")
        print(f"   Failed: {result['summary']['failed']}")
        
        # Store device IDs for cleanup
        device_ids = [device['id'] for device in result['created']]
        
        # Clean up created devices
        print("\n   Cleaning up bulk created devices...")
        for device_id in device_ids:
            response = requests.delete(f"{BASE_URL}/{device_id}")
            if response.status_code == 200:
                print(f"   ✅ Deleted {device_id}")
            else:
                print(f"   ❌ Failed to delete {device_id}")
    else:
        print(f"❌ Failed bulk creation: {response.status_code}")
        print(response.text)

def test_config_export_import():
    """Test configuration export/import"""
    print("\n📋 Testing Configuration Export/Import...")
    
    # 1. Export configuration
    print("\n1. Exporting device configuration...")
    response = requests.get(f"{BASE_URL}/config/export")
    if response.status_code == 200:
        config = response.json()
        print(f"✅ Configuration exported successfully")
        print(f"   Devices: {len(config['devices'])}")
        print(f"   Version: {config['version']}")
        print(f"   Timestamp: {config['export_timestamp']}")
        
        # Save for import test
        exported_config = config
    else:
        print(f"❌ Failed to export configuration: {response.status_code}")
        return
    
    # 2. Test import (merge strategy)
    print("\n2. Testing configuration import...")
    import_payload = {
        "devices": exported_config['devices'],
        "global_settings": exported_config['global_settings'],
        "merge_strategy": "merge"
    }
    
    response = requests.post(f"{BASE_URL}/config/import", json=import_payload)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Configuration imported successfully")
        print(f"   Message: {result['message']}")
        print(f"   Strategy: {result['merge_strategy']}")
    else:
        print(f"❌ Failed to import configuration: {response.status_code}")
        print(response.text)

def main():
    """Run all tests"""
    print("🚀 Starting Device Monitoring API Tests")
    print("=" * 50)
    
    try:
        # Test basic connectivity
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ API is healthy: {health['status']}")
            print(f"   Configured devices: {health['configured_devices']}")
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return
        
        # Run tests
        test_device_crud()
        test_discovery_operations()
        test_bulk_operations()
        test_config_export_import()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to API. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main() 