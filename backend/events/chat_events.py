"""
events/chat_events.py — Chat event handlers (connect, disconnect, message)

Now using:
- Unified message protocol (core/messages.py)
- Event-driven architecture (core/events.py)
- State management & persistence
"""

from socket_manager import sio
from core.state import registry
from core.presence import presence_manager, PresenceStatus
from core.rooms import room_manager
from core.events import event_bus, EventType
from core.messages import Message, MessageType, MessageRouter, MessageBuilder
import db
from datetime import datetime

@sio.event
async def connect(sid, environ):
    """Handle user connection"""
    print(f"[CONNECT] Client connected: {sid}")
    
    # Create temporary user in DB
    user_id = db.get_or_create_temp_user(sid)
    db.record_session(sid, user_id, ip_address=environ.get('REMOTE_ADDR'))
    
    # Issue a session token (24 hours) so the client can reconnect to same uid
    try:
        token = db.issue_session_token(user_id, ttl_seconds=24*3600, ip_address=environ.get('REMOTE_ADDR'))
        # Send token to client for storage (client should emit it on reconnect)
        await sio.emit("session_token", {"token": token, "ttl": 24*3600}, to=sid)
    except Exception:
        # Fail silently — token issuance shouldn't block connect
        pass

    # Register user in session registry
    user = registry.register_user(sid)
    
    # Mark as online
    presence_manager.set_presence(sid, PresenceStatus.ONLINE)
    
    # Auto-join general room
    db.create_room_db("general", "General", is_private=False)
    room_manager.join_room("general", sid)
    db.add_room_member("general", user_id)
    
    # Emit user.connected event
    event_bus.emit(EventType.USER_CONNECTED, {
        "sid": sid,
        "user_id": user_id,
        "name": user.name
    })
    
    # Get recent message history for general room
    messages = db.get_recent_messages("general", limit=20)
    
    # Notify all clients about the new user
    await sio.emit("user_joined", {
        "sid": sid,
        "name": user.name,
        "online_count": registry.get_online_count()
    })
    
    # Send message history to the connecting client
    await sio.emit("message_history", {
        "messages": [
            {
                "sender": m["sender_name"],
                "text": m["content"],
                "timestamp": m["created_at"]
            }
            for m in messages
        ]
    }, to=sid)
    
    # Send current user list to the connecting client
    await sio.emit("user_list", {
        "users": registry.get_all_users()
    }, to=sid)
    
    # Send room list to the connecting client
    await sio.emit("room_list", {
        "rooms": room_manager.get_all_rooms()
    }, to=sid)

@sio.event
async def disconnect(sid):
    """Handle user disconnection"""
    print(f"[DISCONNECT] Client disconnected: {sid}")
    
    # Update session in DB
    db.update_session_activity(sid)
    
    # Get user data before removing
    user = registry.get_user(sid)
    user_id = sid  # User ID = SID for temp users
    
    # Remove from all rooms
    for room_id in room_manager.get_user_rooms(sid):
        room_manager.leave_room(room_id, sid)
    
    # Remove from session registry
    registry.remove_user(sid)
    
    # Mark as offline
    presence_manager.set_presence(sid, PresenceStatus.OFFLINE)
    presence_manager.remove_presence(sid)
    
    # Emit user.disconnected event
    if user:
        event_bus.emit(EventType.USER_DISCONNECTED, {
            "sid": sid,
            "user_id": user_id,
            "name": user.name
        })
        
        # Notify all clients about the user leaving
        await sio.emit("user_left", {
            "sid": sid,
            "name": user.name,
            "online_count": registry.get_online_count()
        })

@sio.event
async def message(sid, data):
    """Handle incoming message"""
    user = registry.get_user(sid)
    if not user:
        print(f"[MESSAGE] Unknown user: {sid}")
        return
    
    print(f"[MESSAGE] {user.name}: {data}")
    
    # Get user's current room (default to "general")
    room_id = user.current_room or "general"
    
    # Build unified message
    msg = MessageBuilder(sid).set_content(data).set_room(room_id).build()
    msg.sender_name = user.name
    
    # Determine if should persist
    if MessageRouter.should_persist(msg):
        msg_id = db.save_message(sid, room_id, data, MessageType.TEXT.value)
        msg.id = msg_id
    
    db.update_session_activity(sid)
    
    # Emit message.sent event
    event_bus.emit(EventType.MESSAGE_SENT, {
        "sender_id": sid,
        "sender_name": user.name,
        "content": data,
        "room_id": room_id
    })
    
    # Broadcast to room members (using unified message)
    await sio.emit("message", msg.to_dict())

@sio.event
async def join_room(sid, room_id):
    """Handle user joining a room"""
    user = registry.get_user(sid)
    if not user:
        return
    
    # Leave old room if in one
    if user.current_room:
        room_manager.leave_room(user.current_room, sid)
    
    # Create room in DB if doesn't exist
    db.create_room_db(room_id, room_id.replace("_", " ").title(), sid, False)
    
    # Join new room
    if room_manager.join_room(room_id, sid):
        user.current_room = room_id
        db.add_room_member(room_id, sid)
        print(f"[ROOM] {user.name} joined {room_id}")
        
        # Emit user.joined_room event
        event_bus.emit(EventType.USER_JOINED_ROOM, {
            "sid": sid,
            "name": user.name,
            "room_id": room_id
        })
        
        # Get recent message history
        messages = db.get_recent_messages(room_id, limit=20)
        
        # Send message history to the user
        await sio.emit("message_history", {
            "messages": [
                {
                    "sender": m["sender_name"],
                    "text": m["content"],
                    "timestamp": m["created_at"]
                }
                for m in messages
            ]
        }, to=sid)
        
        # Notify room members
        await sio.emit("user_joined_room", {
            "user_name": user.name,
            "room_id": room_id
        }, room=room_id)

@sio.event
async def leave_room(sid, room_id):
    """Handle user leaving a room"""
    user = registry.get_user(sid)
    if not user:
        return
    
    if room_manager.leave_room(room_id, sid):
        print(f"[ROOM] {user.name} left {room_id}")
        user.current_room = None
        
        # Emit user.left_room event
        event_bus.emit(EventType.USER_LEFT_ROOM, {
            "sid": sid,
            "name": user.name,
            "room_id": room_id
        })
        
        # Notify room members
        await sio.emit("user_left_room", {
            "user_name": user.name,
            "room_id": room_id
        }, room=room_id)

@sio.event
async def typing(sid, is_typing):
    """Handle typing indicator"""
    user = registry.get_user(sid)
    if not user:
        return
    
    room_id = user.current_room or "general"
    db.update_session_activity(sid)
    
    # Build typing message using unified protocol
    msg = MessageBuilder(sid).set_type(MessageType.TYPING).set_room(room_id).build()
    msg.sender_name = user.name
    msg.add_metadata("is_typing", is_typing)
    
    if is_typing:
        event_bus.emit(EventType.USER_TYPING, {
            "sid": sid,
            "name": user.name,
            "room_id": room_id
        })
    else:
        event_bus.emit(EventType.USER_STOPPED_TYPING, {
            "sid": sid,
            "name": user.name,
            "room_id": room_id
        })
    
    await sio.emit("user_typing", {
        "user_name": user.name,
        "is_typing": is_typing,
        "room_id": room_id
    }, skip_sid=sid, room=room_id)

@sio.event
async def get_online_users(sid):
    """Send list of online users to client"""
    await sio.emit("online_users", {
        "users": registry.get_all_users(),
        "count": registry.get_online_count()
    }, to=sid)

@sio.event
async def get_event_stats(sid):
    """Send event statistics (for admin/debugging)"""
    stats = event_bus.get_event_stats()
    await sio.emit("event_stats", stats, to=sid)

@sio.event
async def get_event_history(sid, event_type=None, limit=50):
    """Get event history (for admin/debugging)"""
    from core.events import EventType as ET
    
    # Convert string to EventType if provided
    if event_type:
        try:
            event_type = ET[event_type]
        except KeyError:
            event_type = None
    
    history = event_bus.get_event_history(event_type, limit)
    await sio.emit("event_history", history, to=sid)
