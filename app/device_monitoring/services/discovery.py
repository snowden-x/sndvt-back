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
import xml.etree.ElementTree as ET

class NetworkDiscovery:
    """Network device discovery class"""
    
    def __init__(self, max_concurrent: int = 50, timeout: int = 2):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    def _run_nmap_scan(self, network: str, ports: List[int]) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[int, bool]]]:
        """Run Nmap scan to discover hosts and open ports."""
        print(f"🔬 Running Nmap scan on {network} for specified ports...")
        port_str = ",".join(map(str, ports))
        
        # -T4 for faster execution, --open to only show hosts with open ports
        # -oX - to output XML to stdout
        cmd = ['nmap', '-T4', '-p', port_str, '--open', network, '-oX', '-']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=(self.timeout * 100) # Generous timeout for nmap
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"❌ Nmap scan failed. Ensure Nmap is installed and in your PATH.")
            print(f"   Error: {e}")
            return [], {}
        except subprocess.TimeoutExpired:
            print(f"❌ Nmap scan timed out for network {network}.")
            return [], {}

        alive_hosts = []
        port_results = {}

        try:
            root = ET.fromstring(result.stdout)
            for host in root.findall('host'):
                ip_address = host.find('address').get('addr')
                status_elem = host.find('status')
                if status_elem is None or status_elem.get('state') != 'up':
                    continue

                # It's alive, get response time if available
                host_script = host.find('hostscript')
                response_time = 0.0
                if host_script is not None:
                    ping_elem = host_script.find("./script[@id='ping']//elem[@key='rtt']")
                    if ping_elem is not None:
                        response_time = float(ping_elem.text)


                alive_hosts.append({
                    'ip': ip_address,
                    'response_time': response_time,
                    'status': 'alive'
                })

                port_results[ip_address] = {}
                ports_elem = host.find('ports')
                if ports_elem is not None:
                    for port in ports_elem.findall('port'):
                        if port.find('state').get('state') == 'open':
                            port_id = int(port.get('portid'))
                            port_results[ip_address][port_id] = True

        except ET.ParseError as e:
            print(f"❌ Failed to parse Nmap XML output: {e}")
            return [], {}

        print(f"✅ Nmap scan complete. Found {len(alive_hosts)} alive hosts.")
        return alive_hosts, port_results
    
    def _run_nmap_ping_scan(self, network: str) -> List[Dict[str, Any]]:
        """Run simple Nmap ping scan to discover live hosts."""
        print(f"🔬 Running simple Nmap ping scan on {network}...")
        
        # Use -sn for ping scan only (no port scan) and -oX for XML output
        cmd = ['nmap',  network, '-oX', '-']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=(self.timeout * 50)  # Reasonable timeout for ping scan
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"❌ Nmap ping scan failed. Ensure Nmap is installed and in your PATH.")
            print(f"   Error: {e}")
            return []
        except subprocess.TimeoutExpired:
            print(f"❌ Nmap ping scan timed out for network {network}.")
            return []

        alive_hosts = []

        try:
            root = ET.fromstring(result.stdout)
            for host in root.findall('host'):
                ip_address = host.find('address').get('addr')
                status_elem = host.find('status')
                if status_elem is None or status_elem.get('state') != 'up':
                    continue

                # Get hostname if available
                hostname = ip_address
                hostnames_elem = host.find('hostnames')
                if hostnames_elem is not None:
                    hostname_elem = hostnames_elem.find('hostname')
                    if hostname_elem is not None:
                        hostname = hostname_elem.get('name', ip_address)

                alive_hosts.append({
                    'ip': ip_address,
                    'hostname': hostname,
                    'response_time': 0.0,  # Nmap ping scan doesn't provide timing by default
                    'status': 'alive'
                })

        except ET.ParseError as e:
            print(f"❌ Failed to parse Nmap XML output: {e}")
            return []

        print(f"✅ Nmap ping scan complete. Found {len(alive_hosts)} alive hosts.")
        return alive_hosts
    
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

        # Define ports to scan
        ports_to_scan = [22, 23, 80, 161, 443, 8080, 8443, 9000]

        # Use Nmap for discovery
        alive_hosts, port_scan_results = self._run_nmap_scan(network, ports_to_scan)

        if not alive_hosts:
            print("🏁 No active hosts found. Discovery finished.")
            return []

        discovered_devices = []
        hosts_to_process = [host['ip'] for host in alive_hosts]
        
        # Get hostnames concurrently
        print(f"🔍 Resolving hostnames for {len(hosts_to_process)} hosts...")
        loop = asyncio.get_event_loop()
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def get_hostname_with_semaphore(host: str):
            async with semaphore:
                hostname = await loop.run_in_executor(self.executor, self._get_hostname, host)
                return host, hostname
        
        tasks = []
        for host in hosts_to_process:
            tasks.append(get_hostname_with_semaphore(host))
        
        hostname_results = await asyncio.gather(*tasks)
        hostnames = {ip: name for ip, name in hostname_results}
        
        # Process each discovered host
        print(f"🕵️  Performing detailed analysis on {len(hosts_to_process)} hosts...")
        for host_info in alive_hosts:
            ip = host_info['ip']
            
            # Get port scan results from Nmap output
            host_ports = port_scan_results.get(ip, {})
            
            # Attempt to get system info via SNMP
            system_info = {}
            if 161 in host_ports and host_ports[161]:
                for community in snmp_communities:
                    snmp_info = await loop.run_in_executor(
                        self.executor, self._snmp_get_system_info, ip, community
                    )
                    if snmp_info:
                        system_info = snmp_info
                        break
            
            device_type = self._detect_device_type(host_ports, system_info)
            protocols = self._suggest_protocols(host_ports, system_info)
            
            device_details = {
                'ip': ip,
                'hostname': hostnames.get(ip) or ip,
                'status': 'alive',
                'response_time': host_info['response_time'],
                'device_type': device_type,
                'open_ports': [p for p, is_open in host_ports.items() if is_open],
                'protocols': protocols,
                'snmp_details': system_info,
            }
            discovered_devices.append(device_details)
        
        print("=" * 60)
        print(f"✅ Discovery complete. Found {len(discovered_devices)} devices.")
        
        self.print_discovery_results(discovered_devices)
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
            print(f"   Suggested Protocols: {', '.join(device['protocols'])}")
            
            if device.get('snmp_details'):
                desc = device['snmp_details']['system_description'][:100] + "..." if len(device['snmp_details']['system_description']) > 100 else device['snmp_details']['system_description']
                print(f"   Description: {desc}")
            
            if device.get('snmp_details') and device['snmp_details'].get('community'):
                print(f"   SNMP Community: {device['snmp_details']['community']}")
    
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
            if 'snmp' in device['protocols']:
                credentials['snmp_version'] = '2c'
                if device['snmp_details'].get('community'):
                    credentials['snmp_community'] = device['snmp_details']['community']
                else:
                    credentials['snmp_community'] = 'public'
            
            # Build device config
            device_config = {
                'name': device.get('hostname', device['ip']),
                'host': device['ip'],
                'device_type': device['device_type'],
                'description': f"Auto-discovered {device['device_type']}",
                'enabled_protocols': device['protocols'],
                'credentials': credentials,
                'timeout': 10,
                'retry_count': 3
            }
            
            # Add system description if available
            if device['snmp_details'].get('system_description'):
                device_config['description'] = device['snmp_details']['system_description'][:100]
            
            config['devices'][device_id] = device_config
        
        return config
    
    def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True) 