"""Core Ansible execution service with AI integration."""

import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator

from app.config import get_settings
from ..models.playbook import (
    PlaybookResult,
    PlaybookStatus,
    PlaybookInfo,
    PlaybookType,
    SafetyCheck,
    PlaybookExecuteRequest
)


class AnsibleService:
    """Core Ansible execution service with AI integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.ansible_base_path = Path(__file__).parent.parent.parent.parent / "ansible"
        self.playbooks_path = self.ansible_base_path / "playbooks"
        self.inventory_path = self.ansible_base_path / "inventory"
        self.active_executions: Dict[str, PlaybookResult] = {}
        
        # Ensure Ansible directories exist
        self._ensure_ansible_structure()
    
    def _ensure_ansible_structure(self):
        """Ensure Ansible directory structure exists."""
        directories = [
            self.ansible_base_path,
            self.playbooks_path,
            self.inventory_path,
            self.playbooks_path / "network",
            self.playbooks_path / "troubleshooting",
            self.playbooks_path / "maintenance",
            self.inventory_path / "group_vars"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def execute_playbook_with_reasoning(
        self, 
        request: PlaybookExecuteRequest
    ) -> PlaybookResult:
        """Execute playbook with AI reasoning context."""
        execution_id = str(uuid.uuid4())
        
        # Create execution result
        result = PlaybookResult(
            execution_id=execution_id,
            playbook_name=request.playbook_name,
            status=PlaybookStatus.PENDING,
            started_at=datetime.now(),
            variables_used=request.variables or {}
        )
        
        # Store in active executions
        self.active_executions[execution_id] = result
        
        # Start execution in background
        asyncio.create_task(self._execute_playbook_async(execution_id, request))
        
        return result
    
    async def _execute_playbook_async(self, execution_id: str, request: PlaybookExecuteRequest):
        """Execute playbook asynchronously."""
        result = self.active_executions[execution_id]
        
        try:
            # Update status to running
            result.status = PlaybookStatus.RUNNING
            
            # Find playbook file
            playbook_file = self._find_playbook_file(request.playbook_name)
            if not playbook_file:
                raise FileNotFoundError(f"Playbook '{request.playbook_name}' not found")
            
            # Prepare inventory
            inventory_file = self._prepare_inventory(request.inventory)
            
            # Prepare variables file
            variables_file = None
            if request.variables:
                variables_file = self._prepare_variables_file(request.variables)
            
            # Build ansible-playbook command
            cmd = self._build_ansible_command(
                playbook_file=playbook_file,
                inventory_file=inventory_file,
                variables_file=variables_file,
                tags=request.tags,
                limit=request.limit
            )
            
            print(f"🔧 Executing Ansible command: {' '.join(cmd)}")
            
            # Execute playbook
            start_time = datetime.now()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            end_time = datetime.now()
            
            # Parse results
            result.completed_at = end_time
            result.duration = (end_time - start_time).total_seconds()
            result.output = stdout.decode('utf-8') if stdout else ""
            
            if process.returncode == 0:
                result.status = PlaybookStatus.COMPLETED
                result.success_count = self._parse_success_count(result.output)
            else:
                result.status = PlaybookStatus.FAILED
                result.error_message = stderr.decode('utf-8') if stderr else "Unknown error"
                result.failure_count = self._parse_failure_count(result.output)
            
        except Exception as e:
            result.status = PlaybookStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
        
        finally:
            # Clean up temporary files
            if 'variables_file' in locals() and variables_file:
                try:
                    os.unlink(variables_file)
                except:
                    pass
    
    def _find_playbook_file(self, playbook_name: str) -> Optional[Path]:
        """Find playbook file by name."""
        # Search in playbooks directory
        for playbook_file in self.playbooks_path.rglob("*.yml"):
            if playbook_file.stem == playbook_name:
                return playbook_file
        
        # Also check with .yaml extension
        for playbook_file in self.playbooks_path.rglob("*.yaml"):
            if playbook_file.stem == playbook_name:
                return playbook_file
        
        return None
    
    def _prepare_inventory(self, inventory: Optional[str]) -> str:
        """Prepare inventory file."""
        if inventory:
            # If inventory is a file path, use it directly
            if os.path.exists(inventory):
                return inventory
            
            # If inventory is a host list, create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                f.write(f"all:\n  hosts:\n")
                for host in inventory.split(','):
                    host = host.strip()
                    if host == "localhost":
                        f.write(f"    {host}:\n      ansible_connection: local\n      ansible_host: 127.0.0.1\n")
                    else:
                        f.write(f"    {host}:\n")
                return f.name
        
        # Use default inventory
        default_inventory = self.inventory_path / "hosts.yml"
        if default_inventory.exists():
            return str(default_inventory)
        
        # Create minimal inventory if it doesn't exist
        default_inventory.write_text("all:\n  hosts:\n")
        return str(default_inventory)
    
    def _prepare_variables_file(self, variables: Dict[str, Any]) -> str:
        """Prepare variables file for Ansible."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            json.dump(variables, f, indent=2)
            return f.name
    
    def _build_ansible_command(
        self,
        playbook_file: Path,
        inventory_file: str,
        variables_file: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[str] = None
    ) -> List[str]:
        """Build ansible-playbook command."""
        cmd = [
            "ansible-playbook",
            "-i", inventory_file,
            str(playbook_file)
        ]
        
        if variables_file:
            cmd.extend(["-e", f"@{variables_file}"])
        
        if tags:
            cmd.extend(["--tags", ",".join(tags)])
        
        if limit:
            cmd.extend(["--limit", limit])
        
        return cmd
    
    def _parse_success_count(self, output: str) -> int:
        """Parse success count from Ansible output."""
        # Simple parsing - can be enhanced
        return output.count("ok=")
    
    def _parse_failure_count(self, output: str) -> int:
        """Parse failure count from Ansible output."""
        # Simple parsing - can be enhanced
        return output.count("failed=")
    
    async def get_available_playbooks(self) -> List[PlaybookInfo]:
        """Get list of available playbooks with descriptions."""
        playbooks = []
        
        for playbook_file in self.playbooks_path.rglob("*.yml"):
            playbook_info = await self._parse_playbook_info(playbook_file)
            if playbook_info:
                playbooks.append(playbook_info)
        
        for playbook_file in self.playbooks_path.rglob("*.yaml"):
            playbook_info = await self._parse_playbook_info(playbook_file)
            if playbook_info:
                playbooks.append(playbook_info)
        
        return playbooks
    
    async def _parse_playbook_info(self, playbook_file: Path) -> Optional[PlaybookInfo]:
        """Parse playbook information from file."""
        try:
            content = playbook_file.read_text()
            
            # Extract basic info
            name = playbook_file.stem
            path = str(playbook_file.relative_to(self.ansible_base_path))
            
            # Determine type based on directory
            playbook_type = PlaybookType.MAINTENANCE
            if "network" in playbook_file.parts:
                playbook_type = PlaybookType.NETWORK_BACKUP
            elif "troubleshooting" in playbook_file.parts:
                playbook_type = PlaybookType.TROUBLESHOOTING
            elif "maintenance" in playbook_file.parts:
                playbook_type = PlaybookType.MAINTENANCE
            
            # Extract description from comments
            description = self._extract_description(content)
            
            return PlaybookInfo(
                name=name,
                path=path,
                description=description,
                type=playbook_type,
                tags=self._extract_tags(content),
                variables=self._extract_variables(content),
                safety_level=self._determine_safety_level(content)
            )
        
        except Exception as e:
            print(f"Error parsing playbook {playbook_file}: {e}")
            return None
    
    def _extract_description(self, content: str) -> str:
        """Extract description from playbook comments."""
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('#') and 'description' in line.lower():
                return line.strip('# ').strip()
        return "Network automation playbook"
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from playbook content."""
        tags = []
        lines = content.split('\n')
        for line in lines:
            if 'tags:' in line:
                # Simple tag extraction - can be enhanced
                tag_match = line.split('tags:')[1].strip()
                if tag_match:
                    tags.extend([t.strip() for t in tag_match.split(',')])
        return tags
    
    def _extract_variables(self, content: str) -> Dict[str, Any]:
        """Extract default variables from playbook content."""
        # Simple variable extraction - can be enhanced
        variables = {}
        lines = content.split('\n')
        for line in lines:
            if 'vars:' in line or 'var:' in line:
                # Extract variables - this is a simplified version
                pass
        return variables
    
    def _determine_safety_level(self, content: str) -> str:
        """Determine safety level of playbook."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['restart', 'reload', 'shutdown', 'delete', 'remove']):
            return "dangerous"
        elif any(word in content_lower for word in ['configure', 'set', 'update', 'modify']):
            return "caution"
        else:
            return "safe"
    
    async def validate_playbook_safety(
        self, 
        playbook_name: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> SafetyCheck:
        """AI-powered safety validation for playbooks."""
        playbook_file = self._find_playbook_file(playbook_name)
        if not playbook_file:
            return SafetyCheck(
                is_safe=False,
                warnings=["Playbook not found"],
                risk_level="high"
            )
        
        content = playbook_file.read_text()
        warnings = []
        recommendations = []
        risk_level = "low"
        
        # Basic safety checks
        if any(word in content.lower() for word in ['restart', 'reload', 'shutdown']):
            warnings.append("Playbook may restart services or devices")
            recommendations.append("Ensure this is run during maintenance window")
            risk_level = "high"
        
        if any(word in content.lower() for word in ['delete', 'remove', 'purge']):
            warnings.append("Playbook may delete or remove data")
            recommendations.append("Verify backup exists before running")
            risk_level = "high"
        
        if variables and any(key in variables for key in ['force', 'confirm']):
            warnings.append("Force flags detected in variables")
            recommendations.append("Review variables carefully before execution")
            risk_level = "medium"
        
        return SafetyCheck(
            is_safe=risk_level == "low",
            warnings=warnings,
            recommendations=recommendations,
            risk_level=risk_level,
            affected_hosts=self._extract_affected_hosts(content)
        )
    
    def _extract_affected_hosts(self, content: str) -> List[str]:
        """Extract hosts that will be affected by playbook."""
        # Simple host extraction - can be enhanced
        hosts = []
        lines = content.split('\n')
        for line in lines:
            if 'hosts:' in line and not line.strip().startswith('#'):
                host_match = line.split('hosts:')[1].strip()
                if host_match and host_match != 'all':
                    hosts.append(host_match)
        return hosts
    
    async def get_execution_status(self, execution_id: str) -> Optional[PlaybookResult]:
        """Get status of a playbook execution."""
        return self.active_executions.get(execution_id)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running playbook execution."""
        if execution_id in self.active_executions:
            result = self.active_executions[execution_id]
            if result.status == PlaybookStatus.RUNNING:
                result.status = PlaybookStatus.CANCELLED
                result.completed_at = datetime.now()
                return True
        return False 