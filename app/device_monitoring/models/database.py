"""
Database models and schema for device monitoring
"""

import sqlite3
import asyncio
import aiosqlite
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class Device:
    """Device model"""
    id: str
    name: str
    host: str
    device_type: str
    description: str
    enabled_protocols: List[str]
    credentials: Dict[str, Any]
    timeout: int = 10
    retry_count: int = 3
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DeviceMetric:
    """Device metric model"""
    device_id: str
    metric_type: str
    value: float
    unit: str
    timestamp: Optional[datetime] = None


@dataclass
class DeviceStatus:
    """Device status model"""
    device_id: str
    status: str  # 'online', 'offline', 'unknown'
    last_seen: datetime
    response_time: Optional[float] = None
    error_message: Optional[str] = None


class DatabaseManager:
    """SQLite database manager for device monitoring"""
    
    def __init__(self, db_path: str = "data/device_monitoring.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize database and create tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all necessary tables"""
        
        # Devices table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                host TEXT NOT NULL UNIQUE,
                device_type TEXT NOT NULL,
                description TEXT,
                enabled_protocols TEXT NOT NULL,  -- JSON array
                credentials TEXT NOT NULL,        -- JSON object
                timeout INTEGER DEFAULT 10,
                retry_count INTEGER DEFAULT 3,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Device metrics table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS device_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE
            )
        """)
        
        # Device status table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS device_status (
                device_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                response_time REAL,
                error_message TEXT,
                FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE
            )
        """)
        
        # Discovery results table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discovery_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_range TEXT NOT NULL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                results TEXT NOT NULL  -- JSON object with discovery data
            )
        """)
        
        # Create indexes for performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_device_time ON device_metrics(device_id, timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type ON device_metrics(metric_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_devices_host ON devices(host)")
        
        await db.commit()
    
    # Device CRUD operations
    async def add_device(self, device: Device) -> bool:
        """Add a new device to the database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO devices 
                    (id, name, host, device_type, description, enabled_protocols, credentials, timeout, retry_count, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device.id,
                    device.name,
                    device.host,
                    device.device_type,
                    device.description,
                    json.dumps(device.enabled_protocols),
                    json.dumps(device.credentials),
                    device.timeout,
                    device.retry_count,
                    device.enabled
                ))
                await db.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    async def get_device(self, device_id: str) -> Optional[Device]:
        """Get a device by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_device(row)
                return None
    
    async def get_all_devices(self, enabled_only: bool = False) -> List[Device]:
        """Get all devices"""
        query = "SELECT * FROM devices"
        params = ()
        
        if enabled_only:
            query += " WHERE enabled = 1"
        
        query += " ORDER BY name"
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_device(row) for row in rows]
    
    async def update_device(self, device: Device) -> bool:
        """Update an existing device"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE devices SET 
                    name = ?, host = ?, device_type = ?, description = ?,
                    enabled_protocols = ?, credentials = ?, timeout = ?, 
                    retry_count = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    device.name,
                    device.host,
                    device.device_type,
                    device.description,
                    json.dumps(device.enabled_protocols),
                    json.dumps(device.credentials),
                    device.timeout,
                    device.retry_count,
                    device.enabled,
                    device.id
                ))
                await db.commit()
                return True
        except sqlite3.Error:
            return False
    
    async def delete_device(self, device_id: str) -> bool:
        """Delete a device and all its associated data"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
                await db.commit()
                return True
        except sqlite3.Error:
            return False
    
    # Device metrics operations
    async def add_metric(self, metric: DeviceMetric) -> bool:
        """Add a device metric"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO device_metrics (device_id, metric_type, value, unit, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    metric.device_id,
                    metric.metric_type,
                    metric.value,
                    metric.unit,
                    metric.timestamp or datetime.now()
                ))
                await db.commit()
                return True
        except sqlite3.Error:
            return False
    
    async def add_metrics(self, metrics: List[DeviceMetric]) -> bool:
        """Add multiple metrics in a batch"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.executemany("""
                    INSERT INTO device_metrics (device_id, metric_type, value, unit, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    (m.device_id, m.metric_type, m.value, m.unit, m.timestamp or datetime.now())
                    for m in metrics
                ])
                await db.commit()
                return True
        except sqlite3.Error:
            return False
    
    async def get_device_metrics(self, device_id: str, metric_type: str = None, 
                               hours: int = 24) -> List[DeviceMetric]:
        """Get device metrics for the last N hours"""
        query = """
            SELECT device_id, metric_type, value, unit, timestamp 
            FROM device_metrics 
            WHERE device_id = ? AND timestamp > datetime('now', '-{} hours')
        """.format(hours)
        
        params = [device_id]
        
        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)
        
        query += " ORDER BY timestamp DESC"
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    DeviceMetric(
                        device_id=row[0],
                        metric_type=row[1],
                        value=row[2],
                        unit=row[3],
                        timestamp=datetime.fromisoformat(row[4])
                    )
                    for row in rows
                ]
    
    # Device status operations
    async def update_device_status(self, status: DeviceStatus) -> bool:
        """Update device status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO device_status 
                    (device_id, status, last_seen, response_time, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    status.device_id,
                    status.status,
                    status.last_seen,
                    status.response_time,
                    status.error_message
                ))
                await db.commit()
                return True
        except sqlite3.Error:
            return False
    
    async def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        """Get device status"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT device_id, status, last_seen, response_time, error_message
                FROM device_status WHERE device_id = ?
            """, (device_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return DeviceStatus(
                        device_id=row[0],
                        status=row[1],
                        last_seen=datetime.fromisoformat(row[2]),
                        response_time=row[3],
                        error_message=row[4]
                    )
                return None
    
    async def get_all_device_status(self) -> List[DeviceStatus]:
        """Get status for all devices"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT device_id, status, last_seen, response_time, error_message
                FROM device_status ORDER BY last_seen DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [
                    DeviceStatus(
                        device_id=row[0],
                        status=row[1],
                        last_seen=datetime.fromisoformat(row[2]),
                        response_time=row[3],
                        error_message=row[4]
                    )
                    for row in rows
                ]
    
    # Discovery operations
    async def save_discovery_result(self, network_range: str, results: List[Dict[str, Any]]) -> bool:
        """Save discovery results"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO discovery_results (network_range, results)
                    VALUES (?, ?)
                """, (network_range, json.dumps(results)))
                await db.commit()
                return True
        except sqlite3.Error:
            return False
    
    # Utility methods
    def _row_to_device(self, row) -> Device:
        """Convert database row to Device object"""
        return Device(
            id=row[0],
            name=row[1],
            host=row[2],
            device_type=row[3],
            description=row[4],
            enabled_protocols=json.loads(row[5]),
            credentials=json.loads(row[6]),
            timeout=row[7],
            retry_count=row[8],
            enabled=bool(row[9]),
            created_at=datetime.fromisoformat(row[10]) if row[10] else None,
            updated_at=datetime.fromisoformat(row[11]) if row[11] else None
        )
    
    async def cleanup_old_metrics(self, days: int = 30) -> int:
        """Clean up metrics older than specified days"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM device_metrics 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            await db.commit()
            return cursor.rowcount


# Global database instance
db_manager = DatabaseManager() 