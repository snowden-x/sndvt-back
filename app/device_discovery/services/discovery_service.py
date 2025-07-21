"""Device discovery service for network scanning."""

import asyncio
import ipaddress
import json
import socket
import subprocess
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from ..models.discovery import (
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveredDevice,
    ScanStatus,
    ScanType,
)


class DiscoveryService:
    """Service for network device discovery using nmap and other tools."""
    
    def __init__(self):
        self.active_scans: Dict[str, DiscoveryResponse] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def start_discovery_scan(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """Start a new discovery scan."""
        scan_id = str(uuid.uuid4())
        
        # Validate network range
        try:
            network = ipaddress.ip_network(request.network, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid network range: {e}")
        
        # Calculate total hosts
        total_hosts = network.num_addresses
        if total_hosts > 1024:  # Limit for safety
            raise ValueError("Network range too large. Maximum 1024 hosts allowed.")
        
        # Create initial scan response
        scan_response = DiscoveryResponse(
            scan_id=scan_id,
            network=request.network,
            scan_type=request.scan_type,
            status=ScanStatus.running,
            started_at=datetime.now(),
            total_hosts=total_hosts,
            scanned_hosts=0,
            discovered_devices=[]
        )
        
        # Store scan in active scans
        self.active_scans[scan_id] = scan_response
        
        # Start the scan in background
        asyncio.create_task(self._execute_scan(scan_id, request))
        
        return scan_response
    
    async def get_scan_status(self, scan_id: str) -> Optional[DiscoveryResponse]:
        """Get the status of a discovery scan."""
        return self.active_scans.get(scan_id)
    
    async def _execute_scan(self, scan_id: str, request: DiscoveryRequest):
        """Execute the discovery scan in background."""
        scan_response = self.active_scans[scan_id]
        
        try:
            if request.scan_type == ScanType.ping:
                devices = await self._ping_scan(request, scan_response)
            elif request.scan_type == ScanType.port:
                devices = await self._port_scan(request, scan_response)
            elif request.scan_type == ScanType.full:
                devices = await self._full_scan(request, scan_response)
            else:
                devices = await self._ping_scan(request, scan_response)
            
            # Update final results
            scan_response.discovered_devices = devices
            scan_response.status = ScanStatus.completed
            scan_response.completed_at = datetime.now()
            
        except Exception as e:
            scan_response.status = ScanStatus.failed
            scan_response.error_message = str(e)
            scan_response.completed_at = datetime.now()
    
    async def _ping_scan(self, request: DiscoveryRequest, scan_response: DiscoveryResponse) -> List[DiscoveredDevice]:
        """Perform a ping scan using nmap."""
        devices = []
        
        try:
            # Use nmap for ping scan
            cmd = [
                "nmap",
                "-sn",  # Ping scan only
                "-T4",  # Timing template (aggressive)
                f"--max-rtt-timeout={request.timeout}s",
                request.network
            ]
            
            print(f"Running nmap command: {' '.join(cmd)}")
            
            # Execute nmap command
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            )
            
            if result.returncode != 0:
                raise Exception(f"nmap failed: {result.stderr}")
            
            # Parse nmap output
            devices = self._parse_nmap_ping_output(result.stdout)
            
            # Update scan progress
            scan_response.scanned_hosts = scan_response.total_hosts
            
        except FileNotFoundError:
            # Fallback to Python ping if nmap is not available
            print("nmap not found, using Python fallback ping")
            devices = await self._python_ping_scan(request, scan_response)
        except Exception as e:
            print(f"Ping scan error: {e}")
            raise
        
        return devices
    
    async def _port_scan(self, request: DiscoveryRequest, scan_response: DiscoveryResponse) -> List[DiscoveredDevice]:
        """Perform a port scan using nmap."""
        devices = []
        
        try:
            # Build port list
            ports = ",".join(map(str, request.ports or [22, 23, 80, 161, 443]))
            
            cmd = [
                "nmap",
                "-sS",  # SYN scan
                "-T4",  # Timing template
                f"-p{ports}",
                f"--max-rtt-timeout={request.timeout}s",
                request.network
            ]
            
            print(f"Running nmap command: {' '.join(cmd)}")
            
            # Execute nmap command
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            )
            
            if result.returncode != 0:
                raise Exception(f"nmap failed: {result.stderr}")
            
            # Parse nmap output
            devices = self._parse_nmap_port_output(result.stdout)
            
            # Update scan progress
            scan_response.scanned_hosts = scan_response.total_hosts
            
        except FileNotFoundError:
            # Fallback to Python port scan if nmap is not available
            print("nmap not found, using Python fallback port scan")
            devices = await self._python_port_scan(request, scan_response)
        except Exception as e:
            print(f"Port scan error: {e}")
            raise
        
        return devices
    
    async def _full_scan(self, request: DiscoveryRequest, scan_response: DiscoveryResponse) -> List[DiscoveredDevice]:
        """Perform a full scan with service detection."""
        devices = []
        
        try:
            # Build port list
            ports = ",".join(map(str, request.ports or [22, 23, 80, 161, 443]))
            
            cmd = [
                "nmap",
                "-sS",  # SYN scan
                "-sV",  # Service version detection
                "-T4",  # Timing template
                f"-p{ports}",
                f"--max-rtt-timeout={request.timeout}s",
                request.network
            ]
            
            print(f"Running nmap command: {' '.join(cmd)}")
            
            # Execute nmap command
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            )
            
            if result.returncode != 0:
                raise Exception(f"nmap failed: {result.stderr}")
            
            # Parse nmap output
            devices = self._parse_nmap_full_output(result.stdout)
            
            # Update scan progress
            scan_response.scanned_hosts = scan_response.total_hosts
            
        except FileNotFoundError:
            # Fallback to port scan if nmap is not available
            print("nmap not found, falling back to port scan")
            devices = await self._python_port_scan(request, scan_response)
        except Exception as e:
            print(f"Full scan error: {e}")
            raise
        
        return devices
    
    def _parse_nmap_ping_output(self, output: str) -> List[DiscoveredDevice]:
        """Parse nmap ping scan output."""
        devices = []
        lines = output.split('\n')
        
        current_ip = None
        current_hostname = None
        
        for line in lines:
            line = line.strip()
            
            # Look for host discovery lines
            if line.startswith("Nmap scan report for"):
                if "(" in line and ")" in line:
                    # Format: "Nmap scan report for hostname (ip)"
                    parts = line.split("(")
                    current_hostname = parts[0].replace("Nmap scan report for", "").strip()
                    current_ip = parts[1].replace(")", "").strip()
                else:
                    # Format: "Nmap scan report for ip"
                    current_ip = line.replace("Nmap scan report for", "").strip()
                    current_hostname = None
                
                if current_ip:
                    device = DiscoveredDevice(
                        ip=current_ip,
                        hostname=current_hostname,
                        status="up",
                        confidence_score=0.8
                    )
                    devices.append(device)
        
        return devices
    
    def _parse_nmap_port_output(self, output: str) -> List[DiscoveredDevice]:
        """Parse nmap port scan output."""
        devices = []
        lines = output.split('\n')
        
        current_device = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("Nmap scan report for"):
                # Save previous device if exists
                if current_device:
                    devices.append(current_device)
                
                # Parse new device
                if "(" in line and ")" in line:
                    parts = line.split("(")
                    hostname = parts[0].replace("Nmap scan report for", "").strip()
                    ip = parts[1].replace(")", "").strip()
                else:
                    ip = line.replace("Nmap scan report for", "").strip()
                    hostname = None
                
                current_device = DiscoveredDevice(
                    ip=ip,
                    hostname=hostname,
                    status="up",
                    open_ports=[],
                    suggested_protocols=[],
                    confidence_score=0.9
                )
            
            elif current_device and "/tcp" in line and "open" in line:
                # Parse open ports
                port_info = line.split("/tcp")[0].strip()
                try:
                    port = int(port_info)
                    current_device.open_ports.append(port)
                    
                    # Suggest protocols based on ports
                    if port == 22:
                        current_device.suggested_protocols.append("ssh")
                    elif port == 23:
                        current_device.suggested_protocols.append("telnet")
                    elif port == 161:
                        current_device.suggested_protocols.append("snmp")
                    elif port in [80, 443]:
                        current_device.suggested_protocols.append("rest")
                except ValueError:
                    pass
        
        # Add the last device
        if current_device:
            devices.append(current_device)
        
        return devices
    
    def _parse_nmap_full_output(self, output: str) -> List[DiscoveredDevice]:
        """Parse nmap full scan output with service detection."""
        # For now, use the same parsing as port scan
        # TODO: Add service version parsing
        return self._parse_nmap_port_output(output)
    
    async def _python_ping_scan(self, request: DiscoveryRequest, scan_response: DiscoveryResponse) -> List[DiscoveredDevice]:
        """Fallback Python-based ping scan."""
        devices = []
        network = ipaddress.ip_network(request.network, strict=False)
        
        # Limit concurrent pings
        semaphore = asyncio.Semaphore(request.max_concurrent or 50)
        
        async def ping_host(ip: str) -> Optional[DiscoveredDevice]:
            async with semaphore:
                try:
                    # Try to resolve hostname
                    hostname = None
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except:
                        pass
                    
                    # Simple socket-based connectivity test
                    loop = asyncio.get_event_loop()
                    future = loop.run_in_executor(
                        self.executor,
                        lambda: self._test_connectivity(ip, request.timeout or 5)
                    )
                    
                    response_time = await asyncio.wait_for(future, timeout=request.timeout or 5)
                    
                    if response_time is not None:
                        return DiscoveredDevice(
                            ip=ip,
                            hostname=hostname,
                            status="up",
                            response_time=response_time,
                            confidence_score=0.6
                        )
                except:
                    pass
                
                return None
        
        # Ping all hosts in the network
        tasks = []
        for ip in network.hosts():
            if len(tasks) >= 256:  # Limit total hosts for safety
                break
            tasks.append(ping_host(str(ip)))
        
        # Execute pings
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        for result in results:
            if isinstance(result, DiscoveredDevice):
                devices.append(result)
        
        return devices
    
    async def _python_port_scan(self, request: DiscoveryRequest, scan_response: DiscoveryResponse) -> List[DiscoveredDevice]:
        """Fallback Python-based port scan."""
        devices = []
        network = ipaddress.ip_network(request.network, strict=False)
        ports = request.ports or [22, 23, 80, 161, 443]
        
        # First do a ping scan to find live hosts
        live_hosts = await self._python_ping_scan(request, scan_response)
        
        # Then scan ports on live hosts
        for device in live_hosts:
            open_ports = []
            suggested_protocols = []
            
            for port in ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(request.timeout or 5)
                    result = sock.connect_ex((device.ip, port))
                    sock.close()
                    
                    if result == 0:
                        open_ports.append(port)
                        
                        # Suggest protocols
                        if port == 22:
                            suggested_protocols.append("ssh")
                        elif port == 23:
                            suggested_protocols.append("telnet")
                        elif port == 161:
                            suggested_protocols.append("snmp")
                        elif port in [80, 443]:
                            suggested_protocols.append("rest")
                except:
                    pass
            
            device.open_ports = open_ports
            device.suggested_protocols = list(set(suggested_protocols))
            device.confidence_score = 0.7 if open_ports else 0.5
            devices.append(device)
        
        return devices
    
    def _test_connectivity(self, ip: str, timeout: int) -> Optional[float]:
        """Test basic connectivity to an IP address."""
        import time
        
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # Try common ports that might respond quickly
            for port in [80, 443, 22, 23]:
                try:
                    result = sock.connect_ex((ip, port))
                    if result == 0:
                        end_time = time.time()
                        sock.close()
                        return (end_time - start_time) * 1000  # Convert to ms
                except:
                    continue
            
            sock.close()
            return None
        except:
            return None 