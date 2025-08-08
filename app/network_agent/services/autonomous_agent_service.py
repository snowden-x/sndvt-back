"""Service for interfacing with the autonomous network agent."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Dict, Any, AsyncGenerator, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AutonomousAgentService:
    """Service to interact with the autonomous network agent."""
    
    def __init__(self):
        self.agent_path = self._find_agent_path()
        self.python_path = self._find_python_path()
        
    def _find_agent_path(self) -> Optional[str]:
        """Find the autonomous network agent script."""
        # Look for the agent in the Network-ai-agent directory
        possible_paths = [
            "/Users/xsnowdev/Documents/Projects/Network-ai-agent/autonomous_network_agent.py",
            "../Network-ai-agent/autonomous_network_agent.py",
            "../../Network-ai-agent/autonomous_network_agent.py"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        logger.warning("Could not find autonomous network agent script")
        return None
    
    def _find_python_path(self) -> str:
        """Find the Python executable for the autonomous agent (preferably from venv)."""
        # Look for virtual environment Python first
        venv_paths = [
            "/Users/xsnowdev/Documents/Projects/Network-ai-agent/venv_network_agent/bin/python",
            "/Users/xsnowdev/Documents/Projects/Network-ai-agent/venv/bin/python",
        ]
        
        for venv_python in venv_paths:
            if os.path.exists(venv_python):
                logger.info(f"Using virtual environment Python: {venv_python}")
                return venv_python
        
        # Fallback to system Python
        logger.warning("Virtual environment not found, using system Python")
        return sys.executable
    
    async def execute_command(self, user_input: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a command through the autonomous agent and stream results."""
        if not self.agent_path:
            yield {
                "type": "error",
                "message": "Autonomous agent not found",
                "timestamp": asyncio.get_event_loop().time()
            }
            return
        
        try:
            # Create the command to run the agent
            cmd = [
                self.python_path,
                self.agent_path,
                "--input", user_input,
                "--no-confirm"  # Auto-execute safe commands
            ]
            
            logger.info(f"Executing autonomous agent: {' '.join(cmd)}")
            
            # Start the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(self.agent_path)
            )
            
            # Send initial status
            yield {
                "type": "status",
                "message": "🤖 Starting autonomous network agent...",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Read output line by line
            async for line in self._read_process_output(process):
                if line.strip():
                    # Try to parse as JSON first
                    try:
                        data = json.loads(line.strip())
                        if isinstance(data, dict):
                            data["timestamp"] = asyncio.get_event_loop().time()
                            yield data
                        else:
                            yield {
                                "type": "output",
                                "message": str(data),
                                "timestamp": asyncio.get_event_loop().time()
                            }
                    except json.JSONDecodeError:
                        # Not JSON, treat as regular output
                        yield {
                            "type": "output",
                            "message": line.strip(),
                            "timestamp": asyncio.get_event_loop().time()
                        }
            
            # Wait for process to complete
            await process.wait()
            
            if process.returncode == 0:
                yield {
                    "type": "complete",
                    "message": "✅ Task completed successfully",
                    "timestamp": asyncio.get_event_loop().time()
                }
            else:
                # Get error output
                stderr = await process.stderr.read()
                error_msg = stderr.decode() if stderr else "Unknown error"
                yield {
                    "type": "error",
                    "message": f"❌ Task failed: {error_msg}",
                    "timestamp": asyncio.get_event_loop().time()
                }
                
        except Exception as e:
            logger.error(f"Failed to execute autonomous agent: {e}")
            yield {
                "type": "error",
                "message": f"Failed to execute agent: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def _read_process_output(self, process: asyncio.subprocess.Process) -> AsyncGenerator[str, None]:
        """Read process output line by line."""
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode().rstrip('\n\r')
        except Exception as e:
            logger.error(f"Error reading process output: {e}")
    
    async def interactive_session(self, websocket) -> AsyncGenerator[Dict[str, Any], None]:
        """Start an interactive session with the autonomous agent."""
        if not self.agent_path:
            yield {
                "type": "error",
                "message": "Autonomous agent not found",
                "timestamp": asyncio.get_event_loop().time()
            }
            return
        
        try:
            # Start the interactive agent process
            cmd = [
                self.python_path,
                self.agent_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(self.agent_path)
            )
            
            yield {
                "type": "status",
                "message": "🤖 Interactive autonomous agent started",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Create tasks for reading output and handling input
            read_task = asyncio.create_task(self._handle_agent_output(process, websocket))
            write_task = asyncio.create_task(self._handle_agent_input(process, websocket))
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [read_task, write_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            # Cleanup process
            if process.returncode is None:
                process.terminate()
                await process.wait()
                
        except Exception as e:
            logger.error(f"Failed to start interactive session: {e}")
            yield {
                "type": "error",
                "message": f"Failed to start interactive session: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def _handle_agent_output(self, process: asyncio.subprocess.Process, websocket):
        """Handle output from the agent process."""
        try:
            async for line in self._read_process_output(process):
                if line.strip():
                    try:
                        # Try to parse as JSON
                        data = json.loads(line.strip())
                        if isinstance(data, dict):
                            data["timestamp"] = asyncio.get_event_loop().time()
                            await websocket.send_json(data)
                        else:
                            await websocket.send_json({
                                "type": "output",
                                "message": str(data),
                                "timestamp": asyncio.get_event_loop().time()
                            })
                    except json.JSONDecodeError:
                        # Regular text output
                        await websocket.send_json({
                            "type": "output",
                            "message": line.strip(),
                            "timestamp": asyncio.get_event_loop().time()
                        })
        except Exception as e:
            logger.error(f"Error handling agent output: {e}")
    
    async def _handle_agent_input(self, process: asyncio.subprocess.Process, websocket):
        """Handle input to the agent process."""
        try:
            while True:
                # Wait for input from websocket
                data = await websocket.receive_json()
                if data.get("type") == "input":
                    user_input = data.get("message", "")
                    if user_input:
                        # Send to agent process
                        process.stdin.write(f"{user_input}\n".encode())
                        await process.stdin.drain()
        except Exception as e:
            logger.error(f"Error handling agent input: {e}")
