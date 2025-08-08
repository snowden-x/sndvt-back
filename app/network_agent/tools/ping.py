"""Simple ping tool using the system ping command (read-only)."""

from __future__ import annotations

import asyncio
import shlex
from typing import Any, Dict, Mapping

from .base import BaseTool, RiskLevel


class PingTool(BaseTool):
    name = "ping"
    description = "Ping a target host to check reachability and latency."
    risk_level = RiskLevel.READ_ONLY
    read_only = True
    input_spec = {
        "target": "Hostname or IP to ping",
        "count": "Number of echo requests to send (default 3)",
        "timeout": "Per-packet timeout seconds (default 2)",
    }

    async def run(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        target = str(params.get("target"))
        count = int(params.get("count", 3))
        timeout = int(params.get("timeout", 2))

        # macOS/BSD ping uses -c for count and -W for timeout (in ms on some systems)
        cmd = f"ping -c {count} -W {timeout * 1000} {shlex.quote(target)}"

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            status = "success" if proc.returncode == 0 else "error"
            return {
                "tool": self.name,
                "status": status,
                "command": cmd,
                "return_code": proc.returncode,
                "output": output,
                "error": error or None,
            }
        except Exception as e:
            return {
                "tool": self.name,
                "status": "error",
                "error": str(e),
            }


