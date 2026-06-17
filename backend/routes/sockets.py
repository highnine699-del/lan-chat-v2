# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

import logging
logging.basicConfig(filename='startup_debug.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logging.info("SOCKETS_STEP 1: Starting routes/sockets.py")
"""
routes/sockets.py — Socket.IO handler registration.

This file serves as the entry point for registering all Socket.IO event handlers.
The actual handler implementations have been split into concern-specific modules:
- socket_rate_limit.py: Rate limiting and security helpers
- socket_auth.py: Authentication and user management
- socket_messages.py: Message handling
- socket_rooms.py: Room management
- socket_admin.py: Admin functions
- socket_webrtc.py: WebRTC signaling
"""

log = logging.getLogger('lan-chat')

from .socket_rate_limit import (
    reset_rate_limiters, _prune_module_state,
    _join_rate, _signal_tracker, _uid_last_kick,
    _JOIN_RATE_LIMIT, _JOIN_RATE_WINDOW,
    _SIGNAL_RATE_LIMIT, _SIGNAL_RATE_WINDOW,
    _UID_KICK_COOLDOWN,
)
from .socket_auth import register_auth_handlers
from .socket_messages import register_message_handlers
from .socket_rooms import register_room_handlers
from .socket_admin import register_admin_handlers
from .socket_webrtc import register_webrtc_handlers

# Re-export for test compatibility
from config import UPLOAD_FOLDER


def register_socket_handlers(sio):
    """
    Bind all Socket.IO event handlers to *sio*.
    
    This function registers handlers from all concern-specific modules:
    - Authentication and user management
    - Message handling
    - Room management
    - Admin functions
    - WebRTC signaling
    """
    register_auth_handlers(sio)
    register_message_handlers(sio)
    register_room_handlers(sio)
    register_admin_handlers(sio)
    register_webrtc_handlers(sio)
