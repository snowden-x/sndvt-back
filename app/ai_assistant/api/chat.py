"""Chat API endpoints."""

import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.ai_assistant.models.chat import QueryRequest
from app.ai_assistant.services.chat_service import ChatService
from app.ai_assistant.services.model_service import ModelService

router = APIRouter(tags=["AI Assistant"])

# Global service instances (will be initialized by the main app)
chat_service: ChatService = None


def initialize_chat_api(model_service: ModelService):
    """Initialize the chat API with required services."""
    global chat_service
    chat_service = ChatService(model_service)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming communication."""
    await websocket.accept()
    print("🔌 WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                query = message_data.get("query", "")
                
                if not query.strip():
                    await websocket.send_text(json.dumps({"error": "Empty query received"}))
                    continue
                
                print(f"📨 Processing WebSocket query: {query[:50]}...")
                
                # Stream the response
                async for response_chunk in chat_service.stream_query_response(query):
                    await websocket.send_text(response_chunk)
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                print(f"Error processing WebSocket message: {e}")
                await websocket.send_text(json.dumps({"error": f"Error processing message: {str(e)}"}))
                
    except WebSocketDisconnect:
        print("🔌 WebSocket connection closed")
    except Exception as e:
        print(f"WebSocket error: {e}")


@router.post("/ask", summary="Ask the AI Assistant a question with streaming")
async def ask_question(request: QueryRequest):
    """
    Streaming endpoint that returns real-time response chunks.
    """
    if chat_service is None:
        raise HTTPException(status_code=500, detail="Chat service is not initialized. Check server logs for errors.")
    
    print(f"📨 Received HTTP streaming query: {request.query[:50]}...")
    
    async def generate_sse_response():
        try:
            async for response_chunk in chat_service.stream_query_response(request.query):
                # Convert to SSE format
                yield f"data: {response_chunk}\n\n"
        except Exception as e:
            print(f"Error during HTTP streaming: {e}")
            error_response = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {error_response}\n\n"

    return StreamingResponse(
        generate_sse_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    ) 