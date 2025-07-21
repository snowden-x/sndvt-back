"""FastAPI router for device discovery endpoints."""

from fastapi import APIRouter, HTTPException, status
from typing import List

from ..models.discovery import (
    DiscoveryRequest,
    DiscoveryResponse,
    ScanHistoryResponse,
)
from ..services.discovery_service import DiscoveryService

router = APIRouter(tags=["Device Discovery"])

# Global discovery service instance
discovery_service = DiscoveryService()


@router.post("/devices/discovery/scan", response_model=DiscoveryResponse)
async def start_discovery_scan(request: DiscoveryRequest):
    """
    Start a network discovery scan.
    
    This endpoint initiates a network scan using nmap to discover active devices
    on the specified network range.
    """
    try:
        result = await discovery_service.start_discovery_scan(request)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start discovery scan: {str(e)}"
        )


@router.get("/devices/discovery/scan/{scan_id}", response_model=DiscoveryResponse)
async def get_scan_status(scan_id: str):
    """
    Get the status and results of a discovery scan.
    
    Returns the current status of the scan including any discovered devices.
    """
    result = await discovery_service.get_scan_status(scan_id)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found"
        )
    
    return result


@router.get("/devices/discovery/scan/{scan_id}/results")
async def get_scan_results(scan_id: str):
    """
    Get the results of a completed discovery scan.
    
    Returns only the discovered devices from the scan.
    """
    result = await discovery_service.get_scan_status(scan_id)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found"
        )
    
    return {
        "scan_id": result.scan_id,
        "status": result.status,
        "discovered_devices": result.discovered_devices
    }


@router.get("/devices/discovery/history", response_model=List[ScanHistoryResponse])
async def get_scan_history():
    """
    Get the history of all discovery scans.
    
    Returns a summary of all scans that have been performed.
    """
    # For now, return scans from the active scans
    # In a real implementation, this would come from a database
    history = []
    
    for scan in discovery_service.active_scans.values():
        history.append(ScanHistoryResponse(
            scan_id=scan.scan_id,
            network=scan.network,
            scan_type=scan.scan_type,
            status=scan.status,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            device_count=len(scan.discovered_devices)
        ))
    
    return history


@router.delete("/devices/discovery/scan/{scan_id}")
async def delete_scan_result(scan_id: str):
    """
    Delete a discovery scan result.
    
    Removes the scan from the active scans list.
    """
    if scan_id not in discovery_service.active_scans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found"
        )
    
    del discovery_service.active_scans[scan_id]
    
    return {"message": f"Scan {scan_id} deleted successfully"}


@router.post("/devices/discovery/cleanup")
async def cleanup_old_results():
    """
    Clean up old discovery scan results.
    
    Removes completed scans older than a certain threshold.
    """
    from datetime import datetime, timedelta
    
    # Remove scans older than 1 hour
    cutoff_time = datetime.now() - timedelta(hours=1)
    scans_to_remove = []
    
    for scan_id, scan in discovery_service.active_scans.items():
        if scan.completed_at and scan.completed_at < cutoff_time:
            scans_to_remove.append(scan_id)
    
    for scan_id in scans_to_remove:
        del discovery_service.active_scans[scan_id]
    
    return {
        "message": f"Cleaned up {len(scans_to_remove)} old scan results",
        "removed_scans": scans_to_remove
    } 