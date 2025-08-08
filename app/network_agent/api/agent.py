"""Network Agent API endpoints."""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.config.database import get_db
from app.network_agent.services.agent_service import NetworkAgentService, AgentSessionManager
from app.network_agent.services.autonomous_agent_service import AutonomousAgentService
from app.network_agent.models.session import AgentSession, DeviceInfo
from app.network_agent.models.command import CommandHistory
from app.core.dependencies import get_current_user
from app.network_agent.tools.registry import registry as tool_registry
from app.auth.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/network-agent", tags=["network-agent"])


# Pydantic models for API requests/responses
class QueryRequest(BaseModel):
    """Request model for agent queries."""
    question: str = Field(..., min_length=1, max_length=1000)
    device_name: Optional[str] = Field(None, max_length=255)
    session_id: Optional[str] = None


class CommandRequest(BaseModel):
    """Request model for direct command execution."""
    command: str = Field(..., min_length=1, max_length=500)
    device_name: Optional[str] = Field(None, max_length=255)
    session_id: Optional[str] = None


class SessionCreateRequest(BaseModel):
    """Request model for creating a new session."""
    session_type: str = Field("network", pattern="^(network|general)$")
    session_name: Optional[str] = Field(None, max_length=255)


class QueryResponse(BaseModel):
    """Response model for agent queries."""
    answer: str
    device_used: Optional[str]
    timestamp: str
    status: str
    command_id: Optional[str]
    response_time_ms: Optional[float]


class CommandResponse(BaseModel):
    """Response model for command execution."""
    output: str
    device_used: Optional[str]
    output_type: str
    status: str
    execution_time_ms: Optional[float]
    command_id: Optional[str]


class SessionResponse(BaseModel):
    """Response model for sessions."""
    id: str
    session_type: str
    session_name: Optional[str]
    created_at: str
    last_activity: str
    is_active: bool
    
    @classmethod
    def from_session(cls, session: AgentSession) -> "SessionResponse":
        return cls(
            id=str(session.id),
            session_type=session.session_type,
            session_name=session.session_name,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            is_active=session.is_active
        )


class CommandHistoryResponse(BaseModel):
    """Response model for command history."""
    id: str
    user_query: str
    command_type: str
    device_name: Optional[str]
    executed_command: Optional[str]
    agent_response: Optional[str]
    raw_output: Optional[str]
    execution_status: str
    timestamp: str
    execution_time_ms: Optional[float]
    response_time_ms: Optional[float]
    
    @classmethod
    def from_command(cls, command: CommandHistory) -> "CommandHistoryResponse":
        return cls(
            id=str(command.id),
            user_query=command.user_query,
            command_type=command.command_type,
            device_name=command.device_name,
            executed_command=command.executed_command,
            agent_response=command.agent_response,
            raw_output=command.raw_output,
            execution_status=command.execution_status,
            timestamp=command.timestamp.isoformat(),
            execution_time_ms=command.execution_time_ms,
            response_time_ms=command.response_time_ms
        )


class DeviceResponse(BaseModel):
    """Response model for devices."""
    id: str
    device_name: str
    device_type: Optional[str]
    ip_address: Optional[str]
    hostname: Optional[str]
    is_reachable: str
    last_seen: Optional[str]
    os_type: Optional[str]
    discovered_at: str
    
    @classmethod
    def from_device(cls, device: DeviceInfo) -> "DeviceResponse":
        return cls(
            id=str(device.id),
            device_name=device.device_name,
            device_type=device.device_type,
            ip_address=device.ip_address,
            hostname=device.hostname,
            is_reachable=device.is_reachable,
            last_seen=device.last_seen.isoformat() if device.last_seen else None,
            os_type=device.os_type,
            discovered_at=device.discovered_at.isoformat()
        )


# Initialize services
agent_service = NetworkAgentService()
session_manager = AgentSessionManager()
autonomous_agent_service = AutonomousAgentService()


@router.get("/health")
async def check_agent_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check Network Agent service health."""
    try:
        health_status = await agent_service.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Failed to check agent health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/query", response_model=QueryResponse)
async def query_agent(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> QueryResponse:
    """Send a natural language query to the AI agent."""
    try:
        # Get or create session
        session_id = None
        if request.session_id:
            try:
                session_id = UUID(request.session_id)
                session = session_manager.get_session(db, session_id)
                if not session or session.user_id != current_user.id:
                    raise HTTPException(status_code=404, detail="Session not found")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid session ID format")
        else:
            # Create new session if none provided
            session = session_manager.create_session(
                db, current_user.id, "network", "Network Troubleshooting"
            )
            session_id = session.id
        
        # Process query
        result = await session_manager.process_query(
            db=db,
            session_id=session_id,
            user_id=current_user.id,
            user_query=request.question,
            device_name=request.device_name
        )
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("error", "Query failed"))
        
        response_data = result["response"]
        return QueryResponse(
            answer=response_data.get("answer", "No response"),
            device_used=response_data.get("device_used"),
            timestamp=response_data.get("timestamp", datetime.utcnow().isoformat()),
            status=response_data.get("status", "success"),
            command_id=result.get("command_id"),
            response_time_ms=response_data.get("response_time_ms")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process query: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@router.post("/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CommandResponse:
    """Execute a direct command on a device."""
    try:
        # Get or create session
        session_id = None
        if request.session_id:
            try:
                session_id = UUID(request.session_id)
                session = session_manager.get_session(db, session_id)
                if not session or session.user_id != current_user.id:
                    raise HTTPException(status_code=404, detail="Session not found")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid session ID format")
        else:
            # Create new session if none provided
            session = session_manager.create_session(
                db, current_user.id, "network", "Direct Commands"
            )
            session_id = session.id
        
        # Execute command
        result = await session_manager.execute_direct_command(
            db=db,
            session_id=session_id,
            user_id=current_user.id,
            command=request.command,
            device_name=request.device_name
        )
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("error", "Command execution failed"))
        
        execution_data = result["result"]
        return CommandResponse(
            output=execution_data.get("output", "No output"),
            device_used=execution_data.get("device_used"),
            output_type=execution_data.get("output_type", "unknown"),
            status=execution_data.get("status", "success"),
            execution_time_ms=execution_data.get("execution_time_ms"),
            command_id=result.get("command_id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[SessionResponse]:
    """Get user's agent sessions."""
    try:
        sessions = session_manager.get_user_sessions(db, current_user.id, limit)
        return [SessionResponse.from_session(session) for session in sessions]
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SessionResponse:
    """Create a new agent session."""
    try:
        session = session_manager.create_session(
            db=db,
            user_id=current_user.id,
            session_type=request.session_type,
            session_name=request.session_name
        )
        return SessionResponse.from_session(session)
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SessionResponse:
    """Get a specific session."""
    try:
        session_uuid = UUID(session_id)
        session = session_manager.get_session(db, session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return SessionResponse.from_session(session)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.get("/sessions/{session_id}/history", response_model=List[CommandHistoryResponse])
async def get_session_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[CommandHistoryResponse]:
    """Get command history for a session."""
    try:
        session_uuid = UUID(session_id)
        session = session_manager.get_session(db, session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        commands = session_manager.get_command_history(db, session_uuid, limit)
        return [CommandHistoryResponse.from_command(cmd) for cmd in commands]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session history")


class ToolListItem(BaseModel):
    name: str
    description: str
    risk_level: str
    read_only: bool
    input_spec: Dict[str, str]


class ToolRunRequest(BaseModel):
    name: str
    params: Dict[str, Any]


@router.get("/tools", response_model=List[ToolListItem])
async def list_tools(
    current_user: User = Depends(get_current_user)
) -> List[ToolListItem]:
    """List available autonomous tools."""
    tools = tool_registry.list()
    return [ToolListItem(**t) for t in tools]


@router.post("/tools/run")
async def run_tool(
    request: ToolRunRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Run a tool (policy/guardrails to be added)."""
    result = await tool_registry.run(request.name, request.params)
    return result


@router.get("/devices", response_model=List[DeviceResponse])
async def get_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[DeviceResponse]:
    """Get discovered network devices."""
    try:
        devices = db.query(DeviceInfo).order_by(DeviceInfo.discovered_at.desc()).all()
        return [DeviceResponse.from_device(device) for device in devices]
    except Exception as e:
        logger.error(f"Failed to get devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve devices")


@router.get("/tools", response_model=List[ToolListItem])
async def proxy_list_tools(
    current_user: User = Depends(get_current_user)
) -> List[ToolListItem]:
    """Proxy to Network AI Agent tools list."""
    try:
        tools = await agent_service.list_tools()
        # Coerce to schema
        items = []
        for t in tools:
            items.append(
                ToolListItem(
                    name=str(t.get("name")),
                    description=str(t.get("description", "")),
                    risk_level=str(t.get("risk_level", "read_only")),
                    read_only=bool(t.get("read_only", True)),
                    input_spec={k: str(v) for k, v in (t.get("input_spec") or {}).items()},
                )
            )
        return items
    except Exception as e:
        logger.error(f"Failed to proxy tools list: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tools")


class ToolRunProxyRequest(BaseModel):
    name: str
    params: Dict[str, Any]


@router.post("/tools/run")
async def proxy_run_tool(
    request: ToolRunProxyRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Proxy to Network AI Agent tool run."""
    try:
        result = await agent_service.run_tool(request.name, request.params)
        return result
    except Exception as e:
        logger.error(f"Failed to proxy tool run: {e}")
        raise HTTPException(status_code=500, detail="Failed to run tool")


@router.post("/devices/discover")
async def discover_devices(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Discover devices and sync with database."""
    try:
        result = await session_manager.sync_devices(db, current_user.id)
        return result
    except Exception as e:
        logger.error(f"Failed to discover devices: {e}")
        raise HTTPException(status_code=500, detail=f"Device discovery failed: {str(e)}")


@router.get("/devices/connectivity")
async def test_connectivity(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Test connectivity to all devices."""
    try:
        result = await agent_service.test_connectivity()
        return result
    except Exception as e:
        logger.error(f"Failed to test connectivity: {e}")
        raise HTTPException(status_code=500, detail=f"Connectivity test failed: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a session and its history."""
    try:
        session_uuid = UUID(session_id)
        session = session_manager.get_session(db, session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        db.delete(session)
        db.commit()
        
        return {"message": "Session deleted successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.websocket("/autonomous")
async def autonomous_agent_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time autonomous agent interaction."""
    await websocket.accept()
    logger.info("WebSocket connection established for autonomous agent")
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "🤖 Connected to Autonomous Network Agent",
            "timestamp": asyncio.get_event_loop().time()
        })
        
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "execute":
                    # Execute a single command
                    user_input = data.get("message", "")
                    if user_input:
                        logger.info(f"Executing command via WebSocket: {user_input}")
                        
                        # Stream results back to client
                        async for result in autonomous_agent_service.execute_command(user_input):
                            await websocket.send_json(result)
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No command provided",
                            "timestamp": asyncio.get_event_loop().time()
                        })
                
                elif message_type == "interactive":
                    # Start interactive session
                    logger.info("Starting interactive autonomous agent session")
                    await websocket.send_json({
                        "type": "status",
                        "message": "🔄 Starting interactive session...",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    
                    # This will handle the interactive session
                    async for result in autonomous_agent_service.interactive_session(websocket):
                        await websocket.send_json(result)
                
                elif message_type == "ping":
                    # Health check
                    await websocket.send_json({
                        "type": "pong",
                        "message": "WebSocket connection active",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON received",
                    "timestamp": asyncio.get_event_loop().time()
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"WebSocket error: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            })
        except:
            pass  # Connection might be closed
    finally:
        logger.info("WebSocket connection terminated")