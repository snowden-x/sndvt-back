"""Manage and execute network automation playbooks."""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.playbook import (
    PlaybookExecuteRequest,
    PlaybookResult,
    PlaybookStatus
)
from .ansible_service import AnsibleService


class BackupResult:
    """Result of backup operation."""
    def __init__(self, success: bool, backup_files: List[str], error: Optional[str] = None):
        self.success = success
        self.backup_files = backup_files
        self.error = error
        self.timestamp = datetime.now()


class HealthResult:
    """Result of health check operation."""
    def __init__(self, device_status: Dict[str, Any], issues: List[str], recommendations: List[str]):
        self.device_status = device_status
        self.issues = issues
        self.recommendations = recommendations
        self.timestamp = datetime.now()


class VlanConfig:
    """VLAN configuration."""
    def __init__(self, vlan_id: int, name: str, devices: List[str], interfaces: Optional[List[str]] = None):
        self.vlan_id = vlan_id
        self.name = name
        self.devices = devices
        self.interfaces = interfaces or []


class ConfigResult:
    """Result of configuration operation."""
    def __init__(self, success: bool, changes: List[str], error: Optional[str] = None):
        self.success = success
        self.changes = changes
        self.error = error
        self.timestamp = datetime.now()


class TroubleshootResult:
    """Result of troubleshooting operation."""
    def __init__(self, connectivity_status: str, path_analysis: Dict[str, Any], issues: List[str], solutions: List[str]):
        self.connectivity_status = connectivity_status
        self.path_analysis = path_analysis
        self.issues = issues
        self.solutions = solutions
        self.timestamp = datetime.now()


class PlaybookService:
    """Manage and execute network automation playbooks."""
    
    def __init__(self, ansible_service: AnsibleService):
        self.ansible_service = ansible_service
    
    async def execute_network_backup(self, devices: List[str]) -> BackupResult:
        """Backup network device configurations."""
        try:
            # Create backup playbook request
            request = PlaybookExecuteRequest(
                playbook_name="backup_configs",
                inventory=",".join(devices),
                variables={
                    "backup_dir": "/tmp/network_backups",
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
                },
                ai_reasoning="Backing up network device configurations for safety and compliance"
            )
            
            # Execute backup playbook
            result = await self.ansible_service.execute_playbook_with_reasoning(request)
            
            # Wait for completion
            while result.status in [PlaybookStatus.PENDING, PlaybookStatus.RUNNING]:
                await asyncio.sleep(2)
                result = await self.ansible_service.get_execution_status(result.execution_id)
                if not result:
                    break
            
            if result.status == PlaybookStatus.COMPLETED:
                # Parse backup files from output
                backup_files = self._parse_backup_files(result.output)
                return BackupResult(success=True, backup_files=backup_files)
            else:
                return BackupResult(success=False, backup_files=[], error=result.error_message)
        
        except Exception as e:
            return BackupResult(success=False, backup_files=[], error=str(e))
    
    async def check_device_health(self, devices: List[str]) -> HealthResult:
        """Comprehensive device health check."""
        try:
            # Create health check playbook request
            request = PlaybookExecuteRequest(
                playbook_name="health_check",
                inventory=",".join(devices),
                variables={
                    "check_interfaces": True,
                    "check_memory": True,
                    "check_cpu": True,
                    "check_temperature": True
                },
                ai_reasoning="Performing comprehensive health check to identify potential issues"
            )
            
            # Execute health check playbook
            result = await self.ansible_service.execute_playbook_with_reasoning(request)
            
            # Wait for completion
            while result.status in [PlaybookStatus.PENDING, PlaybookStatus.RUNNING]:
                await asyncio.sleep(2)
                result = await self.ansible_service.get_execution_status(result.execution_id)
                if not result:
                    break
            
            if result.status == PlaybookStatus.COMPLETED:
                # Parse health data from output
                device_status, issues, recommendations = self._parse_health_data(result.output)
                return HealthResult(device_status, issues, recommendations)
            else:
                return HealthResult({}, ["Health check failed"], ["Check device connectivity"])
        
        except Exception as e:
            return HealthResult({}, [f"Health check error: {str(e)}"], ["Verify device accessibility"])
    
    async def configure_vlans(self, vlan_config: VlanConfig) -> ConfigResult:
        """Configure VLANs across devices."""
        try:
            # Create VLAN configuration playbook request
            request = PlaybookExecuteRequest(
                playbook_name="configure_vlans",
                inventory=",".join(vlan_config.devices),
                variables={
                    "vlan_id": vlan_config.vlan_id,
                    "vlan_name": vlan_config.name,
                    "interfaces": vlan_config.interfaces
                },
                ai_reasoning=f"Configuring VLAN {vlan_config.vlan_id} ({vlan_config.name}) across network devices"
            )
            
            # Execute VLAN configuration playbook
            result = await self.ansible_service.execute_playbook_with_reasoning(request)
            
            # Wait for completion
            while result.status in [PlaybookStatus.PENDING, PlaybookStatus.RUNNING]:
                await asyncio.sleep(2)
                result = await self.ansible_service.get_execution_status(result.execution_id)
                if not result:
                    break
            
            if result.status == PlaybookStatus.COMPLETED:
                changes = self._parse_config_changes(result.output)
                return ConfigResult(success=True, changes=changes)
            else:
                return ConfigResult(success=False, changes=[], error=result.error_message)
        
        except Exception as e:
            return ConfigResult(success=False, changes=[], error=str(e))
    
    async def troubleshoot_connectivity(self, source: str, target: str) -> TroubleshootResult:
        """Troubleshoot connectivity issues."""
        try:
            # Create troubleshooting playbook request
            request = PlaybookExecuteRequest(
                playbook_name="troubleshoot_connectivity",
                inventory=f"{source},{target}",
                variables={
                    "source_host": source,
                    "target_host": target,
                    "test_ports": [80, 443, 22, 23]
                },
                ai_reasoning=f"Troubleshooting connectivity from {source} to {target}"
            )
            
            # Execute troubleshooting playbook
            result = await self.ansible_service.execute_playbook_with_reasoning(request)
            
            # Wait for completion
            while result.status in [PlaybookStatus.PENDING, PlaybookStatus.RUNNING]:
                await asyncio.sleep(2)
                result = await self.ansible_service.get_execution_status(result.execution_id)
                if not result:
                    break
            
            if result.status == PlaybookStatus.COMPLETED:
                # Parse troubleshooting data from output
                connectivity_status, path_analysis, issues, solutions = self._parse_troubleshoot_data(result.output)
                return TroubleshootResult(connectivity_status, path_analysis, issues, solutions)
            else:
                return TroubleshootResult(
                    "unknown", 
                    {}, 
                    ["Troubleshooting failed"], 
                    ["Check device accessibility and credentials"]
                )
        
        except Exception as e:
            return TroubleshootResult(
                "error", 
                {}, 
                [f"Troubleshooting error: {str(e)}"], 
                ["Verify device connectivity and configuration"]
            )
    
    async def ping_test(self, target: str) -> Dict[str, Any]:
        """Simple ping test to a target."""
        try:
            request = PlaybookExecuteRequest(
                playbook_name="simple_ping_test",
                inventory=target,
                variables={"ping_count": 3},
                ai_reasoning=f"Testing connectivity to {target}"
            )
            
            result = await self.ansible_service.execute_playbook_with_reasoning(request)
            
            # Wait for completion
            while result.status in [PlaybookStatus.PENDING, PlaybookStatus.RUNNING]:
                await asyncio.sleep(1)
                result = await self.ansible_service.get_execution_status(result.execution_id)
                if not result:
                    break
            
            if result.status == PlaybookStatus.COMPLETED:
                return self._parse_ping_results(result.output)
            else:
                return {"status": "failed", "error": result.error_message}
        
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def check_print_server(self, print_server: str) -> Dict[str, Any]:
        """Check print server health and services."""
        try:
            request = PlaybookExecuteRequest(
                playbook_name="print_server_check",
                inventory=print_server,
                variables={
                    "check_ports": [9100, 631, 515],
                    "test_print_service": True
                },
                ai_reasoning=f"Checking print server {print_server} health and services"
            )
            
            result = await self.ansible_service.execute_playbook_with_reasoning(request)
            
            # Wait for completion
            while result.status in [PlaybookStatus.PENDING, PlaybookStatus.RUNNING]:
                await asyncio.sleep(2)
                result = await self.ansible_service.get_execution_status(result.execution_id)
                if not result:
                    break
            
            if result.status == PlaybookStatus.COMPLETED:
                return self._parse_print_server_results(result.output)
            else:
                return {"status": "failed", "error": result.error_message}
        
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _parse_backup_files(self, output: str) -> List[str]:
        """Parse backup files from Ansible output."""
        backup_files = []
        lines = output.split('\n')
        for line in lines:
            if 'backup' in line.lower() and '.cfg' in line:
                # Extract backup file path
                parts = line.split()
                for part in parts:
                    if '.cfg' in part and 'backup' in part:
                        backup_files.append(part)
        return backup_files
    
    def _parse_health_data(self, output: str) -> tuple:
        """Parse health data from Ansible output."""
        device_status = {}
        issues = []
        recommendations = []
        
        lines = output.split('\n')
        current_device = None
        
        for line in lines:
            if 'TASK' in line and 'hosts' in line:
                # Extract device name
                if '[' in line and ']' in line:
                    current_device = line.split('[')[1].split(']')[0]
            
            if current_device and 'ok=' in line:
                # Parse task results
                if 'failed=' in line and int(line.split('failed=')[1].split()[0]) > 0:
                    issues.append(f"Task failed on {current_device}")
            
            if 'WARNING' in line or 'ERROR' in line:
                issues.append(line.strip())
            
            if 'recommendation' in line.lower():
                recommendations.append(line.strip())
        
        return device_status, issues, recommendations
    
    def _parse_config_changes(self, output: str) -> List[str]:
        """Parse configuration changes from Ansible output."""
        changes = []
        lines = output.split('\n')
        
        for line in lines:
            if 'changed=' in line and int(line.split('changed=')[1].split()[0]) > 0:
                changes.append("Configuration modified")
            elif 'added' in line.lower():
                changes.append("Configuration added")
            elif 'removed' in line.lower():
                changes.append("Configuration removed")
        
        return changes
    
    def _parse_troubleshoot_data(self, output: str) -> tuple:
        """Parse troubleshooting data from Ansible output."""
        connectivity_status = "unknown"
        path_analysis = {}
        issues = []
        solutions = []
        
        lines = output.split('\n')
        
        for line in lines:
            if 'ping' in line.lower() and 'ok=' in line:
                if int(line.split('ok=')[1].split()[0]) > 0:
                    connectivity_status = "connected"
                else:
                    connectivity_status = "disconnected"
                    issues.append("Ping failed")
                    solutions.append("Check network connectivity and firewall rules")
            
            if 'port' in line.lower() and 'failed' in line:
                issues.append("Port connectivity issue")
                solutions.append("Check service status and firewall configuration")
        
        return connectivity_status, path_analysis, issues, solutions
    
    def _parse_ping_results(self, output: str) -> Dict[str, Any]:
        """Parse ping test results."""
        results = {"status": "unknown", "response_time": None, "packet_loss": None}
        
        lines = output.split('\n')
        for line in lines:
            if 'PLAY RECAP' in line:
                # Look for the summary line
                continue
            elif 'ok=' in line and 'failed=' in line and 'localhost' in line:
                # Parse the summary line like: localhost : ok=3    changed=0    unreachable=0    failed=0
                parts = line.split()
                for part in parts:
                    if part.startswith('ok='):
                        ok_count = int(part.split('=')[1])
                    elif part.startswith('failed='):
                        failed_count = int(part.split('=')[1])
                
                if ok_count > 0 and failed_count == 0:
                    results["status"] = "success"
                elif ok_count > 0:
                    results["status"] = "partial"
                else:
                    results["status"] = "failed"
                break
            elif 'ping": "pong"' in line:
                # Direct ping success indicator
                results["status"] = "success"
        
        return results
    
    def _parse_print_server_results(self, output: str) -> Dict[str, Any]:
        """Parse print server check results."""
        results = {
            "status": "unknown",
            "connectivity": False,
            "services": {},
            "issues": []
        }
        
        lines = output.split('\n')
        for line in lines:
            if 'ping' in line.lower() and 'ok=' in line:
                if int(line.split('ok=')[1].split()[0]) > 0:
                    results["connectivity"] = True
            
            if 'port' in line.lower():
                if '9100' in line and 'ok=' in line:
                    results["services"]["lpd"] = int(line.split('ok=')[1].split()[0]) > 0
                elif '631' in line and 'ok=' in line:
                    results["services"]["ipp"] = int(line.split('ok=')[1].split()[0]) > 0
        
        # Determine overall status
        if results["connectivity"] and all(results["services"].values()):
            results["status"] = "healthy"
        elif results["connectivity"]:
            results["status"] = "partial"
            results["issues"].append("Some print services not responding")
        else:
            results["status"] = "unreachable"
            results["issues"].append("Print server not reachable")
        
        return results 