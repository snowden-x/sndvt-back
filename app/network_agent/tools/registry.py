"""Simple in-process tool registry for the Network Agent."""

from __future__ import annotations

from typing import Dict, List, Mapping, Any

from .base import BaseTool
from .ping import PingTool
from .ssh_discover import SSHDiscoverTool
from .snmp_enrich import SNMPEnrichTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(PingTool())
        self.register(SSHDiscoverTool())
        self.register(SNMPEnrichTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level,
                "read_only": t.read_only,
                "input_spec": t.input_spec,
            }
            for t in self._tools.values()
        ]

    async def run(self, name: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"status": "error", "error": f"Unknown tool: {name}"}
        try:
            tool.validate(params)
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return await tool.run(params)


registry = ToolRegistry()


