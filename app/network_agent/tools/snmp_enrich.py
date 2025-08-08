"""SNMP enrichment tool: fetch basic sysName and interface names (read-only)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping

from .base import BaseTool, RiskLevel, redact


class SNMPEnrichTool(BaseTool):
    name = "snmp_enrich"
    description = "Use SNMP to collect device/port names and basic facts."
    risk_level = RiskLevel.READ_ONLY
    read_only = True
    input_spec = {
        "host": "Hostname or IP address",
        "community": "SNMP community (v2c)",
        "version": "SNMP version (default v2c)",
        "timeout": "Timeout seconds (default 3)",
    }

    async def run(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        host = str(params.get("host"))
        community = str(params.get("community", "public"))
        version = str(params.get("version", "2c"))
        timeout = int(params.get("timeout", 3))

        # Placeholder for real SNMP calls. Return a mock shape for now.
        await asyncio.sleep(0.1)

        return {
            "tool": self.name,
            "status": "success",
            "summary": f"Collected SNMP facts from {host}",
            "inputs": {
                "host": host,
                "community": redact(community),
                "version": version,
                "timeout": timeout,
            },
            "facts": {
                "sysName": host,
                "sysDescr": "unknown",
            },
            "interfaces": [
                {"ifIndex": 1, "ifName": "GigabitEthernet0/1", "ifAlias": "uplink"},
                {"ifIndex": 2, "ifName": "GigabitEthernet0/2", "ifAlias": "server"},
            ],
        }


