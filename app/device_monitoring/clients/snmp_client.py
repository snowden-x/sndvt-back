"""
SNMP Client for network device monitoring
"""

import asyncio
from typing import Dict, List, Any, Optional
from pysnmp.hlapi.asyncio import *
from pysnmp.proto.rfc1902 import Counter32, Counter64, Gauge32, Integer
import time

from app.device_monitoring.utils.base import BaseMonitor, DeviceConfig, InterfaceInfo, DeviceHealth, InterfaceStatus

class SNMPClient(BaseMonitor):
    """SNMP-based device monitor"""
    
    # Standard SNMP OIDs
    OID_SYSTEM = {
        'sysDescr': '1.3.6.1.2.1.1.1.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysContact': '1.3.6.1.2.1.1.4.0',
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysLocation': '1.3.6.1.2.1.1.6.0',
    }
    
    OID_INTERFACES = {
        'ifIndex': '1.3.6.1.2.1.2.2.1.1',
        'ifDescr': '1.3.6.1.2.1.2.2.1.2',
        'ifType': '1.3.6.1.2.1.2.2.1.3',
        'ifMtu': '1.3.6.1.2.1.2.2.1.4',
        'ifSpeed': '1.3.6.1.2.1.2.2.1.5',
        'ifPhysAddress': '1.3.6.1.2.1.2.2.1.6',
        'ifAdminStatus': '1.3.6.1.2.1.2.2.1.7',
        'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',
        'ifLastChange': '1.3.6.1.2.1.2.2.1.9',
        'ifInOctets': '1.3.6.1.2.1.2.2.1.10',
        'ifInErrors': '1.3.6.1.2.1.2.2.1.14',
        'ifOutOctets': '1.3.6.1.2.1.2.2.1.16',
        'ifOutErrors': '1.3.6.1.2.1.2.2.1.20',
    }
    
    OID_HOST_RESOURCES = {
        'hrSystemUptime': '1.3.6.1.2.1.25.1.1.0',
        'hrSystemProcesses': '1.3.6.1.2.1.25.1.6.0',
        'hrMemorySize': '1.3.6.1.2.1.25.2.2.0',
        'hrProcessorLoad': '1.3.6.1.2.1.25.3.3.1.2',  # Table
    }
    
    # Cisco-specific OIDs
    OID_CISCO = {
        'cpmCPUTotal5minRev': '1.3.6.1.4.1.9.9.109.1.1.1.1.8',
        'ciscoMemoryPoolUsed': '1.3.6.1.4.1.9.9.48.1.1.1.5',
        'ciscoMemoryPoolFree': '1.3.6.1.4.1.9.9.48.1.1.1.6',
        'ciscoEnvMonTemperatureStatusValue': '1.3.6.1.4.1.9.9.13.1.3.1.3',
    }
    
    def __init__(self, device_config: DeviceConfig):
        super().__init__(device_config)
        self.community = device_config.credentials.snmp_community or 'public'
        self.version = device_config.credentials.snmp_version or '2c'
        self.port = 161
    
    async def test_connection(self) -> bool:
        """Test SNMP connectivity by getting system description"""
        try:
            result = await self._snmp_get([self.OID_SYSTEM['sysDescr']])
            return len(result) > 0
        except Exception:
            return False
    
    async def get_device_info(self) -> Dict[str, Any]:
        """Get basic device information via SNMP"""
        try:
            oids = [
                self.OID_SYSTEM['sysDescr'],
                self.OID_SYSTEM['sysUpTime'],
                self.OID_SYSTEM['sysName'],
                self.OID_SYSTEM['sysLocation'],
                self.OID_SYSTEM['sysContact'],
            ]
            
            result = await self._snmp_get(oids)
            
            return {
                'description': result.get(self.OID_SYSTEM['sysDescr'], 'Unknown'),
                'uptime': self._parse_uptime(result.get(self.OID_SYSTEM['sysUpTime'], 0)),
                'name': result.get(self.OID_SYSTEM['sysName'], 'Unknown'),
                'location': result.get(self.OID_SYSTEM['sysLocation'], 'Unknown'),
                'contact': result.get(self.OID_SYSTEM['sysContact'], 'Unknown'),
            }
        except Exception as e:
            raise Exception(f"Failed to get device info: {e}")
    
    async def get_interfaces(self) -> List[InterfaceInfo]:
        """Get all interface information"""
        try:
            # Get interface table data
            interface_data = await self._snmp_walk_table([
                self.OID_INTERFACES['ifIndex'],
                self.OID_INTERFACES['ifDescr'],
                self.OID_INTERFACES['ifAdminStatus'],
                self.OID_INTERFACES['ifOperStatus'],
                self.OID_INTERFACES['ifSpeed'],
                self.OID_INTERFACES['ifMtu'],
                self.OID_INTERFACES['ifPhysAddress'],
                self.OID_INTERFACES['ifInOctets'],
                self.OID_INTERFACES['ifOutOctets'],
                self.OID_INTERFACES['ifInErrors'],
                self.OID_INTERFACES['ifOutErrors'],
                self.OID_INTERFACES['ifLastChange'],
            ])
            
            interfaces = []
            for index, data in interface_data.items():
                try:
                    interface = InterfaceInfo(
                        name=data.get(self.OID_INTERFACES['ifDescr'], f"Interface {index}"),
                        description=data.get(self.OID_INTERFACES['ifDescr'], ''),
                        status=self._parse_interface_status(data.get(self.OID_INTERFACES['ifOperStatus'], 2)),
                        admin_status=self._parse_interface_status(data.get(self.OID_INTERFACES['ifAdminStatus'], 2)),
                        speed=self._parse_speed(data.get(self.OID_INTERFACES['ifSpeed'], 0)),
                        mtu=data.get(self.OID_INTERFACES['ifMtu']),
                        mac_address=self._parse_mac_address(data.get(self.OID_INTERFACES['ifPhysAddress'])),
                        in_octets=data.get(self.OID_INTERFACES['ifInOctets']),
                        out_octets=data.get(self.OID_INTERFACES['ifOutOctets']),
                        in_errors=data.get(self.OID_INTERFACES['ifInErrors']),
                        out_errors=data.get(self.OID_INTERFACES['ifOutErrors']),
                        last_change=self._parse_uptime(data.get(self.OID_INTERFACES['ifLastChange'], 0))
                    )
                    interfaces.append(interface)
                except Exception as e:
                    print(f"Error parsing interface {index}: {e}")
                    continue
            
            return interfaces
        except Exception as e:
            raise Exception(f"Failed to get interfaces: {e}")
    
    async def get_interface(self, interface_name: str) -> Optional[InterfaceInfo]:
        """Get specific interface information"""
        interfaces = await self.get_interfaces()
        for interface in interfaces:
            if interface.name.lower() == interface_name.lower():
                return interface
        return None
    
    async def get_health_metrics(self) -> DeviceHealth:
        """Get device health metrics"""
        health = DeviceHealth()
        
        try:
            # Get basic system info
            basic_oids = [
                self.OID_SYSTEM['sysUpTime'],
                self.OID_HOST_RESOURCES['hrMemorySize'],
            ]
            
            basic_result = await self._snmp_get(basic_oids)
            health.uptime = self._parse_uptime(basic_result.get(self.OID_SYSTEM['sysUpTime'], 0))
            
            memory_size = basic_result.get(self.OID_HOST_RESOURCES['hrMemorySize'])
            if memory_size:
                health.memory_total = int(memory_size) // 1024  # Convert KB to MB
            
            # Try to get CPU usage (Cisco-specific first, then generic)
            try:
                cpu_result = await self._snmp_walk(self.OID_CISCO['cpmCPUTotal5minRev'])
                if cpu_result:
                    # Get the first CPU value
                    cpu_values = list(cpu_result.values())
                    if cpu_values:
                        health.cpu_usage = float(cpu_values[0])
            except:
                # Try generic host resources
                try:
                    cpu_result = await self._snmp_walk(self.OID_HOST_RESOURCES['hrProcessorLoad'])
                    if cpu_result:
                        cpu_values = [float(v) for v in cpu_result.values() if v is not None]
                        if cpu_values:
                            health.cpu_usage = sum(cpu_values) / len(cpu_values)
                except:
                    pass
            
            # Try to get memory usage (Cisco-specific)
            try:
                memory_used_result = await self._snmp_walk(self.OID_CISCO['ciscoMemoryPoolUsed'])
                memory_free_result = await self._snmp_walk(self.OID_CISCO['ciscoMemoryPoolFree'])
                
                if memory_used_result and memory_free_result:
                    used_values = [int(v) for v in memory_used_result.values() if v is not None]
                    free_values = [int(v) for v in memory_free_result.values() if v is not None]
                    
                    if used_values and free_values:
                        total_used = sum(used_values)
                        total_free = sum(free_values)
                        total_memory = total_used + total_free
                        
                        if total_memory > 0:
                            health.memory_usage = (total_used / total_memory) * 100
                            health.memory_used = total_used // (1024 * 1024)  # Convert to MB
                            health.memory_total = total_memory // (1024 * 1024)  # Convert to MB
            except:
                pass
            
            # Try to get temperature (Cisco-specific)
            try:
                temp_result = await self._snmp_walk(self.OID_CISCO['ciscoEnvMonTemperatureStatusValue'])
                if temp_result:
                    temp_values = [float(v) for v in temp_result.values() if v is not None and v > 0]
                    if temp_values:
                        health.temperature = sum(temp_values) / len(temp_values)
            except:
                pass
            
        except Exception as e:
            print(f"Warning: Could not get all health metrics: {e}")
        
        return health
    
    async def _snmp_get(self, oids: List[str]) -> Dict[str, Any]:
        """Perform SNMP GET operation"""
        result = {}
        
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in await getCmd(
                SnmpEngine(),
                CommunityData(self.community, mpModel=0 if self.version == '1' else 1),
                UdpTransportTarget((self.device_config.host, self.port), timeout=self.timeout),
                ContextData(),
                *[ObjectType(ObjectIdentity(oid)) for oid in oids]
            ):
                if errorIndication:
                    raise Exception(f"SNMP error: {errorIndication}")
                elif errorStatus:
                    raise Exception(f"SNMP error: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}")
                else:
                    for varBind in varBinds:
                        oid_str = str(varBind[0])
                        value = varBind[1]
                        result[oid_str] = self._convert_snmp_value(value)
        
        except Exception as e:
            raise Exception(f"SNMP GET failed: {e}")
        
        return result
    
    async def _snmp_walk(self, base_oid: str) -> Dict[str, Any]:
        """Perform SNMP WALK operation"""
        result = {}
        
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in await nextCmd(
                SnmpEngine(),
                CommunityData(self.community, mpModel=0 if self.version == '1' else 1),
                UdpTransportTarget((self.device_config.host, self.port), timeout=self.timeout),
                ContextData(),
                ObjectType(ObjectIdentity(base_oid)),
                lexicographicMode=False,
                ignoreNonIncreasingOid=True
            ):
                if errorIndication:
                    break
                elif errorStatus:
                    break
                else:
                    for varBind in varBinds:
                        oid_str = str(varBind[0])
                        value = varBind[1]
                        if oid_str.startswith(base_oid):
                            result[oid_str] = self._convert_snmp_value(value)
                        else:
                            break
        
        except Exception as e:
            raise Exception(f"SNMP WALK failed: {e}")
        
        return result
    
    async def _snmp_walk_table(self, oids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Walk multiple OIDs and organize by table index"""
        all_results = {}
        
        # Walk each OID
        for oid in oids:
            try:
                oid_results = await self._snmp_walk(oid)
                for full_oid, value in oid_results.items():
                    # Extract the index from the OID
                    if full_oid.startswith(oid + '.'):
                        index = full_oid[len(oid) + 1:]
                        if index not in all_results:
                            all_results[index] = {}
                        all_results[index][oid] = value
            except Exception as e:
                print(f"Warning: Failed to walk OID {oid}: {e}")
                continue
        
        return all_results
    
    def _convert_snmp_value(self, value):
        """Convert SNMP value to Python type"""
        if isinstance(value, (Counter32, Counter64, Gauge32, Integer)):
            return int(value)
        elif hasattr(value, 'prettyPrint'):
            return value.prettyPrint()
        else:
            return str(value)
    
    def _parse_uptime(self, timeticks) -> Optional[int]:
        """Convert SNMP timeticks to seconds"""
        try:
            if timeticks:
                return int(timeticks) // 100  # Timeticks are in 1/100th seconds
        except:
            pass
        return None
    
    def _parse_speed(self, speed_value) -> Optional[int]:
        """Convert interface speed to Mbps"""
        try:
            if speed_value and int(speed_value) > 0:
                return int(speed_value) // 1000000  # Convert bps to Mbps
        except:
            pass
        return None
    
    def _parse_mac_address(self, mac_bytes) -> Optional[str]:
        """Convert MAC address bytes to string"""
        try:
            if mac_bytes and len(str(mac_bytes)) >= 12:
                # Convert hex string to MAC format
                mac_str = str(mac_bytes).replace('0x', '').replace(' ', '')
                if len(mac_str) >= 12:
                    return ':'.join([mac_str[i:i+2] for i in range(0, 12, 2)])
        except:
            pass
        return None
    
    def _parse_interface_status(self, status_value) -> InterfaceStatus:
        """Parse interface status from SNMP value"""
        try:
            status = int(status_value)
            if status == 1:
                return InterfaceStatus.UP
            elif status == 2:
                return InterfaceStatus.DOWN
            elif status == 3:
                return InterfaceStatus.TESTING
            else:
                return InterfaceStatus.UNKNOWN
        except:
            return InterfaceStatus.UNKNOWN 