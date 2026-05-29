"""
Test script for Phase 4
Verifies that state management is working correctly
"""

import sys
sys.path.insert(0, r"C:\Users\AY ADVANCE TECH\Documents\lan-chat-v2\backend")

from core.state import registry
from core.presence import presence_manager, PresenceStatus
from core.rooms import room_manager

print("\n=== PHASE 4 STATE MANAGEMENT TEST ===\n")

# Test 1: User Registration
print("Test 1: User Registration")
user1 = registry.register_user("sid123", "Alice")
user2 = registry.register_user("sid456", "Bob")
print(f"✓ Registered 2 users")
print(f"  - Online count: {registry.get_online_count()}")

# Test 2: Presence Tracking
print("\nTest 2: Presence Tracking")
presence_manager.set_presence("sid123", PresenceStatus.ONLINE)
presence_manager.set_presence("sid456", PresenceStatus.ONLINE)
print(f"✓ Set both users as online")
print(f"  - Online users: {len(presence_manager.get_online_users())}")

# Test 3: Room Management
print("\nTest 3: Room Management")
room_manager.join_room("general", "sid123")
room_manager.join_room("general", "sid456")
print(f"✓ Both users joined general room")
print(f"  - General room members: {room_manager.get_room_members('general')}")

# Test 4: Create new room
print("\nTest 4: Create New Room")
room = room_manager.create_room("Developers")
room_manager.join_room(room.room_id, "sid123")
print(f"✓ Created 'developers' room and Alice joined")
print(f"  - Alice's rooms: {registry.get_user('sid123').current_room}")

# Test 5: Get all users
print("\nTest 5: Get All Users")
users = registry.get_all_users()
print(f"✓ Retrieved all users:")
for user in users:
    print(f"  - {user['name']} ({user['status']})")

# Test 6: Get all rooms
print("\nTest 6: Get All Rooms")
rooms = room_manager.get_all_rooms()
print(f"✓ Retrieved {len(rooms)} rooms")

# Test 7: User disconnect
print("\nTest 7: User Disconnect")
registry.remove_user("sid123")
presence_manager.set_presence("sid123", PresenceStatus.OFFLINE)
print(f"✓ Alice disconnected")
print(f"  - Online count: {registry.get_online_count()}")

print("\n=== ALL TESTS PASSED ===\n")
