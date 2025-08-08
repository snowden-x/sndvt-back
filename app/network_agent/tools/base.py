"""Base interfaces for autonomous Network Agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Mapping, Optional


class RiskLevel(str, Enum):
    """Execution risk classification used for policy gating."""

    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BaseTool(ABC):
    """Abstract base class for tools the agent can execute.

    Tools should be small, composable actions (e.g., ping target, SSH facts, SNMP query).
    """

    name: str = "base"
    description: str = ""
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    read_only: bool = True

    # Simple, human-readable input spec for UI/docs
    input_spec: Dict[str, str] = {}

    def validate(self, params: Mapping[str, Any]) -> None:
        """Validate required inputs. Raise ValueError if invalid."""
        for key in self.input_spec.keys():
            # Required by default unless spec marks otherwise (keep simple for v1)
            if key not in params:
                raise ValueError(f"Missing required parameter: {key}")

    @abstractmethod
    async def run(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        """Execute the tool and return a structured result."""
        raise NotImplementedError


def redact(value: Optional[str]) -> str:
    """Utility to mask secrets when echoing parameters."""
    if not value:
        return ""
    if len(value) <= 4:
        return "***"
    return value[:2] + "***" + value[-2:]


