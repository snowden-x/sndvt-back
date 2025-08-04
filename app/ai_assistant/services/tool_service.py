"""Service for AI tool integration and automation requests."""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.network_automation.services.playbook_service import PlaybookService
from app.network_automation.services.ansible_service import AnsibleService


class Tool:
    """Represents an available automation tool."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], category: str):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.category = category


class ToolResult:
    """Result of tool execution."""
    
    def __init__(self, success: bool, output: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.success = success
        self.output = output
        self.data = data or {}
        self.error = error
        self.timestamp = datetime.now()


class ToolService:
    """Service for AI tool integration and automation."""
    
    def __init__(self):
        self.ansible_service = AnsibleService()
        self.playbook_service = PlaybookService(self.ansible_service)
        self.available_tools = self._initialize_tools()
    
    def _initialize_tools(self) -> Dict[str, Tool]:
        """Initialize available automation tools."""
        tools = {
            "ping_test": Tool(
                name="ping_test",
                description="Test connectivity to a network device or host",
                parameters={"target": "string"},
                category="connectivity"
            ),
            "health_check": Tool(
                name="health_check",
                description="Perform comprehensive health check on network devices",
                parameters={"devices": "list"},
                category="monitoring"
            ),
            "backup_configs": Tool(
                name="backup_configs",
                description="Backup network device configurations",
                parameters={"devices": "list"},
                category="backup"
            ),
            "check_print_server": Tool(
                name="check_print_server",
                description="Check print server health and services",
                parameters={"print_server": "string"},
                category="troubleshooting"
            ),
            "troubleshoot_connectivity": Tool(
                name="troubleshoot_connectivity",
                description="Troubleshoot connectivity between two hosts",
                parameters={"source": "string", "target": "string"},
                category="troubleshooting"
            ),
            "configure_vlans": Tool(
                name="configure_vlans",
                description="Configure VLANs across network devices",
                parameters={"vlan_id": "integer", "name": "string", "devices": "list"},
                category="configuration"
            )
        }
        return tools
    
    async def get_available_tools(self) -> List[Tool]:
        """Get list of available automation tools."""
        return list(self.available_tools.values())
    
    async def parse_tool_request(self, ai_response: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse AI response for tool calls."""
        # Look for tool call patterns in AI response
        tool_patterns = [
            r"TOOL_CALL:(\w+)\s*PARAMS:\s*({[^}]+})",
            r"EXECUTE:(\w+)\s*WITH:\s*({[^}]+})",
            r"RUN:(\w+)\s*ARGS:\s*({[^}]+})"
        ]
        
        for pattern in tool_patterns:
            match = re.search(pattern, ai_response, re.IGNORECASE)
            if match:
                tool_name = match.group(1).lower()
                try:
                    params = json.loads(match.group(2))
                    return tool_name, params
                except json.JSONDecodeError:
                    continue
        
        return None
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a specific automation tool."""
        tool_name = tool_name.lower()
        
        if tool_name not in self.available_tools:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' not found"
            )
        
        try:
            if tool_name == "ping_test":
                return await self._execute_ping_test(parameters)
            elif tool_name == "health_check":
                return await self._execute_health_check(parameters)
            elif tool_name == "backup_configs":
                return await self._execute_backup_configs(parameters)
            elif tool_name == "check_print_server":
                return await self._execute_check_print_server(parameters)
            elif tool_name == "troubleshoot_connectivity":
                return await self._execute_troubleshoot_connectivity(parameters)
            elif tool_name == "configure_vlans":
                return await self._execute_configure_vlans(parameters)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Tool '{tool_name}' not implemented"
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {str(e)}"
            )
    
    async def _execute_ping_test(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute ping test tool."""
        target = parameters.get("target")
        if not target:
            return ToolResult(False, "", error="Target parameter required")
        
        # Map common hostnames to IP addresses
        hostname_mapping = {
            "print_server": "192.168.1.3",
            "file_server": "192.168.1.101", 
            "web_server": "192.168.1.102",
            "router1": "192.168.1.1",
            "router2": "192.168.1.2",
            "switch1": "192.168.1.10",
            "switch2": "192.168.1.11"
        }
        
        # Use IP address if hostname is mapped, otherwise use original target
        actual_target = hostname_mapping.get(target.lower(), target)
        
        result = await self.playbook_service.ping_test(actual_target)
        
        if result.get("status") == "success":
            return ToolResult(
                success=True,
                output=f"✅ Ping test successful to {target} ({actual_target})",
                data=result
            )
        else:
            return ToolResult(
                success=False,
                output=f"❌ Ping test failed to {target} ({actual_target})",
                data=result,
                error=result.get("error", "Unknown error")
            )
    
    async def _execute_health_check(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute health check tool."""
        devices = parameters.get("devices", [])
        if not devices:
            return ToolResult(False, "", error="Devices parameter required")
        
        result = await self.playbook_service.check_device_health(devices)
        
        output_lines = [f"🏥 Health check completed for {len(devices)} devices"]
        
        if result.issues:
            output_lines.append("⚠️ Issues found:")
            for issue in result.issues:
                output_lines.append(f"   - {issue}")
        
        if result.recommendations:
            output_lines.append("💡 Recommendations:")
            for rec in result.recommendations:
                output_lines.append(f"   - {rec}")
        
        return ToolResult(
            success=len(result.issues) == 0,
            output="\n".join(output_lines),
            data={
                "issues": result.issues,
                "recommendations": result.recommendations,
                "device_status": result.device_status
            }
        )
    
    async def _execute_backup_configs(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute backup configs tool."""
        devices = parameters.get("devices", [])
        if not devices:
            return ToolResult(False, "", error="Devices parameter required")
        
        result = await self.playbook_service.execute_network_backup(devices)
        
        if result.success:
            output_lines = [f"💾 Backup completed successfully for {len(devices)} devices"]
            if result.backup_files:
                output_lines.append("📁 Backup files created:")
                for file in result.backup_files:
                    output_lines.append(f"   - {file}")
            
            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                data={"backup_files": result.backup_files}
            )
        else:
            return ToolResult(
                success=False,
                output=f"❌ Backup failed: {result.error}",
                error=result.error
            )
    
    async def _execute_check_print_server(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute print server check tool."""
        target = parameters.get("target")
        if not target:
            return ToolResult(False, "", error="Target parameter required")
        
        # Map common hostnames to IP addresses
        hostname_mapping = {
            "print_server": "192.168.1.3",
            "file_server": "192.168.1.101", 
            "web_server": "192.168.1.102",
            "router1": "192.168.1.1",
            "router2": "192.168.1.2",
            "switch1": "192.168.1.10",
            "switch2": "192.168.1.11"
        }
        
        # Use IP address if hostname is mapped, otherwise use original target
        actual_target = hostname_mapping.get(target.lower(), target)
        
        result = await self.playbook_service.check_print_server(actual_target)
        
        output_lines = [f"🖨️ Print server check for {target} ({actual_target})"]
        
        if result.get("status") == "healthy":
            output_lines.append("✅ Print server is healthy")
            output_lines.append(f"   - Connectivity: {'✅' if result.get('connectivity') else '❌'}")
            for service, status in result.get("services", {}).items():
                output_lines.append(f"   - {service.upper()}: {'✅' if status else '❌'}")
        else:
            output_lines.append(f"⚠️ Print server status: {result.get('status')}")
            for issue in result.get("issues", []):
                output_lines.append(f"   - {issue}")
        
        return ToolResult(
            success=result.get("status") == "healthy",
            output="\n".join(output_lines),
            data=result
        )
    
    async def _execute_troubleshoot_connectivity(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute troubleshoot connectivity tool."""
        source = parameters.get("source")
        target = parameters.get("target")
        
        if not source or not target:
            return ToolResult(False, "", error="Source and target parameters required")
        
        result = await self.playbook_service.troubleshoot_connectivity(source, target)
        
        output_lines = [f"🔍 Troubleshooting connectivity from {source} to {target}"]
        output_lines.append(f"Status: {result.connectivity_status}")
        
        if result.issues:
            output_lines.append("⚠️ Issues found:")
            for issue in result.issues:
                output_lines.append(f"   - {issue}")
        
        if result.solutions:
            output_lines.append("💡 Solutions:")
            for solution in result.solutions:
                output_lines.append(f"   - {solution}")
        
        return ToolResult(
            success=result.connectivity_status == "connected",
            output="\n".join(output_lines),
            data={
                "connectivity_status": result.connectivity_status,
                "issues": result.issues,
                "solutions": result.solutions
            }
        )
    
    async def _execute_configure_vlans(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute configure VLANs tool."""
        vlan_id = parameters.get("vlan_id")
        name = parameters.get("name")
        devices = parameters.get("devices", [])
        
        if not all([vlan_id, name, devices]):
            return ToolResult(False, "", error="VLAN ID, name, and devices parameters required")
        
        from app.network_automation.services.playbook_service import VlanConfig
        vlan_config = VlanConfig(vlan_id=vlan_id, name=name, devices=devices)
        
        result = await self.playbook_service.configure_vlans(vlan_config)
        
        if result.success:
            output_lines = [f"✅ VLAN {vlan_id} ({name}) configured successfully"]
            if result.changes:
                output_lines.append("📝 Changes made:")
                for change in result.changes:
                    output_lines.append(f"   - {change}")
            
            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                data={"changes": result.changes}
            )
        else:
            return ToolResult(
                success=False,
                output=f"❌ VLAN configuration failed: {result.error}",
                error=result.error
            )
    
    async def explain_tool_usage(self, tool_name: str, context: str) -> str:
        """AI explains how to use a specific tool."""
        tool_name = tool_name.lower()
        
        if tool_name not in self.available_tools:
            return f"Tool '{tool_name}' not found. Available tools: {', '.join(self.available_tools.keys())}"
        
        tool = self.available_tools[tool_name]
        
        explanation = f"""
Tool: {tool.name}
Category: {tool.category}
Description: {tool.description}

Parameters:
"""
        
        for param, param_type in tool.parameters.items():
            explanation += f"  - {param} ({param_type})\n"
        
        explanation += f"""
Usage Example:
Based on your context: "{context}"

I can use the {tool.name} tool to help with this. The tool will:
1. Execute the appropriate automation playbook
2. Provide real-time feedback on the execution
3. Return structured results that I can analyze
4. Suggest next steps based on the results

Would you like me to execute this tool for you?
"""
        
        return explanation
    
    async def suggest_tools_for_problem(self, problem_description: str) -> List[Tool]:
        """Suggest appropriate tools for a given problem."""
        problem_lower = problem_description.lower()
        suggested_tools = []
        
        # Simple keyword-based tool suggestion
        if any(word in problem_lower for word in ["ping", "connect", "reach", "network"]):
            suggested_tools.append(self.available_tools["ping_test"])
        
        if any(word in problem_lower for word in ["health", "status", "monitor", "check"]):
            suggested_tools.append(self.available_tools["health_check"])
        
        if any(word in problem_lower for word in ["backup", "config", "save"]):
            suggested_tools.append(self.available_tools["backup_configs"])
        
        if any(word in problem_lower for word in ["print", "printer", "printing"]):
            suggested_tools.append(self.available_tools["check_print_server"])
        
        if any(word in problem_lower for word in ["troubleshoot", "connectivity", "path"]):
            suggested_tools.append(self.available_tools["troubleshoot_connectivity"])
        
        if any(word in problem_lower for word in ["vlan", "configure", "network"]):
            suggested_tools.append(self.available_tools["configure_vlans"])
        
        return suggested_tools 