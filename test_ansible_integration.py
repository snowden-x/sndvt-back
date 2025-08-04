#!/usr/bin/env python3
"""Test script for Ansible integration."""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.network_automation.services.ansible_service import AnsibleService
from app.network_automation.services.playbook_service import PlaybookService
from app.network_automation.models.playbook import PlaybookExecuteRequest


async def test_ansible_integration():
    """Test the Ansible integration."""
    print("🧪 Testing Ansible Integration...")
    
    try:
        # Initialize services
        print("📦 Initializing Ansible service...")
        ansible_service = AnsibleService()
        
        print("📦 Initializing Playbook service...")
        playbook_service = PlaybookService(ansible_service)
        
        # Test getting available playbooks
        print("📋 Getting available playbooks...")
        playbooks = await ansible_service.get_available_playbooks()
        print(f"✅ Found {len(playbooks)} playbooks:")
        for playbook in playbooks:
            print(f"   - {playbook.name}: {playbook.description}")
        
        # Test safety validation
        if playbooks:
            print(f"🔒 Testing safety validation for {playbooks[0].name}...")
            safety_check = await ansible_service.validate_playbook_safety(playbooks[0].name)
            print(f"✅ Safety check: {safety_check.is_safe} (Risk: {safety_check.risk_level})")
        
        # Test ping functionality
        print("🏓 Testing ping functionality...")
        ping_result = await playbook_service.ping_test("localhost")
        print(f"✅ Ping test result: {ping_result}")
        
        # Test print server check
        print("🖨️ Testing print server check...")
        print_result = await playbook_service.check_print_server("localhost")
        print(f"✅ Print server check result: {print_result}")
        
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ansible_integration()) 