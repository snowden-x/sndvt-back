"""Pydantic models for inventory management."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class InventoryHost(BaseModel):
    """Model for an inventory host."""
    name: str = Field(..., description="Host name")
    ip_address: Optional[str] = Field(None, description="IP address")
    hostname: Optional[str] = Field(None, description="Hostname")
    device_type: Optional[str] = Field(None, description="Device type (router, switch, server, etc.)")
    groups: List[str] = Field(default_factory=list, description="Groups this host belongs to")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Host variables")
    status: str = Field(default="unknown", description="Host status")


class InventoryGroup(BaseModel):
    """Model for an inventory group."""
    name: str = Field(..., description="Group name")
    hosts: List[str] = Field(default_factory=list, description="Hosts in this group")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Group variables")
    children: List[str] = Field(default_factory=list, description="Child groups")


class InventoryInfo(BaseModel):
    """Model for inventory information."""
    hosts: List[InventoryHost] = Field(default_factory=list, description="All hosts in inventory")
    groups: List[InventoryGroup] = Field(default_factory=list, description="All groups in inventory")
    total_hosts: int = Field(default=0, description="Total number of hosts")
    total_groups: int = Field(default=0, description="Total number of groups")


class InventoryUpdateRequest(BaseModel):
    """Request model for inventory updates."""
    hosts: Optional[List[InventoryHost]] = Field(None, description="Hosts to add/update")
    groups: Optional[List[InventoryGroup]] = Field(None, description="Groups to add/update")
    remove_hosts: Optional[List[str]] = Field(None, description="Hosts to remove")
    remove_groups: Optional[List[str]] = Field(None, description="Groups to remove")


class InventorySearchRequest(BaseModel):
    """Request model for inventory search."""
    query: str = Field(..., description="Search query")
    search_type: str = Field(default="name", description="Search type (name, ip, type, group)")
    limit: Optional[int] = Field(None, description="Maximum number of results") 