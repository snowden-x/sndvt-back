"""
Network Discovery Module
Discovers network devices using various methods
"""

import asyncio
import ipaddress
import socket
import subprocess
import platform
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import re

class NetworkDiscovery:
    """Network device discovery class"""
    
    def __init__(self, max_concurrent: int = 50, timeout: int = 2):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    def _ping_host(self, host: str) -> Tuple[str, bool, float]:
        """Ping a single host and return result"""
        try:
            start_time = time.time()
            
            # Use appropriate ping command based on OS
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', '1', '-w', str(self.timeout * 1000), host]
            else:
                cmd = ['ping', '-c', '1', '-W', str(self.timeout), host]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout + 1
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            return host, result.returncode == 0, response_time
            
        except Exception:
            return host, False, 0.0
    
    async def ping_sweep(self, network: str) -> List[Dict[str, Any]]:
        """Perform ping sweep on a network range"""
        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid network format: {e}")
        
        print(f"🔍 Performing ping sweep on {network}...")
        print(f"   Scanning {net.num_addresses} addresses with {self.max_concurrent} concurrent pings")
        
        # Create list of hosts to ping
        hosts = [str(ip) for ip in net.hosts()]
        
        # If it's a single host network, include the network address
        if net.num_addresses == 1:
            hosts = [str(net.network_address)]
        
        # Limit the number of hosts for very large networks
        if len(hosts) > 1000:
            print(f"⚠️ Large network detected ({len(hosts)} hosts). Limiting to first 1000 hosts.")
            hosts = hosts[:1000]
        
        # Perform concurrent pings
        loop = asyncio.get_event_loop()
        tasks = []
        
        # Use semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def ping_with_semaphore(host: str):
            async with semaphore:
                return await loop.run_in_executor(self.executor, self._ping_host, host)
        
        # Create tasks for all hosts
        tasks = [ping_with_semaphore(host) for host in hosts]
        
        # Execute all pings
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        alive_hosts = []
        for result in results:
            if isinstance(result, Exception):
                continue
            
            host, is_alive, response_time = result
            if is_alive:
                alive_hosts.append({
                    'ip': host,
                    'response_time': round(response_time, 2),
                    'status': 'alive'
                })
        
        print(f"✅ Ping sweep complete. Found {len(alive_hosts)} alive hosts out of {len(hosts)} scanned.")
        return alive_hosts
    
    def _check_port(self, host: str, port: int) -> Tuple[str, int, bool]:
        """Check if a port is open on a host"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return host, port, result == 0
        except Exception:
            return host, port, False
    
    async def port_scan(self, hosts: List[str], ports: List[int] = None) -> Dict[str, Dict[int, bool]]:
        """Scan common network device ports on discovered hosts"""
        if ports is None:
            # Common network device ports
            ports = [
                22,    # SSH
                23,    # Telnet
                80,    # HTTP
                161,   # SNMP
                443,   # HTTPS
                8080,  # HTTP Alt
                8443,  # HTTPS Alt
                9000,  # Various management interfaces
            ]
        
        print(f"🔍 Scanning {len(ports)} ports on {len(hosts)} hosts...")
        
        loop = asyncio.get_event_loop()
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def scan_with_semaphore(host: str, port: int):
            async with semaphore:
                return await loop.run_in_executor(self.executor, self._check_port, host, port)
        
        # Create tasks for all host/port combinations
        tasks = []
        for host in hosts:
            for port in ports:
                tasks.append(scan_with_semaphore(host, port))
        
        # Execute all scans
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        port_results = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            
            host, port, is_open = result
            if host not in port_results:
                port_results[host] = {}
            port_results[host][port] = is_open
        
        return port_results
    
    def _get_hostname(self, ip: str) -> Optional[str]:
        """Try to get hostname for an IP address"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except socket.herror:
            return None
    
    def _snmp_get_system_info(self, host: str, community: str = "public") -> Dict[str, Any]:
        """Try to get basic system info via SNMP"""
        try:
            from pysnmp.hlapi import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            
            # System description OID
            oid = '1.3.6.1.2.1.1.1.0'
            
            for (errorIndication, errorStatus, errorIndex, varBinds) in getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((host, 161), timeout=self.timeout),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            ):
                if errorIndication or errorStatus:
                    return {}
                
                for varBind in varBinds:
                    return {
                        'snmp_available': True,
                        'system_description': str(varBind[1]),
                        'community': community
                    }
        except Exception:
            pass
        
        return {}
    
    def _detect_device_type(self, port_scan: Dict[int, bool], system_info: Dict[str, Any]) -> str:
        """Try to detect device type based on open ports and system info"""
        
        # Check system description for device type hints
        if system_info.get('system_description'):
            desc = system_info['system_description'].lower()
            if any(keyword in desc for keyword in ['router', 'cisco', 'juniper']):
                return 'router'
            elif any(keyword in desc for keyword in ['switch', 'catalyst']):
                return 'switch'
            elif any(keyword in desc for keyword in ['firewall', 'fortigate', 'palo alto']):
                return 'firewall'
            elif any(keyword in desc for keyword in ['access point', 'ap', 'wireless']):
                return 'access_point'
            elif any(keyword in desc for keyword in ['server', 'linux', 'windows']):
                return 'server'
        
        # Fallback to port-based detection
        if port_scan.get(161):  # SNMP
            if port_scan.get(22) or port_scan.get(23):  # SSH/Telnet
                return 'router'  # Most likely a network device
            else:
                return 'switch'  # Managed switch
        elif port_scan.get(22) and (port_scan.get(80) or port_scan.get(443)):
            return 'server'
        
        return 'generic'
    
    def _suggest_protocols(self, port_scan: Dict[int, bool], system_info: Dict[str, Any]) -> List[str]:
        """Suggest monitoring protocols based on available services"""
        protocols = []
        
        if system_info.get('snmp_available') or port_scan.get(161):
            protocols.append('snmp')
        
        if port_scan.get(22):
            protocols.append('ssh')
        
        if port_scan.get(80) or port_scan.get(443) or port_scan.get(8080) or port_scan.get(8443):
            protocols.append('rest')
        
        return protocols or ['snmp']  # Default to SNMP if nothing else detected
    
    async def discover_network(self, network: str, snmp_communities: List[str] = None) -> List[Dict[str, Any]]:
        """Comprehensive network discovery"""
        if snmp_communities is None:
            snmp_communities = ['public', 'private']
        
        print(f"🚀 Starting comprehensive network discovery for {network}")
        print("=" * 60)
        
        # Step 1: Ping sweep
        alive_hosts = await self.ping_sweep(network)
        
        if not alive_hosts:
            print("❌ No alive hosts found")
            return []
        
        # Extract IP addresses
        host_ips = [host['ip'] for host in alive_hosts]
        
        # Step 2: Port scan
        print(f"\n🔍 Scanning ports on {len(host_ips)} alive hosts...")
        port_results = await self.port_scan(host_ips)
        
        # Step 3: Gather additional information
        print(f"\n🔍 Gathering device information...")
        
        discovered_devices = []
        
        loop = asyncio.get_event_loop()
        
        for host_info in alive_hosts:
            ip = host_info['ip']
            ports = port_results.get(ip, {})
            
            # Get hostname
            hostname = await loop.run_in_executor(
                self.executor, self._get_hostname, ip
            )
            
            # Try SNMP with different communities
            system_info = {}
            for community in snmp_communities:
                system_info = await loop.run_in_executor(
                    self.executor, self._snmp_get_system_info, ip, community
                )
                if system_info.get('snmp_available'):
                    break
            
            # Detect device type and suggest protocols
            device_type = self._detect_device_type(ports, system_info)
            protocols = self._suggest_protocols(ports, system_info)
            
            # Build device info
            device_info = {
                'ip': ip,
                'hostname': hostname,
                'response_time': host_info['response_time'],
                'device_type': device_type,
                'suggested_protocols': protocols,
                'open_ports': [port for port, is_open in ports.items() if is_open],
                'system_description': system_info.get('system_description'),
                'snmp_community': system_info.get('community') if system_info.get('snmp_available') else None
            }
            
            discovered_devices.append(device_info)
        
        # Sort by IP address
        discovered_devices.sort(key=lambda x: ipaddress.ip_address(x['ip']))
        
        print(f"\n✅ Discovery complete! Found {len(discovered_devices)} devices")
        return discovered_devices
    
    def print_discovery_results(self, devices: List[Dict[str, Any]]):
        """Print formatted discovery results"""
        if not devices:
            print("No devices discovered")
            return
        
        print(f"\n📋 DISCOVERED DEVICES ({len(devices)} found)")
        print("=" * 80)
        
        for i, device in enumerate(devices, 1):
            print(f"\n{i}. {device['ip']} ({device.get('hostname', 'Unknown hostname')})")
            print(f"   Type: {device['device_type']}")
            print(f"   Response Time: {device['response_time']}ms")
            print(f"   Open Ports: {', '.join(map(str, device['open_ports']))}")
            print(f"   Suggested Protocols: {', '.join(device['suggested_protocols'])}")
            
            if device.get('system_description'):
                desc = device['system_description'][:100] + "..." if len(device['system_description']) > 100 else device['system_description']
                print(f"   Description: {desc}")
            
            if device.get('snmp_community'):
                print(f"   SNMP Community: {device['snmp_community']}")
    
    def generate_device_configs(self, devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate device configuration from discovery results"""
        config = {
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
        
        for device in devices:
            # Generate device ID
            hostname = device.get('hostname', '').replace('.', '-').replace('_', '-')
            if hostname and hostname != 'Unknown hostname':
                device_id = f"{hostname}-{device['ip'].replace('.', '-')}"
            else:
                device_id = f"device-{device['ip'].replace('.', '-')}"
            
            # Clean up device ID
            device_id = re.sub(r'[^a-zA-Z0-9\-]', '', device_id).lower()
            
            # Build credentials
            credentials = {}
            if 'snmp' in device['suggested_protocols']:
                credentials['snmp_version'] = '2c'
                if device.get('snmp_community'):
                    credentials['snmp_community'] = device['snmp_community']
                else:
                    credentials['snmp_community'] = 'public'
            
            # Build device config
            device_config = {
                'name': device.get('hostname', device['ip']),
                'host': device['ip'],
                'device_type': device['device_type'],
                'description': f"Auto-discovered {device['device_type']}",
                'enabled_protocols': device['suggested_protocols'],
                'credentials': credentials,
                'timeout': 10,
                'retry_count': 3
            }
            
            # Add system description if available
            if device.get('system_description'):
                device_config['description'] = device['system_description'][:100]
            
            config['devices'][device_id] = device_config
        
        return config
    
    def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True) 