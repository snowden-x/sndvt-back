"""Alert API endpoints."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.config.database import get_db
from app.alerts.services.alert_service import AlertService
from app.alerts.services.netpredict_service import NetPredictService
from app.alerts.models.alert import Alert
from app.core.dependencies import get_current_user
from app.auth.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


# Pydantic models for API requests/responses
class AlertResponse(BaseModel):
    """Alert response model."""
    id: str
    timestamp: datetime
    probability: float
    prediction: int
    cause: str
    device: str
    interface: Optional[str]
    severity: str
    message: str
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    created_at: datetime
    age_minutes: float
    is_critical: bool
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_alert(cls, alert: Alert) -> "AlertResponse":
        """Create response from Alert model."""
        return cls(
            id=str(alert.id),
            timestamp=alert.timestamp,
            probability=alert.probability,
            prediction=alert.prediction,
            cause=alert.cause,
            device=alert.device,
            interface=alert.interface,
            severity=alert.severity,
            message=alert.message,
            acknowledged=alert.acknowledged,
            acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
            acknowledged_at=alert.acknowledged_at,
            created_at=alert.created_at,
            age_minutes=alert.age_minutes,
            is_critical=alert.is_critical
        )


class AlertsListResponse(BaseModel):
    """Response model for alerts list."""
    alerts: List[AlertResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class AlertStatsResponse(BaseModel):
    """Response model for alert statistics."""
    time_period_hours: int
    total_alerts: int
    acknowledged_alerts: int
    unacknowledged_alerts: int
    recent_critical_alerts: int
    severity_breakdown: Dict[str, int]
    top_devices: Dict[str, int]
    hourly_activity: List[Dict[str, Any]]
    last_updated: str


class AcknowledgeRequest(BaseModel):
    """Request model for acknowledging alerts."""
    alert_ids: List[str]


class AlertSettingsRequest(BaseModel):
    """Request model for alert settings."""
    email_enabled: bool = True
    push_enabled: bool = True
    severity_threshold: str = Field("medium", pattern="^(low|medium|high|critical)$")
    auto_ack_enabled: bool = False
    auto_ack_after_minutes: int = Field(60, ge=1, le=1440)


class SyncResponse(BaseModel):
    """Response model for alert sync operations."""
    status: str
    new_alerts_count: int
    processed_count: int
    timestamp: str


class DeleteRequest(BaseModel):
    """Request model for deleting alerts."""
    alert_ids: List[str]


class DeleteResponse(BaseModel):
    """Response model for delete operations."""
    status: str
    deleted_count: int
    failed_count: int
    total_requested: int


# Initialize services
alert_service = AlertService()
netpredict_service = NetPredictService()


@router.get("/", response_model=AlertsListResponse)
async def get_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of alerts per page"),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    acknowledged: Optional[bool] = Query(None),
    device: Optional[str] = Query(None),
    hours_back: Optional[int] = Query(None, ge=1, le=168, description="Hours to look back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertsListResponse:
    """Get alerts with filtering and pagination."""
    try:
        skip = (page - 1) * page_size
        
        alerts = alert_service.get_alerts(
            db=db,
            skip=skip,
            limit=page_size,
            severity=severity,
            acknowledged=acknowledged,
            device=device,
            hours_back=hours_back
        )
        
        # Get total count for pagination
        total_alerts = alert_service.get_alerts(
            db=db,
            skip=0,
            limit=None,
            severity=severity,
            acknowledged=acknowledged,
            device=device,
            hours_back=hours_back
        )
        total_count = len(total_alerts) if total_alerts else 0
        
        alert_responses = [AlertResponse.from_alert(alert) for alert in alerts]
        
        return AlertsListResponse(
            alerts=alert_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=len(alerts) == page_size and (skip + page_size) < total_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertResponse:
    """Get a specific alert by ID."""
    try:
        alert = alert_service.get_alert_by_id(db, UUID(alert_id))
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return AlertResponse.from_alert(alert)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    except Exception as e:
        logger.error(f"Failed to get alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert")


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertResponse:
    """Acknowledge a specific alert."""
    try:
        # Normalize/validate ID
        clean_alert_id = alert_id.strip()
        try:
            alert_uuid = UUID(clean_alert_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid alert ID format")

        # Find alert using UUID object; GUID type handles both backends
        alert_in_db = db.query(Alert).filter(Alert.id == alert_uuid).first()
        if not alert_in_db:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Set acknowledged flags and user who acknowledged
        alert_in_db.acknowledged = True
        alert_in_db.acknowledged_by = current_user.id
        alert_in_db.acknowledged_at = datetime.utcnow()
        db.commit()

        return AlertResponse.from_alert(alert_in_db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.post("/acknowledge", response_model=Dict[str, Any])
async def acknowledge_multiple_alerts(
    request: AcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Acknowledge multiple alerts."""
    try:
        acknowledged_count = 0
        failed_count = 0

        for alert_id in request.alert_ids:
            try:
                alert_uuid = UUID(alert_id.strip())
                alert_in_db = db.query(Alert).filter(Alert.id == alert_uuid).first()
                if not alert_in_db:
                    failed_count += 1
                    continue
                alert_in_db.acknowledged = True
                alert_in_db.acknowledged_by = current_user.id
                alert_in_db.acknowledged_at = datetime.utcnow()
                acknowledged_count += 1
            except Exception:
                failed_count += 1

        db.commit()

        return {
            "status": "success",
            "acknowledged_count": acknowledged_count,
            "failed_count": failed_count,
            "total_requested": len(request.alert_ids),
        }

    except Exception as e:
        logger.error(f"Failed to acknowledge multiple alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alerts")


@router.get("/stats/summary", response_model=AlertStatsResponse)
async def get_alert_statistics(
    hours_back: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertStatsResponse:
    """Get alert statistics and summary."""
    try:
        stats = alert_service.get_alert_statistics(db, hours_back)
        return AlertStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get alert statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert statistics")


@router.post("/sync", response_model=SyncResponse)
async def sync_alerts_from_netpredict(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SyncResponse:
    """Manually trigger alert sync from NetPredict."""
    try:
        # Run sync in the background
        result = await alert_service.sync_and_process_alerts(db)
        
        return SyncResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to sync alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync alerts from NetPredict")


@router.get("/health/netpredict")
async def check_netpredict_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check NetPredict service health."""
    try:
        health_status = await netpredict_service.health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"Failed to check NetPredict health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/predict", response_model=Dict[str, Any])
async def trigger_prediction(
    minutes_back: int = Query(20, ge=1, le=120, description="Minutes of data to analyze"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger a new prediction in NetPredict."""
    try:
        result = await netpredict_service.make_prediction(minutes_back)
        return {
            "status": "success",
            "prediction_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger prediction: {str(e)}")


@router.post("/train", response_model=Dict[str, Any])
async def trigger_model_training(
    days_back: int = Query(7, ge=1, le=30, description="Days of data for training"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger model retraining in NetPredict."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can trigger model training")
    
    try:
        result = await netpredict_service.trigger_model_training(days_back)
        return {
            "status": "success",
            "training_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger model training: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger model training: {str(e)}")


@router.get("/model/info")
async def get_model_info(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get information about the current prediction model."""
    try:
        model_info = await netpredict_service.get_model_info()
        return {
            "status": "success",
            "model_info": model_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")


@router.get("/prophet/status")
async def get_prophet_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get Prophet model status and information."""
    try:
        prophet_status = await netpredict_service.get_prophet_status()
        return {
            "status": "success",
            "prophet_status": prophet_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get Prophet status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Prophet status: {str(e)}")


@router.get("/prophet/alerts")
async def get_prophet_alerts(
    hours_back: int = Query(2, description="Hours of data to analyze"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current Prophet-based alerts."""
    try:
        alerts = await netpredict_service.fetch_prophet_alerts(hours_back)
        return {
            "status": "success",
            "alerts": alerts,
            "count": len(alerts),
            "hours_back": hours_back,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch Prophet alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Prophet alerts: {str(e)}")


@router.post("/prophet/train")
async def trigger_prophet_training(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger Prophet model training."""
    try:
        result = await netpredict_service.trigger_prophet_training()
        return {
            "status": "success",
            "training_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger Prophet training: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger Prophet training: {str(e)}")


@router.delete("/{alert_id}", response_model=Dict[str, Any])
async def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a specific alert."""
    try:
        # Normalize/validate ID
        clean_alert_id = alert_id.strip()
        try:
            alert_uuid = UUID(clean_alert_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid alert ID format")

        # Find alert using UUID object; GUID type handles both backends
        alert_in_db = db.query(Alert).filter(Alert.id == alert_uuid).first()
        if not alert_in_db:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Delete the alert
        db.delete(alert_in_db)
        db.commit()

        return {
            "status": "success",
            "message": "Alert deleted successfully",
            "deleted_alert_id": alert_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert")


@router.delete("/", response_model=DeleteResponse)
async def delete_multiple_alerts(
    request: DeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DeleteResponse:
    """Delete multiple alerts."""
    try:
        deleted_count = 0
        failed_count = 0

        for alert_id in request.alert_ids:
            try:
                alert_uuid = UUID(alert_id.strip())
                alert_in_db = db.query(Alert).filter(Alert.id == alert_uuid).first()
                if not alert_in_db:
                    failed_count += 1
                    continue
                db.delete(alert_in_db)
                deleted_count += 1
            except Exception:
                failed_count += 1

        db.commit()

        return DeleteResponse(
            status="success",
            deleted_count=deleted_count,
            failed_count=failed_count,
            total_requested=len(request.alert_ids)
        )

    except Exception as e:
        logger.error(f"Failed to delete multiple alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alerts")


@router.delete("/clear/all", response_model=Dict[str, Any])
async def clear_all_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clear all alerts from the system."""
    try:
        # Get count before deletion
        total_alerts = db.query(Alert).count()
        
        # Delete all alerts
        db.query(Alert).delete()
        db.commit()

        return {
            "status": "success",
            "message": f"All {total_alerts} alerts cleared successfully",
            "deleted_count": total_alerts
        }

    except Exception as e:
        logger.error(f"Failed to clear all alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear all alerts")


@router.delete("/clear/acknowledged", response_model=Dict[str, Any])
async def clear_acknowledged_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clear all acknowledged alerts from the system."""
    try:
        # Get count before deletion
        acknowledged_alerts = db.query(Alert).filter(Alert.acknowledged == True).count()
        
        # Delete all acknowledged alerts
        db.query(Alert).filter(Alert.acknowledged == True).delete()
        db.commit()

        return {
            "status": "success",
            "message": f"All {acknowledged_alerts} acknowledged alerts cleared successfully",
            "deleted_count": acknowledged_alerts
        }

    except Exception as e:
        logger.error(f"Failed to clear acknowledged alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear acknowledged alerts")


# WebSocket endpoint for real-time alerts (placeholder for future implementation)
# @router.websocket("/stream")
# async def alert_stream(websocket: WebSocket):
#     """WebSocket endpoint for real-time alert streaming."""
#     await websocket.accept()
#     # TODO: Implement real-time alert streaming
#     pass