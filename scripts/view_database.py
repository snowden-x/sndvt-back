#!/usr/bin/env python3
"""
Database Viewer Script
View and manage the SQLite database contents
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

from device_monitoring.models.database import DatabaseManager


def print_separator(title: str = ""):
    """Print a separator line with optional title"""
    if title:
        print(f"\n{'='*20} {title} {'='*20}")
    else:
        print("="*60)


async def list_devices(db: DatabaseManager):
    """List all devices in the database"""
    devices = await db.get_all_devices()
    
    if not devices:
        print("📭 No devices found in database")
        return
    
    print_separator("DEVICES")
    print(f"Found {len(devices)} devices:")
    
    for device in devices:
        status_indicator = "🟢" if device.enabled else "🔴"
        print(f"\n{status_indicator} {device.name} ({device.id})")
        print(f"   Host: {device.host}")
        print(f"   Type: {device.device_type}")
        print(f"   Protocols: {', '.join(device.enabled_protocols)}")
        print(f"   Description: {device.description[:60]}{'...' if len(device.description) > 60 else ''}")
        print(f"   Created: {device.created_at}")
        if device.updated_at != device.created_at:
            print(f"   Updated: {device.updated_at}")


async def show_device_details(db: DatabaseManager, device_id: str):
    """Show detailed information about a specific device"""
    device = await db.get_device(device_id)
    
    if not device:
        print(f"❌ Device '{device_id}' not found")
        return
    
    print_separator(f"DEVICE DETAILS: {device.name}")
    print(f"ID: {device.id}")
    print(f"Name: {device.name}")
    print(f"Host: {device.host}")
    print(f"Type: {device.device_type}")
    print(f"Description: {device.description}")
    print(f"Enabled: {'Yes' if device.enabled else 'No'}")
    print(f"Protocols: {', '.join(device.enabled_protocols)}")
    print(f"Timeout: {device.timeout}s")
    print(f"Retry Count: {device.retry_count}")
    print(f"Created: {device.created_at}")
    print(f"Updated: {device.updated_at}")
    
    print("\nCredentials:")
    for key, value in device.credentials.items():
        if 'password' in key.lower() or 'secret' in key.lower():
            print(f"  {key}: ***hidden***")
        else:
            print(f"  {key}: {value}")
    
    # Show device status
    status = await db.get_device_status(device_id)
    if status:
        print(f"\nStatus:")
        print(f"  Current Status: {status.status}")
        print(f"  Last Seen: {status.last_seen}")
        if status.response_time:
            print(f"  Response Time: {status.response_time}ms")
        if status.error_message:
            print(f"  Last Error: {status.error_message}")
    
    # Show recent metrics
    metrics = await db.get_device_metrics(device_id, hours=24)
    if metrics:
        print(f"\nRecent Metrics (last 24h): {len(metrics)} entries")
        metric_types = set(m.metric_type for m in metrics[:10])
        for metric_type in sorted(metric_types):
            latest = next(m for m in metrics if m.metric_type == metric_type)
            print(f"  {metric_type}: {latest.value} {latest.unit} (at {latest.timestamp})")


async def list_device_status(db: DatabaseManager):
    """List status of all devices"""
    statuses = await db.get_all_device_status()
    
    if not statuses:
        print("📭 No device status information found")
        return
    
    print_separator("DEVICE STATUS")
    print(f"Status for {len(statuses)} devices:")
    
    for status in statuses:
        status_icon = {"online": "🟢", "offline": "🔴", "unknown": "🟡"}.get(status.status, "❓")
        print(f"\n{status_icon} {status.device_id}")
        print(f"   Status: {status.status}")
        print(f"   Last Seen: {status.last_seen}")
        if status.response_time:
            print(f"   Response Time: {status.response_time}ms")
        if status.error_message:
            print(f"   Error: {status.error_message}")


async def view_discovery_history(db: DatabaseManager):
    """View discovery history"""
    import aiosqlite
    
    async with aiosqlite.connect(db.db_path) as connection:
        async with connection.execute("""
            SELECT network_range, discovered_at, results 
            FROM discovery_results 
            ORDER BY discovered_at DESC 
            LIMIT 10
        """) as cursor:
            rows = await cursor.fetchall()
    
    if not rows:
        print("📭 No discovery results found")
        return
    
    print_separator("DISCOVERY HISTORY")
    print(f"Last {len(rows)} discovery scans:")
    
    for row in rows:
        network_range, discovered_at, results_json = row
        results = json.loads(results_json)
        
        print(f"\n📡 {network_range}")
        print(f"   Discovered: {discovered_at}")
        print(f"   Found {len(results)} devices")
        
        # Show first few devices
        for i, device in enumerate(results[:3]):
            print(f"   - {device['ip']} ({device.get('hostname', 'Unknown')}) [{device['device_type']}]")
        
        if len(results) > 3:
            print(f"   ... and {len(results) - 3} more")


async def cleanup_old_data(db: DatabaseManager):
    """Clean up old metrics data"""
    print("🧹 Cleaning up old metrics data...")
    
    days = input("Delete metrics older than how many days? [30]: ").strip()
    if not days:
        days = 30
    else:
        try:
            days = int(days)
        except ValueError:
            print("❌ Invalid number, using 30 days")
            days = 30
    
    deleted_count = await db.cleanup_old_metrics(days)
    print(f"✅ Deleted {deleted_count} old metric entries")


async def delete_device(db: DatabaseManager):
    """Delete a device from the database"""
    devices = await db.get_all_devices()
    if not devices:
        print("📭 No devices to delete")
        return
    
    print("\nDevices in database:")
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device.name} ({device.id}) - {device.host}")
    
    choice = input(f"\nEnter device number to delete [1-{len(devices)}] or 'cancel': ").strip()
    
    if choice.lower() == 'cancel':
        return
    
    try:
        device_idx = int(choice) - 1
        if 0 <= device_idx < len(devices):
            device = devices[device_idx]
            
            confirm = input(f"⚠️ Are you sure you want to delete '{device.name}' ({device.host})? [y/N]: ").strip().lower()
            if confirm in ['y', 'yes']:
                success = await db.delete_device(device.id)
                if success:
                    print(f"✅ Deleted device: {device.name}")
                else:
                    print(f"❌ Failed to delete device: {device.name}")
            else:
                print("Delete cancelled")
        else:
            print("❌ Invalid device number")
    except ValueError:
        print("❌ Invalid input")


async def main():
    """Main function"""
    db = DatabaseManager()
    await db.initialize()
    
    while True:
        print_separator("DATABASE VIEWER")
        print("1. List all devices")
        print("2. Show device details")
        print("3. View device status")
        print("4. View discovery history")
        print("5. Cleanup old metrics")
        print("6. Delete device")
        print("7. Database statistics")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        try:
            if choice == "0":
                break
            elif choice == "1":
                await list_devices(db)
            elif choice == "2":
                device_id = input("Enter device ID: ").strip()
                if device_id:
                    await show_device_details(db, device_id)
            elif choice == "3":
                await list_device_status(db)
            elif choice == "4":
                await view_discovery_history(db)
            elif choice == "5":
                await cleanup_old_data(db)
            elif choice == "6":
                await delete_device(db)
            elif choice == "7":
                await show_database_stats(db)
            else:
                print("❌ Invalid choice")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        input("\nPress Enter to continue...")


async def show_database_stats(db: DatabaseManager):
    """Show database statistics"""
    import aiosqlite
    
    print_separator("DATABASE STATISTICS")
    
    async with aiosqlite.connect(db.db_path) as connection:
        # Device count
        async with connection.execute("SELECT COUNT(*) FROM devices") as cursor:
            device_count = (await cursor.fetchone())[0]
        
        # Enabled device count
        async with connection.execute("SELECT COUNT(*) FROM devices WHERE enabled = 1") as cursor:
            enabled_count = (await cursor.fetchone())[0]
        
        # Metrics count
        async with connection.execute("SELECT COUNT(*) FROM device_metrics") as cursor:
            metrics_count = (await cursor.fetchone())[0]
        
        # Discovery results count
        async with connection.execute("SELECT COUNT(*) FROM discovery_results") as cursor:
            discovery_count = (await cursor.fetchone())[0]
        
        # Database size
        db_size = os.path.getsize(db.db_path) if os.path.exists(db.db_path) else 0
        db_size_mb = db_size / (1024 * 1024)
    
    print(f"📊 Database file: {db.db_path}")
    print(f"📊 Database size: {db_size_mb:.2f} MB")
    print(f"📊 Total devices: {device_count}")
    print(f"📊 Enabled devices: {enabled_count}")
    print(f"📊 Total metrics: {metrics_count:,}")
    print(f"📊 Discovery scans: {discovery_count}")


if __name__ == "__main__":
    asyncio.run(main()) 