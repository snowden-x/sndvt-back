"""API endpoints for playbook execution and management."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any

from ..models.playbook import (
    PlaybookExecuteRequest,
    PlaybookResult,
    PlaybookInfo,
    PlaybookValidateRequest,
    SafetyCheck
)
from ..services.ansible_service import AnsibleService
from ..services.playbook_service import PlaybookService

router = APIRouter(prefix="/api/automation", tags=["automation"])

# Initialize services
ansible_service = AnsibleService()
playbook_service = PlaybookService(ansible_service)


@router.post("/playbooks/execute", response_model=PlaybookResult)
async def execute_playbook(request: PlaybookExecuteRequest):
    """Execute a playbook with AI reasoning."""
    try:
        result = await ansible_service.execute_playbook_with_reasoning(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute playbook: {str(e)}")


@router.get("/playbooks/available", response_model=List[PlaybookInfo])
async def get_available_playbooks():
    """Get list of available playbooks."""
    try:
        playbooks = await ansible_service.get_available_playbooks()
        return playbooks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playbooks: {str(e)}")


@router.post("/playbooks/validate", response_model=SafetyCheck)
async def validate_playbook(request: PlaybookValidateRequest):
    """Validate playbook safety and correctness."""
    try:
        safety_check = await ansible_service.validate_playbook_safety(
            request.playbook_name, 
            request.variables
        )
        return safety_check
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate playbook: {str(e)}")


@router.get("/playbooks/status/{execution_id}", response_model=PlaybookResult)
async def get_playbook_status(execution_id: str):
    """Get status of a playbook execution."""
    try:
        result = await ansible_service.get_execution_status(execution_id)
        if not result:
            raise HTTPException(status_code=404, detail="Execution not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/playbooks/cancel/{execution_id}")
async def cancel_playbook_execution(execution_id: str):
    """Cancel a running playbook execution."""
    try:
        success = await ansible_service.cancel_execution(execution_id)
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found or not running")
        return {"message": "Execution cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel execution: {str(e)}")


# Network automation specific endpoints

@router.post("/backup")
async def backup_network_configs(devices: List[str]):
    """Backup network device configurations."""
    try:
        result = await playbook_service.execute_network_backup(devices)
        return {
            "success": result.success,
            "backup_files": result.backup_files,
            "error": result.error,
            "timestamp": result.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.post("/health-check")
async def check_device_health(devices: List[str]):
    """Perform comprehensive device health check."""
    try:
        result = await playbook_service.check_device_health(devices)
        return {
            "device_status": result.device_status,
            "issues": result.issues,
            "recommendations": result.recommendations,
            "timestamp": result.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/ping")
async def ping_test(target: str):
    """Perform ping test to a target."""
    try:
        result = await playbook_service.ping_test(target)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ping test failed: {str(e)}")


@router.post("/print-server/check")
async def check_print_server(print_server: str):
    """Check print server health and services."""
    try:
        result = await playbook_service.check_print_server(print_server)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Print server check failed: {str(e)}")


@router.post("/troubleshoot")
async def troubleshoot_connectivity(source: str, target: str):
    """Troubleshoot connectivity between two hosts."""
    try:
        result = await playbook_service.troubleshoot_connectivity(source, target)
        return {
            "connectivity_status": result.connectivity_status,
            "path_analysis": result.path_analysis,
            "issues": result.issues,
            "solutions": result.solutions,
            "timestamp": result.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Troubleshooting failed: {str(e)}")


@router.post("/vlans/configure")
async def configure_vlans(vlan_config: Dict[str, Any]):
    """Configure VLANs across devices."""
    try:
        from ..services.playbook_service import VlanConfig
        
        vlan = VlanConfig(
            vlan_id=vlan_config["vlan_id"],
            name=vlan_config["name"],
            devices=vlan_config["devices"],
            interfaces=vlan_config.get("interfaces", [])
        )
        
        result = await playbook_service.configure_vlans(vlan)
        return {
            "success": result.success,
            "changes": result.changes,
            "error": result.error,
            "timestamp": result.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VLAN configuration failed: {str(e)}") 