"""SSH discovery tool: connect and collect basic device facts and config (read-only)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping

from .base import BaseTool, RiskLevel, redact


class SSHDiscoverTool(BaseTool):
    name = "ssh_discover"
    description = "SSH to a device to collect facts (hostname, version) and running config."
    risk_level = RiskLevel.READ_ONLY
    read_only = True
    input_spec = {
        "host": "Hostname or IP address",
        "username": "SSH username",
        "password": "SSH password (or use key auth if supported)",
        "port": "SSH port (default 22)",
        "platform": "Platform hint (iosxe, nxos, aruba, etc.)",
    }

    async def run(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        host = str(params.get("host"))
        username = str(params.get("username"))
        password = str(params.get("password", ""))
        port = int(params.get("port", 22))
        platform = str(params.get("platform", ""))

        # Placeholder implementation: call external agent (future) or shell out to a script.
        # For safety in v1, we won't execute real SSH here. Return a mock shape.
        # Later: integrate Netmiko/Paramiko with strict policies and timeouts.
        await asyncio.sleep(0.1)

        return {
            "tool": self.name,
            "status": "success",
            "summary": f"Collected facts from {host}:{port} (platform={platform or 'unknown'})",
            "inputs": {
                "host": host,
                "username": username,
                "password": redact(password),
                "port": port,
                "platform": platform or None,
            },
            "facts": {
                "hostname": host,
                "version": "unknown",
                "model": "unknown",
                "os": platform or "unknown",
            },
            "config": "! running-config placeholder (to be implemented)",
        }


