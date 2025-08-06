"""Alert processing and management service."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.alerts.models.alert import Alert, AlertSettings
from app.alerts.services.netpredict_service import AlertManager

logger = logging.getLogger(__name__)


class AlertService:
    """Service for alert processing, filtering, and management."""
    
    def __init__(self):
        self.alert_manager = AlertManager()
    
    async def sync_and_process_alerts(self, db: Session) -> Dict[str, Any]:
        """Sync alerts from NetPredict and process them."""
        try:
            # Sync alerts from NetPredict
            new_alerts = await self.alert_manager.sync_alerts_from_netpredict(db)
            
            # Process new alerts (notifications, auto-acknowledgments, etc.)
            processed_count = await self._process_new_alerts(db, new_alerts)
            
            return {
                "status": "success",
                "new_alerts_count": len(new_alerts),
                "processed_count": processed_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to sync and process alerts: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _process_new_alerts(self, db: Session, alerts: List[Alert]) -> int:
        """Process new alerts for notifications and auto-actions."""
        processed_count = 0
        
        for alert in alerts:
            try:
                # Apply auto-acknowledgment rules if configured
                await self._apply_auto_acknowledgment(db, alert)
                
                # Generate notifications if needed
                await self._generate_notifications(db, alert)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process alert {alert.id}: {e}")
        
        return processed_count
    
    async def _apply_auto_acknowledgment(self, db: Session, alert: Alert):
        """Apply auto-acknowledgment rules to an alert."""
        # Get global auto-ack settings
        global_settings = db.query(AlertSettings).filter(
            AlertSettings.user_id.is_(None)
        ).first()
        
        if global_settings and global_settings.auto_ack_enabled:
            # Check if alert should be auto-acknowledged based on severity
            severity_threshold = global_settings.severity_threshold.lower()
            alert_severity = alert.severity.lower()
            
            severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            threshold_level = severity_levels.get(severity_threshold, 2)
            alert_level = severity_levels.get(alert_severity, 2)
            
            if alert_level < threshold_level:
                # Schedule auto-acknowledgment
                auto_ack_time = alert.created_at + timedelta(
                    minutes=global_settings.auto_ack_after_minutes
                )
                logger.info(f"Alert {alert.id} scheduled for auto-ack at {auto_ack_time}")
    
    async def _generate_notifications(self, db: Session, alert: Alert):
        """Generate notifications for an alert."""
        if alert.is_critical:
            # For critical alerts, we could trigger real-time notifications
            logger.info(f"Critical alert generated: {alert.device} - {alert.message}")
            # TODO: Implement WebSocket broadcasting for real-time notifications
    
    def get_alerts(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 50,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        device: Optional[str] = None,
        hours_back: Optional[int] = None
    ) -> List[Alert]:
        """Get alerts with filtering options."""
        query = db.query(Alert)
        
        # Apply filters
        if severity:
            query = query.filter(Alert.severity == severity.lower())
        
        if acknowledged is not None:
            query = query.filter(Alert.acknowledged == acknowledged)
        
        if device:
            query = query.filter(Alert.device.ilike(f"%{device}%"))
        
        if hours_back:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            query = query.filter(Alert.created_at >= cutoff_time)
        
        # Order by creation time (newest first)
        query = query.order_by(desc(Alert.created_at))
        
        return query.offset(skip).limit(limit).all()
    
    def get_alert_by_id(self, db: Session, alert_id: UUID) -> Optional[Alert]:
        """Get a specific alert by ID."""
        return db.query(Alert).filter(Alert.id == alert_id).first()
    
    def acknowledge_alert(
        self,
        db: Session,
        alert_id: UUID,
        user_id: UUID
    ) -> Optional[Alert]:
        """Acknowledge an alert."""
        return self.alert_manager.acknowledge_alert(db, str(alert_id), str(user_id))
    
    def acknowledge_multiple_alerts(
        self,
        db: Session,
        alert_ids: List[UUID],
        user_id: UUID
    ) -> Dict[str, int]:
        """Acknowledge multiple alerts."""
        acknowledged_count = 0
        failed_count = 0
        
        for alert_id in alert_ids:
            try:
                alert = self.acknowledge_alert(db, alert_id, user_id)
                if alert:
                    acknowledged_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
                failed_count += 1
        
        return {
            "acknowledged_count": acknowledged_count,
            "failed_count": failed_count,
            "total_requested": len(alert_ids)
        }
    
    def get_alert_statistics(
        self,
        db: Session,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get comprehensive alert statistics."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Base query for the time period
        base_query = db.query(Alert).filter(Alert.created_at >= cutoff_time)
        
        # Total counts
        total_alerts = base_query.count()
        acknowledged_alerts = base_query.filter(Alert.acknowledged == True).count()
        unacknowledged_alerts = total_alerts - acknowledged_alerts
        
        # Severity breakdown
        severity_stats = db.query(
            Alert.severity,
            func.count(Alert.id).label('count')
        ).filter(
            Alert.created_at >= cutoff_time
        ).group_by(Alert.severity).all()
        
        severity_breakdown = {stat.severity: stat.count for stat in severity_stats}
        
        # Device breakdown (top 10)
        device_stats = db.query(
            Alert.device,
            func.count(Alert.id).label('count')
        ).filter(
            Alert.created_at >= cutoff_time
        ).group_by(Alert.device).order_by(
            desc(func.count(Alert.id))
        ).limit(10).all()
        
        device_breakdown = {stat.device: stat.count for stat in device_stats}
        
        # Recent activity (alerts per hour for the last 24 hours)
        hourly_stats = []
        for i in range(hours_back):
            hour_start = datetime.utcnow() - timedelta(hours=i+1)
            hour_end = datetime.utcnow() - timedelta(hours=i)
            
            count = db.query(Alert).filter(
                Alert.created_at >= hour_start,
                Alert.created_at < hour_end
            ).count()
            
            hourly_stats.append({
                "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                "count": count
            })
        
        # Critical alerts in the last hour
        last_hour = datetime.utcnow() - timedelta(hours=1)
        recent_critical = base_query.filter(
            Alert.created_at >= last_hour,
            Alert.severity.in_(["critical", "high"])
        ).count()
        
        return {
            "time_period_hours": hours_back,
            "total_alerts": total_alerts,
            "acknowledged_alerts": acknowledged_alerts,
            "unacknowledged_alerts": unacknowledged_alerts,
            "recent_critical_alerts": recent_critical,
            "severity_breakdown": severity_breakdown,
            "top_devices": device_breakdown,
            "hourly_activity": hourly_stats,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_alert_settings(
        self,
        db: Session,
        user_id: Optional[UUID] = None
    ) -> Optional[AlertSettings]:
        """Get alert settings for a user or global settings."""
        return db.query(AlertSettings).filter(
            AlertSettings.user_id == user_id
        ).first()
    
    def update_alert_settings(
        self,
        db: Session,
        user_id: Optional[UUID],
        settings_data: Dict[str, Any]
    ) -> AlertSettings:
        """Update alert settings for a user or global settings."""
        settings = self.get_alert_settings(db, user_id)
        
        if not settings:
            settings = AlertSettings(user_id=user_id)
            db.add(settings)
        
        # Update settings
        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.updated_at = datetime.utcnow()
        db.commit()
        
        return settings