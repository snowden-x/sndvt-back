#!/usr/bin/env python3
"""Debug script for Ansible execution."""

import asyncio
import subprocess
import tempfile
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.network_automation.services.ansible_service import AnsibleService


async def debug_ansible():
    """Debug Ansible execution."""
    print("🔍 Debugging Ansible execution...")
    
    try:
        # Initialize Ansible service
        ansible_service = AnsibleService()
        
        # Test 1: Check if ansible-playbook is available
        print("1️⃣ Testing ansible-playbook availability...")
        try:
            result = subprocess.run(['ansible-playbook', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            print(f"✅ Ansible version: {result.stdout.split('\n')[0]}")
        except Exception as e:
            print(f"❌ Ansible not found: {e}")
            return
        
        # Test 2: Check if we can create a simple inventory
        print("2️⃣ Testing inventory creation...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("""all:
  hosts:
    localhost:
      ansible_connection: local
      ansible_host: 127.0.0.1
""")
            inventory_file = f.name
        
        print(f"✅ Created inventory file: {inventory_file}")
        
        # Test 3: Test simple ping module
        print("3️⃣ Testing simple ping...")
        cmd = ['ansible', 'localhost', '-i', inventory_file, '-m', 'ping']
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        # Test 4: Test playbook execution
        print("4️⃣ Testing playbook execution...")
        playbook_path = "ansible/playbooks/troubleshooting/simple_ping_test.yml"
        
        if os.path.exists(playbook_path):
            print(f"✅ Playbook exists: {playbook_path}")
            
            cmd = ['ansible-playbook', '-i', inventory_file, playbook_path, '-v']
            print(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            print(f"Return code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
        else:
            print(f"❌ Playbook not found: {playbook_path}")
        
        # Cleanup
        os.unlink(inventory_file)
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_ansible()) 