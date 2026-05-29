"""
core/state.py — Session and user state management

Tracks active users by their Socket.IO SID and provides user context.
"""

from typing import Dict, Optional
from datetime import datetime

class User:
    """Represents an active user session"""
    def __init__(self, sid: str, name: str = None):
        self.sid = sid
        self.name = name or f"User_{sid[:6]}"
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()
        self.current_room = None  # Will be set when user joins a room
        self.status = "online"  # online, away, offline
    
    def to_dict(self):
        return {
            "sid": self.sid,
            "name": self.name,
            "connected_at": self.connected_at.isoformat(),
            "status": self.status,
            "current_room": self.current_room
        }

class SessionRegistry:
    """Manages all active user sessions"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
    
    def register_user(self, sid: str, name: str = None) -> User:
        """Register a new user session"""
        user = User(sid, name)
        self.users[sid] = user
        return user
    
    def get_user(self, sid: str) -> Optional[User]:
        """Get user by SID"""
        return self.users.get(sid)
    
    def remove_user(self, sid: str) -> Optional[User]:
        """Unregister a user and return their data"""
        if sid in self.users:
            user = self.users.pop(sid)
            user.status = "offline"
            return user
        return None
    
    def get_all_users(self) -> list:
        """Get all active users as list of dicts"""
        return [user.to_dict() for user in self.users.values()]
    
    def get_online_count(self) -> int:
        """Get number of online users"""
        return len(self.users)
    
    def update_user_status(self, sid: str, status: str):
        """Update user status (online, away, offline)"""
        if user := self.get_user(sid):
            user.status = status
            user.last_seen = datetime.now()
    
    def set_user_room(self, sid: str, room: str):
        """Set user's current room"""
        if user := self.get_user(sid):
            user.current_room = room

# Global registry instance
registry = SessionRegistry()
