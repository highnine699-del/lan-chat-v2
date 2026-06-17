# REPLIT PROMPT: LAN Chat V2 - Complete Recreation Guide

Create a complete LAN Chat V2 application from scratch. This is a real-time chat application designed for local networks with advanced features including WebRTC voice/video calls, end-to-end encryption, room management, and admin tools.

## PROJECT OVERVIEW

**LAN Chat V2** is a modern, event-driven chat application built with FastAPI (backend) and vanilla JavaScript (frontend). It features a WhatsApp-inspired UI with a futuristic "NEXUS" dark theme, supporting real-time messaging, file sharing, voice/video calls, and encrypted communications.

### Key Features:
- Real-time messaging via Socket.IO
- WebRTC voice/video calls with ICE/TURN/STUN support
- End-to-end encryption (ECDH key exchange, AES-GCM)
- Room management (public/private rooms, password protection, approval system)
- File sharing with rate limiting
- Voice messages with recording
- Emoji reactions and emoji picker
- Admin tools (kick, freeze, shadow mute, server management)
- Spam protection and rate limiting
- PWA support with offline capabilities
- Responsive design (mobile-first)

## TECHNOLOGY STACK

### Backend:
- **Python 3.14+**
- **FastAPI 0.136.1** - Web framework
- **Uvicorn 0.47.0** - ASGI server
- **python-socketio 5.16.1** - Real-time communication
- **python-multipart 0.0.29** - File upload handling
- **python-engineio 4.13.1** - Engine.IO server
- **pyngrok 8.1.2** - Ngrok tunneling (optional)
- **pyyaml 6.0.3** - YAML parsing
- **jinja2 3.1.4** - Template engine
- **aiofiles 24.1.0** - Async file operations

### Frontend:
- **Vanilla JavaScript (ES6 modules)** - No frameworks
- **Socket.IO client** - Real-time communication
- **WebRTC API** - Voice/video calls
- **Web Crypto API** - End-to-end encryption
- **CSS3** - Styling with custom properties
- **HTML5** - Single-page application

## PROJECT STRUCTURE

```
lan-chat-v2/
├── backend/
│   ├── app.py                    # FastAPI app entry point
│   ├── socket_manager.py         # Socket.IO configuration
│   ├── config.py                 # Configuration constants
│   ├── state_log.py              # State transition logging
│   ├── core/
│   │   ├── __init__.py
│   │   └── state.py              # State management (1,286 lines)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── http.py               # HTTP routes
│   │   ├── sockets.py            # Socket handler registration
│   │   ├── socket_auth.py        # Authentication handlers
│   │   ├── socket_messages.py     # Message handlers
│   │   ├── socket_rooms.py       # Room handlers
│   │   ├── socket_admin.py       # Admin handlers
│   │   ├── socket_webrtc.py      # WebRTC handlers
│   │   └── socket_rate_limit.py  # Rate limiting
│   └── uploads/                  # File upload directory
├── frontend/
│   ├── templates/
│   │   └── index.html            # Single-page app (3,677 lines)
│   └── static/
│       ├── init.js               # Application entry point
│       ├── socket.io.min.js      # Socket.IO client
│       ├── emoji-picker.js       # Emoji picker module
│       ├── emoji-data.json       # Emoji database
│       ├── emoji-picker-database.js
│       ├── emoji-picker-picker.js
│       ├── manifest.json         # PWA manifest
│       ├── icon.svg              # App icons
│       ├── icon-192.png
│       ├── icon-512.png
│       ├── logo.svg
│       ├── wallpaper.svg         # Chat background
│       ├── style.css             # Additional styles
│       ├── core/                 # Core JavaScript modules
│       │   ├── config.js
│       │   ├── encryption.js
│       │   ├── eventBus.js
│       │   ├── socket.js
│       │   ├── index.js
│       │   └── state/
│       ├── features/             # Feature modules
│       ├── messages/             # Message handling
│       ├── rooms/                # Room management
│       ├── call/                 # WebRTC call logic
│       ├── ui/                   # UI components
│       └── utils/                # Utility functions
├── requirements.txt              # Python dependencies
└── README.md                    # Documentation
```

## BACKEND IMPLEMENTATION

### 1. Configuration (config.py)

Create comprehensive configuration with environment variables:

```python
import os
import secrets
import warnings

# Flask/Session
SECRET_KEY = os.environ.get('SECRET_KEY', '') or secrets.token_hex(32)

# Socket.IO
MAX_HTTP_BUFFER_SIZE = 50 * 1024 * 1024   # 50 MB
PING_TIMEOUT = 60
PING_INTERVAL = 25

# File uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Chat limits
MAX_USERNAME_LEN = 20
MAX_MESSAGE_LEN = 2000
MAX_GLOBAL_HISTORY = 500
MAX_PRIVATE_HISTORY = 200
MAX_SIGNAL_BYTES = 64 * 1024

# Spam protection
SPAM_MSG_LIMIT = 5
SPAM_WINDOW_S = 5
SPAM_COOLDOWN_S = 20
SPAM_REPEAT_LIMIT = 3

# Security
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*')
MAX_CONNECTIONS_PER_IP = int(os.environ.get('MAX_CONNECTIONS_PER_IP', '5'))
TRUSTED_PROXY = os.environ.get('TRUSTED_PROXY', 'false').lower() == 'true'

# Rooms
MAX_ROOM_NAME_LEN = 32
MAX_ROOMS = 50
ROOM_IDLE_GRACE_S = 300
ROOM_HISTORY_SIZE = 200

# Ephemeral messages
EPHEMERAL_TTLS = {
    '5min': 5 * 60,
    '1hour': 60 * 60,
    'session': None,
}

# Admin
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
PUBLIC_MODE = os.environ.get('PUBLIC_MODE', 'false').lower() == 'true'
SERVER_PASSWORD = os.environ.get('SERVER_PASSWORD', '') or None

# WebRTC/TURN
TURN_CREDENTIALS = os.environ.get('TURN_CREDENTIALS', '')
TURN_URL_UDP = os.environ.get('TURN_URL_UDP', 'turn:global.turn.twilio.com:3478?transport=udp')
TURN_URL_TCP = os.environ.get('TURN_URL_TCP', 'turn:global.turn.twilio.com:443?transport=tcp')

# User colors
USER_COLORS = ['#25D366', '#00a884', '#53bdeb', '#f0b429', '#e06c75', '#c678dd', '#56b6c2', '#e5c07b']
```

### 2. State Management (core/state.py)

Implement comprehensive state management with identity authority hierarchy:

```python
import os
import re
import time
import string
import threading
import secrets
from collections import deque

# Core identity state
users: dict = {}           # sid -> user record
sid_map: dict = {}         # "username#tag" -> sid
public_keys: dict = {}     # "username#tag" -> ECDH JWK

# Message history
message_history: deque = deque(maxlen=MAX_GLOBAL_HISTORY)
private_history: dict = {}  # "displayA|displayB" -> deque[msg]

# Rooms
rooms: dict = {}           # room_id -> room dict

# Session management
session_tokens: dict = {}  # uid -> token record
active_sessions: dict = {} # sid -> session metadata
uid_sessions: dict = {}    # uid -> sid

# Call management
active_calls: dict = {}    # call_id -> set[sid]
call_sessions: dict = {}   # call_id -> session_uuid
call_phase: dict = {}      # call_id -> phase constant
open_call: dict = {}       # sid -> call_id (offer lock)

# Moderation
shadow_muted: dict = {}   # sid -> {'until': float}
spam_tracker: dict = {}    # sid -> spam data
message_votes: dict = {}   # msg_id -> set[uid]

# Analytics
analytics: dict = {
    'messages_sent': 0,
    'files_uploaded': 0,
    'peak_users': 0,
    'rooms_created': 0,
    'errors': 0,
    'started_at': time.time(),
}
```

### 3. Socket.IO Setup (socket_manager.py)

Create Socket.IO server with V1 configuration:

```python
import socketio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from config import MAX_HTTP_BUFFER_SIZE, PING_TIMEOUT, PING_INTERVAL, ALLOWED_ORIGINS

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=ALLOWED_ORIGINS,
    max_http_buffer_size=MAX_HTTP_BUFFER_SIZE,
    ping_timeout=PING_TIMEOUT,
    ping_interval=PING_INTERVAL,
    engineio_logger=False,
)

def create_socket_app(fastapi_app):
    return socketio.ASGIApp(sio, fastapi_app)
```

### 4. HTTP Routes (routes/http.py)

Implement HTTP endpoints:

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse

http_router = APIRouter()

@http_router.get("/")
async def index():
    """Serve the single-page application."""
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
    index_file = os.path.join(frontend_path, "templates", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return JSONResponse(content={"error": "Frontend not found"}, status_code=404)

@http_router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Accept file upload and return public URL."""
    # Implement file upload logic with rate limiting
    pass

@http_router.get("/ice-config")
async def ice_config():
    """Return WebRTC ICE server configuration."""
    return JSONResponse(content={
        'iceServers': [
            {'urls': 'stun:stun.l.google.com:19302'},
            # Add TURN servers if configured
        ]
    })
```

### 5. Authentication Handlers (routes/socket_auth.py)

Implement user authentication and session management:

```python
@sio.on('connect')
async def handle_connect(sid, environ):
    """Handle new socket connection."""
    pass

@sio.on('join')
async def handle_join(sid, data):
    """Handle user join with authentication."""
    # Validate username, check rate limits, handle reconnection
    # Issue session tokens, manage ghost sessions
    pass

@sio.on('disconnect')
async def handle_disconnect(sid):
    """Handle user disconnect."""
    # Clean up sessions, leave rooms, teardown calls
    pass

@sio.on('user:presence')
async def handle_presence(sid, data):
    """Handle presence updates."""
    pass

@sio.on('reconnect_sync')
async def handle_reconnect_sync(sid, data):
    """Handle state reconciliation on reconnect."""
    pass
```

### 6. Message Handlers (routes/socket_messages.py)

Implement message handling:

```python
@sio.on('send_message')
async def handle_message(sid, data):
    """Handle text message sending."""
    # Spam protection, message validation, dispatch
    pass

@sio.on('send_file')
async def handle_file(sid, data):
    """Handle file message sending."""
    pass

@sio.on('message:edit')
async def handle_message_edit(sid, data):
    """Handle message editing."""
    pass

@sio.on('message:delete')
async def handle_message_delete(sid, data):
    """Handle message deletion."""
    pass

@sio.on('typing')
async def handle_typing(sid, data):
    """Handle typing indicators."""
    pass
```

### 7. Room Handlers (routes/socket_rooms.py)

Implement room management:

```python
@sio.on('room:create')
async def handle_room_create(sid, data):
    """Handle room creation."""
    pass

@sio.on('room:join')
async def handle_room_join(sid, data):
    """Handle room joining."""
    pass

@sio.on('room:leave')
async def handle_room_leave(sid, data):
    """Handle room leaving."""
    pass

@sio.on('room:call')
async def handle_room_call(sid, data):
    """Handle room calls."""
    pass
```

### 8. WebRTC Handlers (routes/socket_webrtc.py)

Implement WebRTC signaling:

```python
@sio.on('call_signal')
async def handle_call_signal(sid, data):
    """Handle WebRTC signaling."""
    # Implement FSM for call phases, session management
    pass

@sio.on('call:query_phase')
async def handle_call_query_phase(sid, data):
    """Handle call phase queries."""
    pass
```

### 9. Admin Handlers (routes/socket_admin.py)

Implement admin functions:

```python
@sio.on('admin:kick')
async def handle_kick(sid, data):
    """Handle user kick."""
    pass

@sio.on('admin:freeze')
async def handle_freeze(sid, data):
    """Handle room freeze."""
    pass

@sio.on('admin:server_kick')
async def handle_server_kick(sid, data):
    """Handle server-wide kick."""
    pass
```

### 10. Main Application (app.py)

Create FastAPI application:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from socket_manager import sio, create_socket_app
from routes.http import http_router
from routes.sockets import register_socket_handlers

app = FastAPI()
register_socket_handlers(sio)
app.include_router(http_router)

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "static")
if os.path.isdir(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Create ASGI app
asgi_app = create_socket_app(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:asgi_app", host="0.0.0.0", port=8000, reload=False)
```

## FRONTEND IMPLEMENTATION

### 1. HTML Structure (templates/index.html)

Create single-page application with:

- Login screen with matrix rain animation
- Main chat interface with sidebar
- Message area with WhatsApp-style bubbles
- Input area with file attachment, emoji, voice recording
- Call overlay for voice/video calls
- Settings panel
- Room creation/join modals

Key CSS variables for NEXUS theme:
```css
:root {
  --bg-primary: #050508;
  --bg-secondary: #0d0d12;
  --accent: #00f5c4;
  --accent-rgb: 0, 245, 196;
  --text-primary: #e8edf2;
  --text-secondary: #6b7a8d;
}
```

### 2. JavaScript Architecture

Implement modular ES6 structure:

**Core Modules (static/core/):**
- `config.js` - Configuration constants
- `socket.js` - Socket.IO client wrapper
- `encryption.js` - Web Crypto API wrapper for ECDH/AES-GCM
- `eventBus.js` - Event bus for inter-module communication
- `state/` - State management (chat, crypto, ui, media)

**Feature Modules (static/features/):**
- `typing.js` - Typing indicators
- `presence.js` - User presence
- `voiceMessages.js` - Voice recording
- `files.js` - File upload handling
- `reactions.js` - Emoji reactions
- `admin.js` - Admin functions

**Message Modules (static/messages/):**
- `handler.js` - Message event handling
- `sender.js` - Message sending
- `renderer.js` - Message DOM rendering
- `decryption.js` - Message decryption

**Room Modules (static/rooms/):**
- `manager.js` - Room management
- `ui.js` - Room UI components
- `component.js` - Room components

**Call Modules (static/call/):**
- `controlPlane.js` - Call control logic
- `healthEngine.js` - Call health monitoring
- `lifecycle.js` - Call lifecycle management
- `callUI.js` - Call UI
- `moodEngine.js` - Connection mood indicators
- `signalEmit.js` - Signal emission
- `iceManager.js` - ICE candidate management
- `mediaValidator.js` - Media validation
- `statsEngine.js` - Call statistics

### 3. Entry Point (static/init.js)

Initialize all modules:

```javascript
import { socketClient } from './core/socket.js';
import { encryption } from './core/encryption.js';
import { eventBus } from './core/eventBus.js';
import { chatState, cryptoState, uiState, mediaState } from './core/state/index.js';

// Import feature modules
import { messageHandler, messageSender, messageRenderer } from './messages/index.js';
import { roomManager, roomUI } from './rooms/index.js';
import { controlPlane, lifecycle, callUI } from './call/index.js';
import { typing, presence, voiceMessages, files } from './features/index.js';

async function init() {
  // Generate encryption keys
  await encryption.generateKeys();
  
  // Initialize socket
  const socket = socketClient.init();
  
  // Initialize modules
  messageHandler.init();
  roomManager.init();
  typing.init();
  presence.init();
  
  // Attach UI listeners
  attachUIListeners();
}

window.LANCHAT = {
  socket: socketClient,
  encryption,
  eventBus,
  init,
};
```

### 4. Socket Client (static/core/socket.js)

Implement Socket.IO client:

```javascript
import { io } from '/static/socket.io.min.js';
import { config } from './config.js';

export const socketClient = {
  socket: null,
  
  init() {
    this.socket = io({
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });
    
    this.setupEventHandlers();
    return this.socket;
  },
  
  setupEventHandlers() {
    this.socket.on('connect', () => {
      console.log('[Socket] Connected');
    });
    
    this.socket.on('joined', (data) => {
      console.log('[Socket] Joined as:', data.display);
      eventBus.emit('socket:joined', data);
    });
    
    this.socket.on('new_message', (msg) => {
      eventBus.emit('message:received', msg);
    });
    
    // ... more event handlers
  }
};
```

### 5. Encryption (static/core/encryption.js)

Implement Web Crypto API:

```javascript
export const encryption = {
  myKeyPair: null,
  myPublicKeyJwk: null,
  
  async generateKeys() {
    this.myKeyPair = await window.crypto.subtle.generateKey(
      {
        name: 'ECDH',
        namedCurve: 'P-256',
      },
      true,
      ['deriveKey', 'deriveBits']
    );
    
    this.myPublicKeyJwk = await window.crypto.subtle.exportKey(
      'jwk',
      this.myKeyPair.publicKey
    );
  },
  
  async deriveSharedKey(publicKeyJwk) {
    const publicKey = await window.crypto.subtle.importKey(
      'jwk',
      publicKeyJwk,
      { name: 'ECDH', namedCurve: 'P-256' },
      false,
      []
    );
    
    return await window.crypto.subtle.deriveKey(
      { name: 'ECDH', public: publicKey },
      this.myKeyPair.privateKey,
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );
  },
  
  async encrypt(text, key) {
    const encoded = new TextEncoder().encode(text);
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    
    const encrypted = await window.crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      encoded
    );
    
    return {
      iv: Array.from(iv),
      data: Array.from(new Uint8Array(encrypted))
    };
  },
  
  async decrypt(encryptedData, key) {
    const iv = new Uint8Array(encryptedData.iv);
    const data = new Uint8Array(encryptedData.data);
    
    const decrypted = await window.crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      data
    );
    
    return new TextDecoder().decode(decrypted);
  }
};
```

## KEY FUNCTIONALITY IMPLEMENTATION

### 1. Real-time Messaging

**Backend:**
- Message validation and spam protection
- Message dispatching to global chat, rooms, or private messages
- Message editing and deletion with authorization checks
- Message deduplication
- Read receipts and typing indicators

**Frontend:**
- Message rendering with WhatsApp-style bubbles
- Message grouping and animations
- Reply functionality
- Emoji reactions
- Message status indicators (sent, delivered, read)

### 2. WebRTC Voice/Video Calls

**Backend:**
- WebRTC signaling with FSM (offer/answer/ice/end phases)
- Session management with UUID tracking
- Call tombstones for reconnection support
- ICE/TURN server configuration
- Rate limiting for signals

**Frontend:**
- WebRTC peer connection management
- Media stream handling (audio/video)
- ICE candidate trickle
- Call UI with mood indicators
- Health monitoring and stats

### 3. Room Management

**Backend:**
- Room creation with visibility settings (public/private)
- Password protection for private rooms
- Approval system for private rooms
- Room member management
- Room freezing by admins
- Ephemeral rooms with TTL
- Room message history with sequence numbers

**Frontend:**
- Room list display
- Room creation modal
- Room join interface
- Room member list
- Room settings panel

### 4. End-to-End Encryption

**Backend:**
- Public key distribution on join
- Room key relay for encrypted rooms
- No message content inspection

**Frontend:**
- ECDH key pair generation
- Shared key derivation
- AES-GCM encryption/decryption
- Key rotation support

### 5. File Sharing

**Backend:**
- Multipart file upload handling
- File size validation
- MIME type checking
- Rate limiting (burst and daily quotas)
- Secure file serving with Content-Disposition
- SVG blocking for XSS prevention

**Frontend:**
- File selection and upload
- Upload progress indication
- File message rendering
- File download handling

### 6. Admin Tools

**Backend:**
- Room admin functions (kick, freeze, mod management)
- Server admin functions (server kick, shadow mute)
- Authorization checks
- Action logging

**Frontend:**
- Admin UI panels
- User management interface
- Room management interface
- Moderation actions

## RUNNING THE APPLICATION

### Development Setup:

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the server:**
```bash
cd backend
uvicorn app:asgi_app --host 0.0.0.0 --port 8000 --reload
```

3. **Access the application:**
```
http://localhost:8000
```

### Environment Variables:

```bash
# Security
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password
SERVER_PASSWORD=your-server-password

# Public mode (for ngrok/internet deployment)
PUBLIC_MODE=false
ALLOWED_ORIGINS=*

# WebRTC TURN (optional but recommended for internet calls)
TURN_CREDENTIALS=username:credential
TURN_URL_UDP=turn:global.turn.twilio.com:3478?transport=udp
TURN_URL_TCP=turn:global.turn.twilio.com:443?transport=tcp

# Debug mode
DEBUG=false
```

### Production Deployment:

1. **Set environment variables:**
```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export ADMIN_PASSWORD=your-secure-admin-password
export PUBLIC_MODE=true  # if deploying via ngrok
export ALLOWED_ORIGINS=https://your-domain.com
```

2. **Run with production server:**
```bash
uvicorn app:asgi_app --host 0.0.0.0 --port 8000 --workers 4
```

3. **Optional: Use ngrok for public access:**
```bash
ngrok http 8000
```

## SECURITY CONSIDERATIONS

1. **Input Validation:** All user inputs must be validated and sanitized
2. **Rate Limiting:** Implement comprehensive rate limiting for all endpoints
3. **File Upload Security:** Validate file types, limit sizes, block SVG files
4. **CORS Protection:** Configure ALLOWED_ORIGINS appropriately
5. **Session Management:** Use secure session tokens with IP binding
6. **Encryption:** End-to-end encryption for sensitive communications
7. **Admin Authorization:** Strict authorization checks for admin functions
8. **XSS Prevention:** Content Security Policy, input sanitization
9. **CSRF Protection:** Implement CSRF tokens for state-changing operations

## TESTING CONSIDERATIONS

1. **Unit Tests:** Test individual functions and modules
2. **Integration Tests:** Test Socket.IO event handlers
3. **End-to-End Tests:** Test complete user flows
4. **Load Testing:** Test with multiple concurrent users
5. **Security Testing:** Test for XSS, CSRF, rate limiting bypass

## PERFORMANCE OPTIMIZATION

1. **Message History:** Limit history size, use deque for efficient operations
2. **State Management:** Use in-memory state for fast access
3. **File Serving:** Use efficient file serving with proper headers
4. **WebSocket Compression:** Enable Socket.IO compression
5. **Static Files:** Use CDN for static assets in production

## DEPENDENCIES

Create `requirements.txt`:
```
fastapi==0.136.1
uvicorn==0.47.0
python-socketio==5.16.1
python-multipart==0.0.29
python-engineio==4.13.1
pyngrok==8.1.2
pyyaml==6.0.3
jinja2==3.1.4
aiofiles==24.1.0
```

## ADDITIONAL NOTES

1. **PWA Support:** The application includes PWA manifest and service worker for offline capabilities
2. **Mobile Responsive:** The UI is designed mobile-first with responsive breakpoints
3. **Accessibility:** Implement proper ARIA labels and keyboard navigation
4. **Browser Compatibility:** Target modern browsers (Chrome, Firefox, Safari, Edge)
5. **Error Handling:** Comprehensive error handling with user-friendly messages
6. **Logging:** Implement structured logging for debugging and monitoring
7. **Analytics:** Track user actions and system performance

This is a comprehensive guide to recreate the LAN Chat V2 application. The implementation should follow the modular architecture described, with clear separation of concerns between backend and frontend, and proper security measures throughout.
