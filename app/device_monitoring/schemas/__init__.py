"""
Device Monitoring API Schemas
"""

from .device_schemas import (
    DeviceCreateRequest,
    DeviceUpdateRequest,
    DeviceResponse,
    DeviceListResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveryResultResponse
)

__all__ = [
    "DeviceCreateRequest",
    "DeviceUpdateRequest", 
    "DeviceResponse",
    "DeviceListResponse",
    "DiscoveryRequest",
    "DiscoveryResponse",
    "DiscoveryResultResponse"
] 