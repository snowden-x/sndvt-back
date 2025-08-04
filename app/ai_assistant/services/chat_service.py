"""Chat service for handling streaming responses."""

import json
import time
import asyncio
from typing import AsyncGenerator, List, Optional
from langchain.chains import RetrievalQA

from app.config import get_settings
from .model_service import ModelService
from .tool_service import ToolService
from ..models.chat import ChatMessage


class ChatService:
    """Service for handling chat interactions and streaming responses."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        self.tool_service = ToolService()
        self.settings = get_settings()
        
    def _format_conversation_history(self, conversation_history: List[ChatMessage]) -> str:
        """Format conversation history for inclusion in the prompt."""
        if not conversation_history:
            return ""
        
        # Limit conversation history to prevent token overflow
        max_history_messages = 10  # Keep last 10 messages
        recent_history = conversation_history[-max_history_messages:]
        
        formatted_history = []
        for msg in recent_history:
            if msg.sender == 'user':
                formatted_history.append(f"Human: {msg.text}")
            elif msg.sender == 'ai':
                formatted_history.append(f"Assistant: {msg.text}")
        
        return "\n".join(formatted_history)
        
    async def stream_query_response(self, query: str, conversation_history: Optional[List[ChatMessage]] = None) -> AsyncGenerator[str, None]:
        """Stream the response from the LLM in real-time with conversation context."""
        qa_chain = self.model_service.get_qa_chain()
        llm = self.model_service.get_llm()
        
        if qa_chain is None:
            yield json.dumps({"error": "QA chain is not initialized"})
            return
        
        # Preprocess query for better results
        query = query.strip()
        if not query:
            yield json.dumps({"error": "Empty query provided"})
            return
        
        # Format conversation history
        conversation_context = ""
        if conversation_history:
            conversation_context = self._format_conversation_history(conversation_history)
            print(f"📜 Using conversation history with {len(conversation_history)} messages")
        
        # Limit query length to prevent issues
        if len(query) > self.settings.max_query_length:
            query = query[:self.settings.max_query_length] + "..."
            print(f"⚠️ Query truncated to {self.settings.max_query_length} characters")
        
        print(f"🚀 Starting streaming response for: {query[:50]}...")
        stream_start_time = time.time()
        
        try:
            if isinstance(qa_chain, RetrievalQA):
                # For retrieval QA, we need to handle streaming differently
                print("📚 Using RetrievalQA with streaming")
                
                # Get relevant documents first (with timeout to prevent hanging)
                retrieval_start_time = time.time()
                retriever = qa_chain.retriever
                try:
                    docs = await asyncio.wait_for(retriever.ainvoke(query), timeout=5.0)
                    retrieval_end_time = time.time()
                    print(f"⏱️ Document retrieval took: {retrieval_end_time - retrieval_start_time:.2f}s")
                    print(f"📄 Retrieved {len(docs)} documents")
                except asyncio.TimeoutError:
                    retrieval_end_time = time.time()
                    print(f"⏱️ Document retrieval timed out after: {retrieval_end_time - retrieval_start_time:.2f}s")
                    print("⚠️ Document retrieval timeout, using general knowledge")
                    docs = []
                
                # Prepare context with smart truncation for performance
                context_parts = []
                total_chars = 0
                
                for doc in docs:
                    if total_chars + len(doc.page_content) > self.settings.max_context_chars:
                        remaining_space = self.settings.max_context_chars - total_chars
                        if remaining_space > 100:  # Only add if there's reasonable space
                            context_parts.append(doc.page_content[:remaining_space] + "...")
                        break
                    
                    context_parts.append(doc.page_content)
                    total_chars += len(doc.page_content)

                # Handle empty context gracefully
                if context_parts:
                    context = "\n\n".join(context_parts)
                    # Enhanced prompt with conversation history
                    if conversation_context:
                        prompt_text = f"""Previous conversation:
{conversation_context}

Documentation context:
{context}

Current question: {query}

Please answer the current question considering both the conversation history and the documentation context. If the question refers to something from our previous conversation, use that context appropriately."""
                    else:
                        prompt_text = self.model_service.custom_prompt.format(context=context, question=query)
                    print(f"📝 Using documentation context ({total_chars} chars) with conversation history")
                else:
                    # Fallback to general knowledge prompt with conversation history
                    if conversation_context:
                        prompt_text = f"""Previous conversation:
{conversation_context}

Current question: {query}

Please answer the current question considering our conversation history."""
                    else:
                        prompt_text = self.model_service.general_prompt.format(query=query)
                    print("🧠 Using general knowledge with conversation history")
                
                # Stream the LLM response
                print("🔄 Starting LLM streaming...")
                llm_start_time = time.time()
                first_chunk_received = False
                accumulated_response = ""
                
                async for chunk in llm.astream(prompt_text):
                    if not first_chunk_received:
                        first_chunk_time = time.time()
                        print(f"⏱️ Time to first token from LLM: {first_chunk_time - llm_start_time:.2f}s")
                        first_chunk_received = True

                    accumulated_response += chunk
                    yield json.dumps({
                        "type": "chunk",
                        "content": chunk,
                        "accumulated": accumulated_response
                    })
                
                # Send final message with sources
                total_time = time.time() - stream_start_time
                print(f"⏱️ Total stream processing time: {total_time:.2f}s")
                yield json.dumps({
                    "type": "complete",
                    "content": accumulated_response,
                    "sources": [doc.metadata.get('source', 'Unknown') for doc in docs],
                    "used_documentation": len(docs) > 0,
                    "used_conversation_history": bool(conversation_history),
                    "context_size": total_chars if 'total_chars' in locals() else 0,
                    "documents_used": len(docs)
                })
                
            else:
                # Direct LLM streaming with conversation history
                print("🤖 Using direct LLM streaming with conversation history")
                
                if conversation_context:
                    prompt_text = f"""Previous conversation:
{conversation_context}

Current question: {query}

Please answer considering our conversation history."""
                else:
                    prompt_text = f"Question: {query}\n\nAnswer:"
                
                accumulated_response = ""
                
                async for chunk in qa_chain.llm.astream(prompt_text):
                    accumulated_response += chunk
                    yield json.dumps({
                        "type": "chunk", 
                        "content": chunk,
                        "accumulated": accumulated_response
                    })
                
                # Send completion
                yield json.dumps({
                    "type": "complete",
                    "content": accumulated_response,
                    "sources": [],
                    "used_documentation": False,
                    "used_conversation_history": bool(conversation_history)
                })
                
        except Exception as e:
            print(f"❌ Error during streaming: {e}")
            yield json.dumps({
                "type": "error",
                "error": f"Error processing query: {str(e)}"
            })
    
    async def handle_automation_request(self, query: str, conversation_history: Optional[List[ChatMessage]] = None) -> AsyncGenerator[str, None]:
        """Handle automation requests with AI reasoning and tool execution."""
        try:
            # First, let AI analyze the request and suggest tools
            analysis_prompt = f"""
You are a network engineer AI assistant with access to automation tools. Analyze this request and determine if automation tools should be used:

User Request: {query}

Available Tools and Parameters:
- ping_test: Test connectivity to a network device
  Parameters: {{"target": "hostname_or_ip"}}
- health_check: Comprehensive device health check
  Parameters: {{"devices": ["device1", "device2"]}}
- backup_configs: Backup network configurations
  Parameters: {{"devices": ["device1", "device2"]}}
- check_print_server: Check print server health
  Parameters: {{"target": "print_server_hostname_or_ip"}}
- troubleshoot_connectivity: Troubleshoot connectivity issues
  Parameters: {{"source": "source_device", "destination": "target_device"}}
- configure_vlans: Configure VLANs
  Parameters: {{"devices": ["device1"], "vlans": [{{"id": 10, "name": "vlan10"}}]}}

EXAMPLES:
- "ping the print server" → TOOL_CALL:ping_test PARAMS:{{"target": "print_server"}}
- "check if the print server is working" → TOOL_CALL:check_print_server PARAMS:{{"target": "print_server"}}
- "backup network configs" → TOOL_CALL:backup_configs PARAMS:{{"devices": ["router1", "switch1"]}}

If automation is needed, respond with:
TOOL_CALL:<tool_name> PARAMS:{{"param1": "value1", "param2": "value2"}}

If no automation is needed, provide a helpful response based on your knowledge.

Context: {self._format_conversation_history(conversation_history) if conversation_history else ""}
"""
            
            # Get AI analysis
            llm = self.model_service.get_llm()
            if llm is None:
                yield json.dumps({"error": "LLM not available"})
                return
            
            analysis_response = await llm.ainvoke(analysis_prompt)
            
            # Check if AI wants to use a tool
            tool_call = await self.tool_service.parse_tool_request(analysis_response)
            
            if tool_call:
                tool_name, parameters = tool_call
                
                # Send initial response
                yield json.dumps({
                    "type": "start",
                    "content": f"I'll help you with that! Let me use the {tool_name} tool to investigate..."
                })
                
                # Execute the tool
                tool_result = await self.tool_service.execute_tool(tool_name, parameters)
                
                # Send tool result
                yield json.dumps({
                    "type": "tool_result",
                    "tool": tool_name,
                    "success": tool_result.success,
                    "output": tool_result.output,
                    "data": tool_result.data
                })
                
                # Get AI interpretation of results
                interpretation_prompt = f"""
Based on the tool execution results, provide a comprehensive response to the user's original request.

Original Request: {query}
Tool Used: {tool_name}
Tool Results: {tool_result.output}
Tool Data: {tool_result.data}

Provide a helpful, professional response that:
1. Addresses the user's original question
2. Explains what was found
3. Suggests next steps if needed
4. Uses the tool results to provide actionable insights
"""
                
                final_response = await llm.ainvoke(interpretation_prompt)
                
                yield json.dumps({
                    "type": "final_response",
                    "content": final_response
                })
                
            else:
                # No tool needed, provide regular AI response
                async for chunk in self.stream_query_response(query, conversation_history):
                    yield chunk
                    
        except Exception as e:
            yield json.dumps({"error": f"Automation request failed: {str(e)}"}) 