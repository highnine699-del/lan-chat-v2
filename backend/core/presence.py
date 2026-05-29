"""
core/presence.py — Online/offline presence tracking
"""

from typing import List, Dict, Callable
from enum import Enum

class PresenceStatus(Enum):
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"

class PresenceManager:
    """Manages user presence and status changes"""
    
    def __init__(self):
        self.presence: Dict[str, PresenceStatus] = {}
        self.listeners: List[Callable] = []
    
    def set_presence(self, sid: str, status: PresenceStatus):
        """Set user presence status"""
        old_status = self.presence.get(sid)
        self.presence[sid] = status
        
        # Only notify if status actually changed
        if old_status != status:
            self._notify_listeners("presence_changed", {
                "sid": sid,
                "old_status": old_status.value if old_status else None,
                "new_status": status.value
            })
    
    def get_presence(self, sid: str) -> PresenceStatus:
        """Get user presence status"""
        return self.presence.get(sid, PresenceStatus.OFFLINE)
    
    def is_online(self, sid: str) -> bool:
        """Check if user is online"""
        return self.get_presence(sid) == PresenceStatus.ONLINE
    
    def get_online_users(self) -> List[str]:
        """Get list of online user SIDs"""
        return [sid for sid, status in self.presence.items() 
                if status == PresenceStatus.ONLINE]
    
    def remove_presence(self, sid: str):
        """Remove presence record (user disconnected)"""
        if sid in self.presence:
            del self.presence[sid]
    
    def subscribe(self, callback: Callable):
        """Subscribe to presence changes"""
        self.listeners.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from presence changes"""
        if callback in self.listeners:
            self.listeners.remove(callback)
    
    def _notify_listeners(self, event_type: str, data: dict):
        """Notify all listeners of presence changes"""
        for listener in self.listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                print(f"Error in presence listener: {e}")

# Global presence manager instance
presence_manager = PresenceManager()
