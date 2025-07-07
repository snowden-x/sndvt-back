"""
Advanced Network Discovery Service
Manages discovery scans, results storage, and advanced scanning features
"""

import asyncio
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.device_monitoring.services.discovery import NetworkDiscovery
from app.device_monitoring.models.database import DatabaseManager, Device
from app.device_monitoring.utils.base import DeviceConfig, DeviceCredentials, DeviceType

class ScanResult:
    """Container for scan results"""
    
    def __init__(self, scan_id: str, network: str, scan_type: str):
        self.scan_id = scan_id
        self.network = network
        self.scan_type = scan_type
        self.status = "running"
        self.started_at = datetime.now().isoformat()
        self.completed_at = None
        self.total_hosts = 0
        self.scanned_hosts = 0
        self.discovered_devices = []
        self.error_message = None
        self.scan_name = None
        self.created_by = None

class AdvancedDiscoveryService:
    """Advanced discovery service with scan management and storage"""
    
    def __init__(self, results_dir: str = "data/discovery_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.active_scans: Dict[str, 'ScanResult'] = {}
        self.db_manager = DatabaseManager()
        self._load_scan_history()
    
    def _load_scan_history(self):
        """Load previous scan results from disk"""
        try:
            for result_file in self.results_dir.glob("*.json"):
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    scan_result = ScanResult(data['scan_id'], data['network'], data['scan_type'])
                    scan_result.__dict__.update(data)
                    # Don't load running scans as active
                    if scan_result.status == "running":
                        scan_result.status = "failed"
                        scan_result.error_message = "System restart during scan"
        except Exception as e:
            print(f"Error loading scan history: {e}")
    
    def _save_scan_result(self, scan_result: ScanResult):
        """Save scan result to disk"""
        try:
            result_file = self.results_dir / f"{scan_result.scan_id}.json"
            with open(result_file, 'w') as f:
                json.dump(scan_result.__dict__, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving scan result: {e}")
    
    async def start_discovery_scan(
        self,
        network: str,
        scan_type: str = "ping",
        snmp_communities: List[str] = None,
        ports: List[int] = None,
        timeout: int = 2,
        max_concurrent: int = 50,
        scan_name: str = None,
        save_results: bool = True
    ) -> str:
        """Start a network discovery scan"""
        
        # Generate scan ID
        scan_id = str(uuid.uuid4())
        
        # Create scan result container
        scan_result = ScanResult(scan_id, network, scan_type)
        scan_result.scan_name = scan_name
        self.active_scans[scan_id] = scan_result
        
        # Start scan in background
        asyncio.create_task(self._execute_scan(
            scan_result, snmp_communities, ports, timeout, max_concurrent, save_results
        ))
        
        return scan_id
    
    async def _execute_scan(
        self,
        scan_result: ScanResult,
        snmp_communities: List[str],
        ports: List[int],
        timeout: int,
        max_concurrent: int,
        save_results: bool
    ):
        """Execute the actual discovery scan"""
        
        try:
            discovery = NetworkDiscovery(max_concurrent=max_concurrent, timeout=timeout)
            
            if scan_result.scan_type == "ping":
                # Simple ping scan using nmap -sn for better host discovery
                devices = discovery._run_nmap_ping_scan(scan_result.network)
                scan_result.total_hosts = len(devices)
                scan_result.scanned_hosts = len(devices)
                scan_result.discovered_devices = self._process_simple_ping_results(devices)
                
            elif scan_result.scan_type == "port":
                # Ping sweep + port scan
                ping_results = await discovery.ping_sweep(scan_result.network)
                scan_result.total_hosts = len(ping_results)
                scan_result.scanned_hosts = len(ping_results)
                
                alive_hosts = [device['ip'] for device in ping_results]
                
                if alive_hosts:
                    port_results = await discovery.port_scan(alive_hosts, ports)
                    scan_result.discovered_devices = self._process_port_results(
                        ping_results, port_results
                    )
                
            elif scan_result.scan_type == "full":
                # Full discovery with SNMP
                devices = await discovery.discover_network(
                    scan_result.network, snmp_communities or ["public"]
                )
                scan_result.total_hosts = len(devices)
                scan_result.scanned_hosts = len(devices)
                scan_result.discovered_devices = self._process_full_results(devices)
            
            # Update scan status
            scan_result.status = "completed"
            scan_result.completed_at = datetime.now().isoformat()
            
            # Save results if requested
            if save_results:
                self._save_scan_result(scan_result)
                
        except Exception as e:
            scan_result.status = "failed"
            scan_result.error_message = str(e)
            scan_result.completed_at = datetime.now().isoformat()
            print(f"❌ Scan failed: {e}")
            
            if save_results:
                self._save_scan_result(scan_result)
            
            # Clean up active scans after some time
            await asyncio.sleep(300)  # Keep in memory for 5 minutes
            if scan_result.scan_id in self.active_scans:
                del self.active_scans[scan_result.scan_id]
    
    def _process_ping_results(self, ping_results: List[Dict]) -> List[Dict]:
        """Process ping sweep results"""
        devices = []
        for result in ping_results:
            device = {
                'ip': result['ip'],
                'response_time': result.get('response_time'),
                'open_ports': [],
                'suggested_protocols': ['ping'],
                'device_type': 'unknown',
                'confidence_score': 0.3
            }
            devices.append(device)
        return devices
    
    def _process_simple_ping_results(self, ping_results: List[Dict]) -> List[Dict]:
        """Process simple nmap ping scan results"""
        devices = []
        for result in ping_results:
            device = {
                'ip': result['ip'],
                'hostname': result.get('hostname', result['ip']),
                'response_time': result.get('response_time', 0.0),
                'open_ports': [],
                'suggested_protocols': ['ping', 'snmp'],  # Default protocols to try
                'device_type': 'unknown',
                'confidence_score': 0.4  # Slightly higher confidence for nmap results
            }
            devices.append(device)
        return devices
    
    def _process_port_results(self, ping_results: List[Dict], port_results: Dict) -> List[Dict]:
        """Process ping + port scan results"""
        devices = []
        ping_dict = {r['ip']: r for r in ping_results}
        
        for ip, ports in port_results.items():
            open_ports = [port for port, is_open in ports.items() if is_open]
            
            device = {
                'ip': ip,
                'response_time': ping_dict.get(ip, {}).get('response_time'),
                'open_ports': open_ports,
                'suggested_protocols': self._suggest_protocols_from_ports(open_ports),
                'device_type': self._guess_device_type_from_ports(open_ports),
                'confidence_score': self._calculate_confidence_from_ports(open_ports)
            }
            devices.append(device)
        
        return devices
    
    def _process_full_results(self, discovery_results: List[Dict]) -> List[Dict]:
        """Process full discovery results"""
        devices = []
        for result in discovery_results:
            device = {
                'ip': result.get('ip'),
                'hostname': result.get('hostname'),
                'response_time': result.get('response_time'),
                'open_ports': result.get('open_ports', []),
                'suggested_protocols': result.get('suggested_protocols', []),
                'system_description': result.get('system_description'),
                'device_type': result.get('device_type', 'unknown'),
                'snmp_community': result.get('snmp_community'),
                'confidence_score': result.get('confidence_score', 0.5)
            }
            devices.append(device)
        return devices
    
    def _suggest_protocols_from_ports(self, open_ports: List[int]) -> List[str]:
        """Suggest protocols based on open ports"""
        protocols = []
        
        if 22 in open_ports:
            protocols.append('ssh')
        if 23 in open_ports:
            protocols.append('telnet')
        if 161 in open_ports:
            protocols.append('snmp')
        if 80 in open_ports or 443 in open_ports or 8080 in open_ports:
            protocols.append('rest')
        
        return protocols or ['ping']
    
    def _guess_device_type_from_ports(self, open_ports: List[int]) -> str:
        """Guess device type from open ports"""
        # Network device indicators
        if 161 in open_ports:  # SNMP
            if 22 in open_ports or 23 in open_ports:
                return 'router'  # Likely a managed network device
            return 'switch'
        
        # Server indicators
        if 80 in open_ports or 443 in open_ports:
            return 'server'
        
        # Firewall indicators
        if 22 in open_ports and len(open_ports) <= 2:
            return 'firewall'  # SSH only, minimal services
        
        return 'generic'
    
    def _calculate_confidence_from_ports(self, open_ports: List[int]) -> float:
        """Calculate confidence score based on open ports"""
        if not open_ports:
            return 0.2
        
        score = 0.3  # Base score for responding
        
        # Add points for common network device ports
        if 161 in open_ports:  # SNMP
            score += 0.3
        if 22 in open_ports:   # SSH
            score += 0.2
        if 23 in open_ports:   # Telnet
            score += 0.1
        if 80 in open_ports or 443 in open_ports:  # HTTP/HTTPS
            score += 0.2
        
        return min(score, 1.0)
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict]:
        """Get scan status and results"""
        # Check active scans first
        if scan_id in self.active_scans:
            scan_result = self.active_scans[scan_id]
            return scan_result.__dict__
        
        # Check saved results
        result_file = self.results_dir / f"{scan_id}.json"
        if result_file.exists():
            with open(result_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def get_scan_history(self, limit: int = 50) -> List[Dict]:
        """Get scan history"""
        history = []
        
        # Add active scans
        for scan_result in self.active_scans.values():
            history.append({
                'scan_id': scan_result.scan_id,
                'scan_name': scan_result.scan_name,
                'network': scan_result.network,
                'scan_type': scan_result.scan_type,
                'status': scan_result.status,
                'started_at': scan_result.started_at,
                'completed_at': scan_result.completed_at,
                'device_count': len(scan_result.discovered_devices)
            })
        
        # Add saved results
        for result_file in sorted(self.results_dir.glob("*.json"), 
                                key=lambda x: x.stat().st_mtime, reverse=True):
            if len(history) >= limit:
                break
                
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    if data['scan_id'] not in [h['scan_id'] for h in history]:
                        history.append({
                            'scan_id': data['scan_id'],
                            'scan_name': data.get('scan_name'),
                            'network': data['network'],
                            'scan_type': data['scan_type'],
                            'status': data['status'],
                            'started_at': data['started_at'],
                            'completed_at': data.get('completed_at'),
                            'device_count': len(data.get('discovered_devices', []))
                        })
            except Exception as e:
                print(f"Error reading scan result {result_file}: {e}")
        
        return history[:limit]
    
    def delete_scan_result(self, scan_id: str) -> bool:
        """Delete a scan result"""
        try:
            # Remove from active scans
            if scan_id in self.active_scans:
                del self.active_scans[scan_id]
            
            # Remove saved result
            result_file = self.results_dir / f"{scan_id}.json"
            if result_file.exists():
                result_file.unlink()
                return True
            
            return False
        except Exception as e:
            print(f"Error deleting scan result {scan_id}: {e}")
            return False
    
    async def auto_add_devices_from_scan(self, scan_id: str) -> Dict[str, Any]:
        """Automatically add discovered devices to configuration"""
        scan_data = self.get_scan_status(scan_id)
        if not scan_data:
            return {'success': False, 'error': 'Scan not found'}
        
        if scan_data['status'] != 'completed':
            return {'success': False, 'error': 'Scan not completed'}
        
        # Initialize database if needed
        await self.db_manager.initialize()
        
        added_devices = []
        failed_devices = []
        
        for device_info in scan_data['discovered_devices']:
            try:
                # Generate device ID
                hostname = device_info.get('hostname', device_info['ip'])
                device_id = self._generate_device_id(hostname, device_info['ip'])
                
                # Create credentials based on discovered info
                credentials = {}
                if device_info.get('snmp_community'):
                    credentials['snmp_community'] = device_info['snmp_community']
                    credentials['snmp_version'] = '2c'
                else:
                    # Default SNMP credentials for network devices
                    credentials['snmp_community'] = 'public'
                    credentials['snmp_version'] = '2c'
                
                # Determine device type
                device_type_str = device_info.get('device_type', 'generic')
                
                # Create device for database
                device = Device(
                    id=device_id,
                    name=hostname,
                    host=device_info['ip'],
                    device_type=device_type_str,
                    description=f"Auto-discovered from scan {scan_id}",
                    enabled_protocols=device_info.get('suggested_protocols', ['ping']),
                    credentials=credentials,
                    timeout=10,
                    retry_count=3,
                    enabled=True
                )
                
                # Add device to database
                if await self.db_manager.add_device(device):
                    added_devices.append(device_id)
                else:
                    failed_devices.append({
                        'ip': device_info['ip'],
                        'error': 'Failed to add device to database'
                    })
                    
            except Exception as e:
                failed_devices.append({
                    'ip': device_info['ip'],
                    'error': str(e)
                })
        
        return {
            'success': True,
            'added_devices': added_devices,
            'failed_devices': failed_devices,
            'summary': {
                'total_discovered': len(scan_data['discovered_devices']),
                'successfully_added': len(added_devices),
                'failed': len(failed_devices)
            }
        }
    
    def _generate_device_id(self, name: str, host: str) -> str:
        """Generate a unique device ID"""
        # Create base ID from name and host
        base_id = f"{name.lower().replace(' ', '-').replace('.', '-')}-{host.replace('.', '-')}"
        
        # Remove invalid characters
        import re
        base_id = re.sub(r'[^a-zA-Z0-9\-]', '', base_id).lower()
        
        # Ensure it starts with a letter
        if not base_id[0].isalpha():
            base_id = f"device-{base_id}"
        
        # Add timestamp to ensure uniqueness
        timestamp = int(time.time())
        device_id = f"{base_id}-{timestamp}"
        
        return device_id
    
    def cleanup_old_results(self, days: int = 30):
        """Clean up old scan results"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            for result_file in self.results_dir.glob("*.json"):
                if result_file.stat().st_mtime < cutoff_time.timestamp():
                    result_file.unlink()
                    print(f"Deleted old scan result: {result_file.name}")
        except Exception as e:
            print(f"Error cleaning up old results: {e}")
