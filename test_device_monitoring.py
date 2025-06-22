#!/usr/bin/env python3
"""
Test script for device monitoring functionality
"""

import asyncio
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_api_endpoint(endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Test an API endpoint and return the result"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "url": url
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": str(e),
            "success": False,
            "url": url
        }

def print_test_result(test_name: str, result: Dict[str, Any]):
    """Print formatted test result"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    
    if result.get("success"):
        print(f"✅ SUCCESS - Status: {result.get('status_code')}")
        if result.get("data"):
            print(f"📊 Response:")
            print(json.dumps(result["data"], indent=2))
    else:
        print(f"❌ FAILED - Status: {result.get('status_code', 'N/A')}")
        if result.get("error"):
            print(f"🚨 Error: {result['error']}")
        elif result.get("data"):
            print(f"📊 Response:")
            print(json.dumps(result["data"], indent=2))

def main():
    """Run all device monitoring tests"""
    print("🧪 Device Monitoring API Test Suite")
    print("=" * 60)
    
    # Test 1: Health check
    result = test_api_endpoint("/devices/health")
    print_test_result("Device Monitoring Health Check", result)
    
    # Test 2: List devices
    result = test_api_endpoint("/devices/")
    print_test_result("List All Devices", result)
    
    if result.get("success") and result.get("data"):
        devices = result["data"]
        if devices:
            # Use the first device for subsequent tests
            device_id = devices[0]["id"]
            print(f"\n🎯 Using device '{device_id}' for detailed tests...")
            
            # Test 3: Get device status
            result = test_api_endpoint(f"/devices/{device_id}/status")
            print_test_result(f"Get Device Status - {device_id}", result)
            
            # Test 4: Test device connection
            result = test_api_endpoint(f"/devices/{device_id}/test")
            print_test_result(f"Test Device Connection - {device_id}", result)
            
            # Test 5: Get device interfaces
            result = test_api_endpoint(f"/devices/{device_id}/interfaces")
            print_test_result(f"Get Device Interfaces - {device_id}", result)
            
            # Test 6: Get device health
            result = test_api_endpoint(f"/devices/{device_id}/health")
            print_test_result(f"Get Device Health - {device_id}", result)
            
            # Test 7: Ping device
            result = test_api_endpoint(f"/devices/{device_id}/ping", method="POST")
            print_test_result(f"Ping Device - {device_id}", result)
        else:
            print("\n⚠️ No devices configured - skipping device-specific tests")
    
    # Test 8: Get all device status
    result = test_api_endpoint("/devices/status/all")
    print_test_result("Get All Device Status", result)
    
    # Test 9: Clear cache
    result = test_api_endpoint("/devices/cache", method="DELETE")
    print_test_result("Clear Cache", result)
    
    # Test 10: Reload configurations
    result = test_api_endpoint("/devices/reload", method="POST")
    print_test_result("Reload Device Configurations", result)
    
    # Test 11: Network discovery (example with localhost)
    result = test_api_endpoint("/devices/discovery/127.0.0.1/32")
    print_test_result("Network Discovery - Localhost", result)
    
    print(f"\n{'='*60}")
    print("🏁 Test Suite Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check if any tests failed and investigate")
    print("2. Use the setup scripts to add devices:")
    print("   python setup_device.py")
    print("   python discover_network.py")
    print("3. Update credentials in .env file or device config")
    print("4. Test with real devices that support SNMP")

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running, starting tests...\n")
            main()
        else:
            print(f"❌ Server responded with status {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ Server is not running!")
        print("Please start the server first:")
        print("   python main.py")
        print("   or")
        print("   uvicorn main:app --reload") 