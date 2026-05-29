"""
core/events.py — Event-driven architecture

Provides a central event bus for decoupled communication
instead of direct function calls. Enables:
- Event logging & replay
- Plugin system support
- Better observability
- Easier testing
"""

from typing import Callable, Dict, List, Any
from datetime import datetime
from enum import Enum
import json

class EventType(Enum):
    """All system events"""
    # User events
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnected"
    USER_JOINED_ROOM = "user.joined_room"
    USER_LEFT_ROOM = "user.left_room"
    USER_TYPING = "user.typing"
    USER_STOPPED_TYPING = "user.stopped_typing"
    
    # Message events
    MESSAGE_SENT = "message.sent"
    MESSAGE_DELETED = "message.deleted"
    MESSAGE_EDITED = "message.edited"
    MESSAGE_REACTED = "message.reacted"
    
    # Room events
    ROOM_CREATED = "room.created"
    ROOM_DELETED = "room.deleted"
    
    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_STARTUP = "system.startup"

class Event:
    """Represents a system event"""
    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now()
        self.id = f"{event_type.value}_{int(self.timestamp.timestamp() * 1000)}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

class EventBus:
    """Central event bus for the application"""
    
    def __init__(self):
        self.listeners: Dict[EventType, List[Callable]] = {}
        self.event_log: List[Event] = []
        self.max_log_size = 1000
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to events of a specific type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        print(f"[EVENT] Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from events"""
        if event_type in self.listeners:
            self.listeners[event_type].remove(callback)
    
    def emit(self, event_type: EventType, data: Dict[str, Any]):
        """Emit an event"""
        event = Event(event_type, data)
        
        # Log event
        self._log_event(event)
        
        # Print for debugging
        print(f"[EVENT] {event_type.value}: {json.dumps(data, default=str)}")
        
        # Notify listeners
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"[ERROR] Event listener error: {e}")
    
    def emit_async(self, event_type: EventType, data: Dict[str, Any]):
        """Emit event asynchronously (for async handlers)"""
        # For now, same as emit (would be enhanced with async/await)
        self.emit(event_type, data)
    
    def _log_event(self, event: Event):
        """Log event to history"""
        self.event_log.append(event)
        
        # Keep log size manageable
        if len(self.event_log) > self.max_log_size:
            self.event_log.pop(0)
    
    def get_event_history(self, event_type: EventType = None, limit: int = 50) -> List[dict]:
        """Get event history"""
        if event_type:
            events = [e for e in self.event_log if e.type == event_type]
        else:
            events = self.event_log
        
        # Return most recent first
        return [e.to_dict() for e in reversed(events[-limit:])]
    
    def get_event_stats(self) -> dict:
        """Get event statistics"""
        stats = {}
        for event in self.event_log:
            event_name = event.type.value
            stats[event_name] = stats.get(event_name, 0) + 1
        return stats

# Global event bus instance
event_bus = EventBus()
