"""Network agent integration service."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.network_agent.models.session import AgentSession, DeviceInfo
from app.network_agent.models.command import CommandHistory, AgentConfig

logger = logging.getLogger(__name__)


class NetworkAgentService:
    """Service for integrating with Network AI Agent."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.network_agent_api_url
        self.timeout = self.settings.network_agent_timeout
        
    async def health_check(self) -> Dict[str, Any]:
        """Check Network Agent service health."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return {
                    "status": "healthy",
                    "agent_status": response.json(),
                    "timestamp": datetime.utcnow().isoformat()
                }
        except httpx.RequestError as e:
            logger.error(f"Network Agent health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Network Agent returned error status: {e.response.status_code}")
            return {
                "status": "degraded",
                "error": f"HTTP {e.response.status_code}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def query_agent(
        self, 
        question: str, 
        device_name: Optional[str] = None,
        chat_history: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a natural language query to the AI agent."""
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=60) as client:  # Longer timeout for AI responses
                payload = {
                    "question": question,
                    "device_name": device_name,
                    "chat_history": chat_history or ""
                }
                
                response = await client.post(
                    f"{self.base_url}/query",
                    json=payload
                )
                response.raise_for_status()
                
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                result = response.json()
                
                return {
                    "answer": result.get("answer", "No response available"),
                    "device_used": result.get("device_used", device_name),
                    "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
                    "status": result.get("status", "success"),
                    "response_time_ms": response_time
                }
                
        except httpx.RequestError as e:
            logger.error(f"Failed to query agent: {e}")
            return {
                "answer": f"Connection error: {str(e)}",
                "status": "error",
                "error": str(e),
                "response_time_ms": None
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Agent query failed: {e.response.status_code}")
            return {
                "answer": f"Agent error: HTTP {e.response.status_code}",
                "status": "error",
                "error": f"HTTP {e.response.status_code}",
                "response_time_ms": None
            }
    
    async def execute_command(
        self, 
        command: str, 
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a specific command on a device."""
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=45) as client:
                payload = {
                    "command": command,
                    "device_name": device_name
                }
                
                response = await client.post(
                    f"{self.base_url}/command",
                    json=payload
                )
                response.raise_for_status()
                
                execution_time = (time.time() - start_time) * 1000
                result = response.json()
                
                return {
                    "output": result.get("output", "No output"),
                    "device_used": result.get("device", device_name),
                    "output_type": result.get("output_type", "unknown"),
                    "status": "success" if "error" not in result else "error",
                    "execution_time_ms": execution_time,
                    "raw_result": result
                }
                
        except httpx.RequestError as e:
            logger.error(f"Failed to execute command: {e}")
            return {
                "output": f"Connection error: {str(e)}",
                "status": "error",
                "error": str(e),
                "execution_time_ms": None
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Command execution failed: {e.response.status_code}")
            return {
                "output": f"Execution error: HTTP {e.response.status_code}",
                "status": "error",
                "error": f"HTTP {e.response.status_code}",
                "execution_time_ms": None
            }
    
    async def discover_devices(self) -> Dict[str, Any]:
        """Discover available devices in the lab."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/devices")
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Failed to discover devices: {e}")
            return {
                "devices": [],
                "error": str(e),
                "status": "error"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Device discovery failed: {e.response.status_code}")
            return {
                "devices": [],
                "error": f"HTTP {e.response.status_code}",
                "status": "error"
            }
    
    async def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to all lab devices."""
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.get(f"{self.base_url}/connectivity")
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Failed to test connectivity: {e}")
            return {
                "connectivity_results": [],
                "error": str(e),
                "status": "error"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Connectivity test failed: {e.response.status_code}")
            return {
                "connectivity_results": [],
                "error": f"HTTP {e.response.status_code}",
                "status": "error"
            }

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List tools from the external Network AI Agent."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/tools")
                response.raise_for_status()
                tools = response.json()
                return tools if isinstance(tools, list) else []
        except Exception as e:
            logger.error(f"Failed to list tools from agent: {e}")
            return []

    async def run_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a tool via the external Network AI Agent."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/run",
                    json={"name": name, "params": params},
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Tool run request error: {e}")
            return {"status": "error", "error": str(e)}
        except httpx.HTTPStatusError as e:
            logger.error(f"Tool run failed: HTTP {e.response.status_code}")
            try:
                return {"status": "error", "error": e.response.json()}
            except Exception:
                return {"status": "error", "error": f"HTTP {e.response.status_code}"}


class AgentSessionManager:
    """Manager for agent sessions and command history."""
    
    def __init__(self):
        self.agent_service = NetworkAgentService()
    
    def create_session(
        self, 
        db: Session, 
        user_id: int, 
        session_type: str = "network",
        session_name: Optional[str] = None
    ) -> AgentSession:
        """Create a new agent session."""
        session = AgentSession(
            user_id=user_id,
            session_type=session_type,
            session_name=session_name or f"{session_type.title()} Session"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Created new agent session {session.id} for user {user_id}")
        return session
    
    def get_session(self, db: Session, session_id: UUID) -> Optional[AgentSession]:
        """Get a session by ID."""
        return db.query(AgentSession).filter(AgentSession.id == session_id).first()
    
    def get_user_sessions(
        self, 
        db: Session, 
        user_id: int, 
        limit: int = 20
    ) -> List[AgentSession]:
        """Get recent sessions for a user."""
        return db.query(AgentSession).filter(
            AgentSession.user_id == user_id
        ).order_by(
            AgentSession.last_activity.desc()
        ).limit(limit).all()
    
    def update_session_activity(self, db: Session, session_id: UUID):
        """Update session's last activity timestamp."""
        session = self.get_session(db, session_id)
        if session:
            session.last_activity = datetime.utcnow()
            db.commit()
    
    async def process_query(
        self,
        db: Session,
        session_id: UUID,
        user_id: int,
        user_query: str,
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a user query through the AI agent."""
        try:
            # Get chat history for context
            chat_history = self.get_session_chat_history(db, session_id)
            
            # Query the agent
            agent_response = await self.agent_service.query_agent(
                question=user_query,
                device_name=device_name,
                chat_history=chat_history
            )
            
            # Store command history
            command_history = CommandHistory(
                session_id=session_id,
                user_id=user_id,
                user_query=user_query,
                command_type="natural_language",
                device_name=device_name,
                agent_response=agent_response.get("answer"),
                execution_status="success" if agent_response.get("status") == "success" else "error",
                response_time_ms=agent_response.get("response_time_ms"),
                error_message=agent_response.get("error") if agent_response.get("status") != "success" else None
            )
            
            db.add(command_history)
            
            # Update session activity
            self.update_session_activity(db, session_id)
            
            db.commit()
            
            return {
                "status": "success",
                "response": agent_response,
                "command_id": str(command_history.id)
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process query: {e}")
            return {
                "status": "error",
                "error": str(e),
                "response": {
                    "answer": "Sorry, I encountered an error processing your request.",
                    "status": "error"
                }
            }
    
    async def execute_direct_command(
        self,
        db: Session,
        session_id: UUID,
        user_id: int,
        command: str,
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a direct command on a device."""
        try:
            # Execute command through agent
            execution_result = await self.agent_service.execute_command(
                command=command,
                device_name=device_name
            )
            
            # Store command history
            command_history = CommandHistory(
                session_id=session_id,
                user_id=user_id,
                user_query=f"Execute: {command}",
                command_type="direct_command",
                device_name=device_name,
                executed_command=command,
                execution_status="success" if execution_result.get("status") == "success" else "error",
                raw_output=execution_result.get("output"),
                execution_time_ms=execution_result.get("execution_time_ms"),
                error_message=execution_result.get("error") if execution_result.get("status") != "success" else None
            )
            
            db.add(command_history)
            
            # Update session activity
            self.update_session_activity(db, session_id)
            
            db.commit()
            
            return {
                "status": "success",
                "result": execution_result,
                "command_id": str(command_history.id)
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to execute command: {e}")
            return {
                "status": "error",
                "error": str(e),
                "result": {
                    "output": "Command execution failed",
                    "status": "error"
                }
            }
    
    def get_session_chat_history(
        self, 
        db: Session, 
        session_id: UUID, 
        limit: int = 10
    ) -> str:
        """Get formatted chat history for a session."""
        commands = db.query(CommandHistory).filter(
            CommandHistory.session_id == session_id
        ).order_by(
            CommandHistory.timestamp.desc()
        ).limit(limit).all()
        
        history_lines = []
        for cmd in reversed(commands):  # Reverse to get chronological order
            history_lines.append(f"User: {cmd.user_query}")
            if cmd.agent_response:
                history_lines.append(f"Assistant: {cmd.agent_response}")
            elif cmd.raw_output:
                history_lines.append(f"Output: {cmd.raw_output[:200]}...")  # Truncate long outputs
        
        return "\n".join(history_lines)
    
    def get_command_history(
        self, 
        db: Session, 
        session_id: UUID, 
        limit: int = 50
    ) -> List[CommandHistory]:
        """Get command history for a session."""
        return db.query(CommandHistory).filter(
            CommandHistory.session_id == session_id
        ).order_by(
            CommandHistory.timestamp.desc()
        ).limit(limit).all()
    
    async def sync_devices(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Sync device information from the agent."""
        try:
            # Discover devices through agent
            discovery_result = await self.agent_service.discover_devices()
            
            if discovery_result.get("status") == "error":
                return discovery_result
            
            devices_data = discovery_result.get("devices", [])
            synced_count = 0
            
            for device_data in devices_data:
                device_name = device_data.get("name") or device_data.get("hostname")
                if not device_name:
                    continue
                
                # Check if device already exists
                existing_device = db.query(DeviceInfo).filter(
                    DeviceInfo.device_name == device_name
                ).first()
                
                if existing_device:
                    # Update existing device
                    existing_device.is_reachable = device_data.get("status", "unknown")
                    existing_device.last_seen = datetime.utcnow()
                    existing_device.updated_at = datetime.utcnow()
                else:
                    # Create new device
                    device = DeviceInfo(
                        device_name=device_name,
                        device_type=device_data.get("type"),
                        ip_address=device_data.get("ip"),
                        hostname=device_data.get("hostname"),
                        is_reachable=device_data.get("status", "unknown"),
                        last_seen=datetime.utcnow(),
                        os_type=device_data.get("os"),
                        discovered_by=user_id
                    )
                    db.add(device)
                
                synced_count += 1
            
            db.commit()
            
            return {
                "status": "success",
                "synced_devices": synced_count,
                "total_discovered": len(devices_data)
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync devices: {e}")
            return {
                "status": "error",
                "error": str(e)
            }