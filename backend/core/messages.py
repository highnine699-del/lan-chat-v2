"""
core/messages.py — Unified message protocol

All messages (DMs, room messages, system messages, etc.) 
use the same Message class for consistency.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import json

class MessageType(Enum):
    """All message types"""
    TEXT = "text"
    SYSTEM = "system"
    TYPING = "typing"
    REACTION = "reaction"
    MEDIA = "media"
    VOICE = "voice"
    CALL = "call"

class Message:
    """Unified message class"""
    
    def __init__(
        self,
        message_type: MessageType,
        sender_id: str,
        content: str,
        room_id: str,
        recipient_id: str = None,  # For DMs
        metadata: Dict[str, Any] = None
    ):
        self.id = None  # Set by DB
        self.type = message_type
        self.sender_id = sender_id
        self.sender_name = None  # Will be set by handler
        self.content = content
        self.room_id = room_id
        self.recipient_id = recipient_id  # For DMs
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.is_edited = False
        self.edited_at = None
        self.is_deleted = False
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "room_id": self.room_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp.isoformat(),
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)

class MessageRouter:
    """Routes messages to their destinations"""
    
    @staticmethod
    def get_delivery_targets(message: Message) -> list:
        """
        Determine who should receive this message.
        Returns list of user SIDs or room IDs.
        """
        targets = []
        
        if message.type == MessageType.TYPING:
            # Typing indicators go to everyone in the room
            targets = {"type": "room", "room_id": message.room_id}
        
        elif message.recipient_id:
            # DMs go to specific recipient only
            targets = {"type": "dm", "recipient_id": message.recipient_id}
        
        else:
            # Room messages go to all room members
            targets = {"type": "room", "room_id": message.room_id}
        
        return targets
    
    @staticmethod
    def should_persist(message: Message) -> bool:
        """Determine if message should be saved to DB"""
        # Don't persist typing indicators or ephemeral messages
        if message.type in [MessageType.TYPING]:
            return False
        return True
    
    @staticmethod
    def should_broadcast_to_offline(message: Message) -> bool:
        """Determine if message should be queued for offline users"""
        # Voice/call messages don't queue
        if message.type in [MessageType.VOICE, MessageType.CALL]:
            return False
        return True

class MessageBuilder:
    """Builder pattern for creating messages"""
    
    def __init__(self, sender_id: str):
        self.sender_id = sender_id
        self.type = MessageType.TEXT
        self.content = ""
        self.room_id = "general"
        self.recipient_id = None
        self.metadata = {}
    
    def set_type(self, msg_type: MessageType) -> 'MessageBuilder':
        self.type = msg_type
        return self
    
    def set_content(self, content: str) -> 'MessageBuilder':
        self.content = content
        return self
    
    def set_room(self, room_id: str) -> 'MessageBuilder':
        self.room_id = room_id
        return self
    
    def set_recipient(self, recipient_id: str) -> 'MessageBuilder':
        self.recipient_id = recipient_id
        self.type = MessageType.TEXT
        return self
    
    def add_metadata(self, key: str, value: Any) -> 'MessageBuilder':
        self.metadata[key] = value
        return self
    
    def build(self) -> Message:
        return Message(
            message_type=self.type,
            sender_id=self.sender_id,
            content=self.content,
            room_id=self.room_id,
            recipient_id=self.recipient_id,
            metadata=self.metadata
        )
