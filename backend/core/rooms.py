"""
core/rooms.py — Room management (create, join, leave, broadcast)
"""

from typing import Dict, List, Optional, Set
from datetime import datetime

class Room:
    """Represents a chat room"""
    def __init__(self, name: str, room_id: str = None):
        self.room_id = room_id or name.lower().replace(" ", "_")
        self.name = name
        self.created_at = datetime.now()
        self.members: Set[str] = set()  # SIDs of members
        self.is_private = False
    
    def add_member(self, sid: str) -> bool:
        """Add user to room. Returns True if newly added."""
        if sid not in self.members:
            self.members.add(sid)
            return True
        return False
    
    def remove_member(self, sid: str) -> bool:
        """Remove user from room. Returns True if removed."""
        if sid in self.members:
            self.members.discard(sid)
            return True
        return False
    
    def get_member_count(self) -> int:
        """Get number of members in room"""
        return len(self.members)
    
    def has_member(self, sid: str) -> bool:
        """Check if user is in room"""
        return sid in self.members
    
    def get_members(self) -> List[str]:
        """Get all member SIDs"""
        return list(self.members)
    
    def to_dict(self):
        return {
            "room_id": self.room_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "member_count": self.get_member_count(),
            "is_private": self.is_private
        }

class RoomManager:
    """Manages all chat rooms"""
    
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        # Always have a default "general" room
        self.rooms["general"] = Room("General", "general")
    
    def create_room(self, name: str, room_id: str = None, is_private: bool = False) -> Room:
        """Create a new room"""
        room = Room(name, room_id)
        room.is_private = is_private
        self.rooms[room.room_id] = room
        return room
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID"""
        return self.rooms.get(room_id)
    
    def join_room(self, room_id: str, sid: str) -> bool:
        """Add user to room"""
        if room := self.get_room(room_id):
            return room.add_member(sid)
        return False
    
    def leave_room(self, room_id: str, sid: str) -> bool:
        """Remove user from room"""
        if room := self.get_room(room_id):
            return room.remove_member(sid)
        return False
    
    def get_user_rooms(self, sid: str) -> List[str]:
        """Get all rooms a user is in"""
        return [room_id for room_id, room in self.rooms.items() 
                if room.has_member(sid)]
    
    def get_room_members(self, room_id: str) -> List[str]:
        """Get all members in a room"""
        if room := self.get_room(room_id):
            return room.get_members()
        return []
    
    def get_all_rooms(self) -> List[dict]:
        """Get all rooms as list of dicts"""
        return [room.to_dict() for room in self.rooms.values()]
    
    def get_public_rooms(self) -> List[dict]:
        """Get all public rooms"""
        return [room.to_dict() for room in self.rooms.values() 
                if not room.is_private]
    
    def delete_room(self, room_id: str) -> bool:
        """Delete a room (prevents deletion of 'general')"""
        if room_id != "general" and room_id in self.rooms:
            del self.rooms[room_id]
            return True
        return False

# Global room manager instance
room_manager = RoomManager()
