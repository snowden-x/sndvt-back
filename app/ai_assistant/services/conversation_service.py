"""Service for managing conversation persistence."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.conversation import Conversation, ConversationMessage
from ..models.chat import ChatMessage


class ConversationService:
    """Service for managing conversation persistence."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_conversation(self, user_id: int, title: str = "New Conversation") -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            title=title,
            user_id=user_id
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """Get a conversation by ID for a specific user."""
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
    
    def get_user_conversations(self, user_id: int, include_archived: bool = False) -> List[Conversation]:
        """Get all conversations for a user."""
        query = self.db.query(Conversation).filter(Conversation.user_id == user_id)
        
        if not include_archived:
            query = query.filter(Conversation.is_archived == False)
        
        return query.order_by(desc(Conversation.updated_at)).all()
    
    def add_message_to_conversation(
        self,
        conversation_id: int,
        message_type: str,
        content: str,
        sources: Optional[List[str]] = None,
        message_metadata: Optional[dict] = None
    ) -> ConversationMessage:
        """Add a message to a conversation."""
        message = ConversationMessage(
            conversation_id=conversation_id,
            message_type=message_type,
            content=content,
            sources=sources,
            message_metadata=message_metadata
        )
        self.db.add(message)
        
        # Update conversation timestamp
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            # Trigger updated_at update
            conversation.updated_at = conversation.updated_at
        
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_conversation_messages(self, conversation_id: int) -> List[ConversationMessage]:
        """Get all messages for a conversation."""
        return self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.created_at).all()
    
    def convert_db_messages_to_chat_messages(self, db_messages: List[ConversationMessage]) -> List[ChatMessage]:
        """Convert database messages to ChatMessage format for the AI service."""
        chat_messages = []
        for db_msg in db_messages:
            if db_msg.message_type in ['user', 'assistant']:
                sender = 'user' if db_msg.message_type == 'user' else 'ai'
                chat_messages.append(ChatMessage(
                    id=str(db_msg.id),
                    sender=sender,
                    text=db_msg.content,
                    timestamp=db_msg.created_at.isoformat()
                ))
        return chat_messages
    
    def update_conversation_title(self, conversation_id: int, user_id: int, title: str) -> bool:
        """Update a conversation's title."""
        conversation = self.get_conversation(conversation_id, user_id)
        if conversation:
            conversation.title = title
            self.db.commit()
            return True
        return False
    
    def archive_conversation(self, conversation_id: int, user_id: int) -> bool:
        """Archive a conversation."""
        conversation = self.get_conversation(conversation_id, user_id)
        if conversation:
            conversation.is_archived = True
            self.db.commit()
            return True
        return False
    
    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """Delete a conversation."""
        conversation = self.get_conversation(conversation_id, user_id)
        if conversation:
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False
    
    def generate_conversation_title(self, first_message: str) -> str:
        """Generate a conversation title from the first message."""
        # Simple title generation - take first 50 chars and clean up
        title = first_message.strip()[:50]
        if len(first_message) > 50:
            title += "..."
        
        # Remove newlines and extra spaces
        title = " ".join(title.split())
        
        # If title is empty or too short, use default
        if len(title.strip()) < 5:
            title = "New Conversation"
        
        return title
