"""Summary service for managing conversation summaries."""

import asyncio
from typing import List, Optional
from datetime import datetime

from ..models.chat import ChatMessage, ConversationSummary
from .model_service import ModelService


class SummaryService:
    """Service for generating and managing conversation summaries."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        
    async def generate_summary(
        self, 
        current_summary: Optional[ConversationSummary],
        recent_messages: List[ChatMessage]
    ) -> ConversationSummary:
        """Generate or update a conversation summary."""
        
        if not recent_messages:
            return current_summary or ConversationSummary(
                summary="No conversation yet.",
                message_count=0,
                last_updated=datetime.now().isoformat()
            )
        
        # Prepare the summarization prompt
        if current_summary and current_summary.summary != "No conversation yet.":
            prompt = self._create_update_summary_prompt(current_summary, recent_messages)
        else:
            prompt = self._create_initial_summary_prompt(recent_messages)
        
        try:
            # Generate summary using the model service
            summary_text = await self._generate_summary_text(prompt)
            
            return ConversationSummary(
                summary=summary_text,
                last_updated=datetime.now().isoformat(),
                message_count=(current_summary.message_count if current_summary else 0) + len(recent_messages)
            )
        except Exception as e:
            print(f"Error generating summary: {e}")
            # Return current summary or a default one
            return current_summary or ConversationSummary(
                summary="Error generating summary.",
                message_count=len(recent_messages),
                last_updated=datetime.now().isoformat()
            )
    
    def _create_initial_summary_prompt(self, messages: List[ChatMessage]) -> str:
        """Create prompt for initial conversation summary."""
        conversation_text = self._format_messages_for_summary(messages)
        
        return f"""Please create a concise summary of this conversation. Focus on:
- Key topics discussed
- Important information shared
- User's main questions or concerns
- Any technical details or context that should be remembered

Conversation:
{conversation_text}

Summary:"""

    def _create_update_summary_prompt(
        self, 
        current_summary: ConversationSummary, 
        new_messages: List[ChatMessage]
    ) -> str:
        """Create prompt for updating existing summary."""
        new_conversation_text = self._format_messages_for_summary(new_messages)
        
        return f"""Please update the following conversation summary with the new messages. 
Keep the summary concise but comprehensive. Preserve important context while incorporating new information.

Current Summary:
{current_summary.summary}

New Messages:
{new_conversation_text}

Updated Summary:"""

    def _format_messages_for_summary(self, messages: List[ChatMessage]) -> str:
        """Format messages for inclusion in summary prompts."""
        formatted = []
        for msg in messages:
            sender = "User" if msg.sender == "user" else "AI"
            formatted.append(f"{sender}: {msg.text}")
        return "\n".join(formatted)
    
    async def _generate_summary_text(self, prompt: str) -> str:
        """Generate summary text using the model service."""
        try:
            # Use the model service to generate the summary
            # This is a simple implementation - you might want to use a specific model or settings
            response = ""
            async for chunk in self.model_service.stream_query_response(prompt, ""):
                if chunk.get("type") == "chunk" and chunk.get("content"):
                    response += chunk["content"]
            
            return response.strip()
        except Exception as e:
            print(f"Error in summary generation: {e}")
            return "Summary generation failed." 