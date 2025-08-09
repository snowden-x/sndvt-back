"""NetPredict integration service for fetching alerts and predictions."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.config.database import get_db
from app.alerts.models.alert import Alert

logger = logging.getLogger(__name__)


class NetPredictService:
    """Service for integrating with NetPredict API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = getattr(self.settings, 'netpredict_api_url', 'http://localhost:8002')
        self.timeout = getattr(self.settings, 'netpredict_timeout', 30)
        self.poll_interval = getattr(self.settings, 'netpredict_poll_interval', 30)
        
    async def health_check(self) -> Dict[str, Any]:
        """Check NetPredict service health."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return {
                    "status": "healthy",
                    "netpredict_status": response.json(),
                    "timestamp": datetime.utcnow().isoformat()
                }
        except httpx.RequestError as e:
            logger.error(f"NetPredict health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"NetPredict returned error status: {e.response.status_code}")
            return {
                "status": "degraded",
                "error": f"HTTP {e.response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def fetch_current_alerts(self, minutes_back: int = 20) -> List[Dict[str, Any]]:
        """Fetch current alerts from NetPredict."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/alerts",
                    params={"minutes_back": minutes_back}
                )
                response.raise_for_status()
                alerts_data = response.json()
                
                logger.info(f"Fetched {len(alerts_data)} alerts from NetPredict")
                return alerts_data
                
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch alerts from NetPredict: {e}")
            raise Exception(f"NetPredict connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"NetPredict returned error: {e.response.status_code}")
            raise Exception(f"NetPredict API error: {e.response.status_code}")
    
    async def make_prediction(self, minutes_back: int = 20) -> Dict[str, Any]:
        """Make a new prediction request to NetPredict."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/predict",
                    params={"minutes_back": minutes_back}
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Failed to make prediction: {e}")
            raise Exception(f"NetPredict connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Prediction request failed: {e.response.status_code}")
            raise Exception(f"NetPredict API error: {e.response.status_code}")
    
    async def trigger_model_training(self, days_back: int = 7) -> Dict[str, Any]:
        """Trigger model retraining in NetPredict."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:  # Longer timeout for training
                response = await client.post(
                    f"{self.base_url}/train",
                    params={"days_back": days_back}
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Failed to trigger training: {e}")
            raise Exception(f"NetPredict connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Training request failed: {e.response.status_code}")
            raise Exception(f"NetPredict API error: {e.response.status_code}")
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/model/info")
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Failed to get model info: {e}")
            raise Exception(f"NetPredict connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Model info request failed: {e.response.status_code}")
            raise Exception(f"NetPredict API error: {e.response.status_code}")
    
    async def get_prophet_status(self) -> Dict[str, Any]:
        """Get Prophet model status and information."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/prophet/status")
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Failed to get Prophet status: {e}")
            raise Exception(f"NetPredict connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Prophet status request failed: {e.response.status_code}")
            raise Exception(f"NetPredict API error: {e.response.status_code}")
    
    async def fetch_prophet_alerts(self, hours_back: int = 2) -> List[Dict[str, Any]]:
        """Fetch Prophet-based alerts."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/prophet/alerts",
                    params={"hours_back": hours_back}
                )
                response.raise_for_status()
                alerts_data = response.json()
                
                logger.info(f"Fetched {len(alerts_data)} Prophet alerts")
                return alerts_data
                
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch Prophet alerts: {e}")
            raise Exception(f"NetPredict connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Prophet alerts request failed: {e.response.status_code}")
            raise Exception(f"NetPredict API error: {e.response.status_code}")
    
    async def trigger_prophet_training(self) -> Dict[str, Any]:
        """Trigger Prophet model training."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:  # Longer timeout for Prophet training
                response = await client.post(f"{self.base_url}/prophet/train")
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Failed to trigger Prophet training: {e}")
            raise Exception(f"NetPredict connection error: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Prophet training request failed: {e.response.status_code}")
            raise Exception(f"NetPredict API error: {e.response.status_code}")
    
    def parse_alert_data(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and normalize alert data from NetPredict."""
        try:
            # Convert timestamp string to datetime if needed
            timestamp = alert_data.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.utcnow()
            
            return {
                "timestamp": timestamp,
                "probability": float(alert_data.get("probability", 0.0)),
                "prediction": int(alert_data.get("prediction", 0)),
                "cause": str(alert_data.get("cause", "Unknown")),
                "device": str(alert_data.get("device", "Unknown")),
                "interface": alert_data.get("interface"),
                "severity": str(alert_data.get("severity", "medium")).lower(),
                "message": str(alert_data.get("message", "Network alert")),
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse alert data: {e}")
            raise ValueError(f"Invalid alert data format: {e}")


class AlertManager:
    """Manager for alert processing and storage."""
    
    def __init__(self):
        self.netpredict_service = NetPredictService()
    
    async def sync_alerts_from_netpredict(self, db: Session) -> List[Alert]:
        """Sync alerts from NetPredict and store in database."""
        try:
            # Fetch current alerts
            alerts_data = await self.netpredict_service.fetch_current_alerts()
            
            stored_alerts = []
            for alert_data in alerts_data:
                try:
                    # Parse alert data
                    parsed_data = self.netpredict_service.parse_alert_data(alert_data)
                    
                    # Check if alert already exists (based on timestamp and device)
                    existing_alert = db.query(Alert).filter(
                        Alert.timestamp == parsed_data["timestamp"],
                        Alert.device == parsed_data["device"],
                        Alert.cause == parsed_data["cause"]
                    ).first()
                    
                    if not existing_alert:
                        # Create new alert
                        alert = Alert(**parsed_data)
                        db.add(alert)
                        stored_alerts.append(alert)
                        logger.info(f"Stored new alert for device {alert.device}")
                    else:
                        logger.debug(f"Alert already exists for device {parsed_data['device']}")
                        
                except ValueError as e:
                    logger.error(f"Skipping invalid alert data: {e}")
                    continue
            
            # Commit all changes
            if stored_alerts:
                db.commit()
                logger.info(f"Successfully stored {len(stored_alerts)} new alerts")
            
            return stored_alerts
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync alerts: {e}")
            raise
    
    def get_recent_alerts(self, db: Session, limit: int = 50, severity: Optional[str] = None) -> List[Alert]:
        """Get recent alerts from database."""
        query = db.query(Alert).order_by(Alert.created_at.desc())
        
        if severity:
            query = query.filter(Alert.severity == severity.lower())
        
        return query.limit(limit).all()
    
    def acknowledge_alert(self, db: Session, alert_id: str, user_id: str) -> Optional[Alert]:
        """Acknowledge an alert."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = user_id
            alert.acknowledged_at = datetime.utcnow()
            db.commit()
            logger.info(f"Alert {alert_id} acknowledged by user {user_id}")
        return alert
    
    def get_alert_stats(self, db: Session, hours_back: int = 24) -> Dict[str, Any]:
        """Get alert statistics for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        alerts = db.query(Alert).filter(Alert.created_at >= cutoff_time).all()
        
        total_alerts = len(alerts)
        acknowledged_count = sum(1 for alert in alerts if alert.acknowledged)
        critical_count = sum(1 for alert in alerts if alert.is_critical)
        
        severity_counts = {}
        for alert in alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
        
        return {
            "total_alerts": total_alerts,
            "acknowledged_count": acknowledged_count,
            "unacknowledged_count": total_alerts - acknowledged_count,
            "critical_count": critical_count,
            "severity_breakdown": severity_counts,
            "time_period_hours": hours_back,
            "last_updated": datetime.utcnow().isoformat()
        }