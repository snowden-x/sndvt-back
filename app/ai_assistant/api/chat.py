"""Chat API endpoints."""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.ai_assistant.models.chat import QueryRequest, ChatMessage
from app.ai_assistant.services.chat_service import ChatService
from app.ai_assistant.services.model_service import ModelService
from app.ai_assistant.services.conversation_service import ConversationService
from app.config.database import get_db
from app.core.dependencies import get_current_user
from app.auth.models.user import User

router = APIRouter(tags=["AI Assistant"])

# Global service instances (will be initialized by the main app)
chat_service: ChatService = None


class ConversationQueryRequest(BaseModel):
    query: str
    conversation_id: Optional[int] = None
    conversation_title: Optional[str] = None


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
                conversation_history_data = message_data.get("conversation_history", [])
                
                if not query.strip():
                    await websocket.send_text(json.dumps({"error": "Empty query received"}))
                    continue
                
                # Parse conversation history
                conversation_history = []
                if conversation_history_data:
                    try:
                        conversation_history = [ChatMessage(**msg) for msg in conversation_history_data]
                        print(f"📜 Parsed {len(conversation_history)} messages from conversation history")
                    except Exception as e:
                        print(f"⚠️ Error parsing conversation history: {e}")
                        conversation_history = []
                
                print(f"📨 Processing WebSocket query: {query[:50]}...")
                
                # Use regular chat response
                async for response_chunk in chat_service.stream_query_response(query, conversation_history):
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
    print(f"📜 Conversation history length: {len(request.conversation_history)}")
    if request.conversation_history:
        print(f"📜 First message: {request.conversation_history[0]}")
    
    async def generate_sse_response():
        try:
            # Use regular chat response
            async for response_chunk in chat_service.stream_query_response(request.query, request.conversation_history):
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


@router.post("/chat", summary="Chat with conversation persistence")
async def chat_with_persistence(
    request: ConversationQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Streaming endpoint with conversation persistence.
    Creates or continues a conversation and saves all messages.
    """
    if chat_service is None:
        raise HTTPException(status_code=500, detail="Chat service is not initialized. Check server logs for errors.")
    
    conversation_service = ConversationService(db)
    
    # Get or create conversation
    conversation = None
    if request.conversation_id:
        conversation = conversation_service.get_conversation(request.conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        title = request.conversation_title or conversation_service.generate_conversation_title(request.query)
        conversation = conversation_service.create_conversation(current_user.id, title)
    
    # Add user message to conversation
    user_message = conversation_service.add_message_to_conversation(
        conversation.id,
        "user",
        request.query
    )
    
    # Get conversation history for context
    db_messages = conversation_service.get_conversation_messages(conversation.id)
    # Exclude the just-added user message from history (it will be included in the query)
    history_messages = [msg for msg in db_messages if msg.id != user_message.id]
    conversation_history = conversation_service.convert_db_messages_to_chat_messages(history_messages)
    
    print(f"📨 Chat with persistence: {request.query[:50]}...")
    print(f"📄 Conversation ID: {conversation.id}")
    print(f"📜 History length: {len(conversation_history)}")
    
    async def generate_sse_response():
        accumulated_response = ""
        try:
            # Stream the AI response
            async for response_chunk in chat_service.stream_query_response(request.query, conversation_history):
                chunk_data = json.loads(response_chunk)
                
                # Accumulate the response content
                if chunk_data.get("type") == "chunk":
                    accumulated_response = chunk_data.get("accumulated", accumulated_response)
                elif chunk_data.get("type") == "complete":
                    accumulated_response = chunk_data.get("content", accumulated_response)
                    
                    # Save the assistant's response to the conversation
                    try:
                        conversation_service.add_message_to_conversation(
                            conversation.id,
                            "assistant",
                            accumulated_response,
                            sources=chunk_data.get("sources", []),
                            message_metadata={
                                "used_documentation": chunk_data.get("used_documentation", False),
                                "used_conversation_history": chunk_data.get("used_conversation_history", False),
                                "context_size": chunk_data.get("context_size", 0),
                                "documents_used": chunk_data.get("documents_used", 0)
                            }
                        )
                        
                        # Add conversation_id to the response
                        chunk_data["conversation_id"] = conversation.id
                        chunk_data["conversation_title"] = conversation.title
                        
                    except Exception as e:
                        print(f"Error saving assistant message: {e}")
                
                yield f"data: {json.dumps(chunk_data)}\n\n"
                
        except Exception as e:
            print(f"Error during chat streaming: {e}")
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