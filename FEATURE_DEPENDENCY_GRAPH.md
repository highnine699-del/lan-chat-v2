# LAN CHAT FEATURE DEPENDENCY GRAPH

**Generated:** May 30, 2026  
**V1 Location:** `c:\Users\AY ADVANCE TECH\Documents\local-whatsapp\lan-chat-final`  
**V2 Location:** `c:\Users\AY ADVANCE TECH\Documents\lan-chat-v2`

---

# EXECUTIVE SUMMARY

This document maps the dependency relationships between all V1 features based on actual code examination. Understanding these dependencies is critical for planning the migration order - features must be migrated after their dependencies are in place.

**Key Finding:** V1 has a layered architecture with clear dependency chains. The migration must follow these chains to avoid breaking functionality.

---

# DEPENDENCY LAYERS

## Layer 0: Foundation (No Dependencies)

These features have no dependencies and must be migrated first:

### Config System
- **File:** `config.py`
- **Purpose:** All configuration constants and environment variable bindings
- **Dependencies:** None
- **Required by:** Everything
- **V2 Status:** Missing - V2 has no config system
- **Migration Priority:** Critical

### Event Schema Contract
- **File:** `events.py`
- **Purpose:** Central event registry and validation
- **Dependencies:** None
- **Required by:** All Socket.IO handlers
- **V2 Status:** Missing - V2 has no event schema
- **Migration Priority:** High

### Database Schema
- **File:** `db.py` (V2), RAM-only in V1
- **Purpose:** Data persistence layer
- **Dependencies:** None
- **Required by:** All stateful features
- **V2 Status:** Partial - V2 has SQLite but different schema
- **Migration Priority:** Critical

### State Management Architecture
- **File:** `state.py`
- **Purpose:** Identity authority hierarchy, session registry, user tracking
- **Dependencies:** Config
- **Required by:** All user-facing features
- **V2 Status:** Partial - V2 has basic User class but missing identity hierarchy
- **Migration Priority:** Critical

---

## Layer 1: Core Infrastructure (Depends on Layer 0)

These features depend only on foundation layer:

### HTTP Routes
- **File:** `routes/http.py`
- **Purpose:** File upload/download, ICE config endpoint, static file serving
- **Dependencies:** Config, State
- **Required by:** File sharing, Calls
- **V2 Status:** Partial - V2 has basic static file serving only
- **Migration Priority:** High

### Socket.IO Base
- **File:** `routes/__init__.py`, `server.py`
- **Purpose:** Connection lifecycle, base socket setup
- **Dependencies:** Config, State, Event Schema
- **Required by:** All socket handlers
- **V2 Status:** Partial - V2 has Socket.IO but different setup
- **Migration Priority:** Critical

### Rate Limiting Base
- **File:** `routes/socket_rate_limit.py`
- **Purpose:** IP-based rate limiting, join rate limiting
- **Dependencies:** Config, State
- **Required by:** Authentication, Calls
- **V2 Status:** Missing
- **Migration Priority:** High

---

## Layer 2: Authentication & Presence (Depends on Layer 1)

These features depend on core infrastructure:

### Authentication System
- **File:** `routes/socket_auth.py`
- **Purpose:** Username registration with tag system, session tokens, server password, admin password, UID generation, join rate limiting, connection limits per IP
- **Dependencies:** Config, State, Event Schema, Rate Limiting
- **Required by:** All user features, Rooms, DMs, Calls
- **V2 Status:** Missing - V2 has no authentication
- **Migration Priority:** Critical

### Presence System
- **File:** `routes/socket_auth.py`, `state.py`
- **Purpose:** User presence tracking, last seen tracking, persona switching, user color assignment, reputation system
- **Dependencies:** Config, State, Authentication
- **Required by:** UI presence indicators, User lists
- **V2 Status:** Partial - V2 has basic presence but missing colors, reputation
- **Migration Priority:** High

---

## Layer 3: Messaging Core (Depends on Layer 2)

These features depend on authentication:

### Global Chat
- **File:** `routes/socket_messages.py`
- **Purpose:** Message broadcasting, message history (global)
- **Dependencies:** Config, State, Authentication, Event Schema
- **Required by:** All messaging features
- **V2 Status:** Partial - V2 has basic global chat
- **Migration Priority:** High

### Message Editing/Deletion
- **File:** `routes/socket_messages.py`
- **Purpose:** Message editing, message deletion
- **Dependencies:** Global Chat, State
- **Required by:** Message management
- **V2 Status:** Missing
- **Migration Priority:** Medium

### Reply System
- **File:** `routes/socket_messages.py`
- **Purpose:** Reply-to messages
- **Dependencies:** Global Chat, State
- **Required by:** Message context
- **V2 Status:** Missing
- **Migration Priority:** Medium

### Message Status Tracking
- **File:** `routes/socket_messages.py`
- **Purpose:** Sending/delivered/seen status, read receipts
- **Dependencies:** Global Chat, State
- **Required by:** Message delivery confirmation
- **V2 Status:** Missing
- **Migration Priority:** Medium

### Typing Indicators
- **File:** `routes/socket_messages.py`
- **Purpose:** Typing events
- **Dependencies:** Authentication, State
- **Required by:** UI typing indicators
- **V2 Status:** Partial - V2 has basic typing
- **Migration Priority:** Low

---

## Layer 4: Advanced Messaging (Depends on Layer 3)

These features depend on messaging core:

### Spam Protection
- **File:** `state.py`, `routes/socket_messages.py`
- **Purpose:** Smart spam detection, shadow muting, cooldown notifications
- **Dependencies:** Message History, Rate Limiting, State
- **Required by:** Public mode safety
- **V2 Status:** Missing
- **Migration Priority:** High

### Vote-to-Hide
- **File:** `routes/socket_messages.py`
- **Purpose:** Community moderation
- **Dependencies:** Message History, State
- **Required by:** Content moderation
- **V2 Status:** Missing
- **Migration Priority:** Medium

### Message Length Limits
- **File:** `config.py`, `routes/socket_messages.py`
- **Purpose:** Message size validation
- **Dependencies:** Config, Message History
- **Required by:** Resource protection
- **V2 Status:** Missing
- **Migration Priority:** Low

---

## Layer 5: Direct Messages (Depends on Layer 2 + Layer 3)

DMs depend on authentication and messaging:

### DM System
- **File:** `routes/socket_messages.py`, `state.py`
- **Purpose:** Private DMs (1-to-1), private message history
- **Dependencies:** Authentication, Message History, State
- **Required by:** Private communication
- **V2 Status:** Missing
- **Migration Priority:** High

### E2E Encryption for DMs
- **File:** `static/core/encryption.js`
- **Purpose:** ECDH key generation, AES-GCM encryption, shared secret derivation
- **Dependencies:** Web Crypto API, DM System
- **Required by:** Secure DMs
- **V2 Status:** Missing
- **Migration Priority:** Critical

### Public Key Exchange
- **File:** `state.py`, `routes/socket_auth.py`
- **Purpose:** ECDH public key distribution
- **Dependencies:** E2E Encryption, Authentication
- **Required by:** E2E DMs
- **V2 Status:** Missing
- **Migration Priority:** Critical

---

## Layer 6: Rooms (Depends on Layer 2 + Layer 3)

Rooms depend on authentication and messaging:

### Room System
- **File:** `routes/socket_rooms.py`, `state.py`
- **Purpose:** Room creation, public/private rooms, room password protection, room list, room member list, room history, room join/leave
- **Dependencies:** Authentication, Message History, State
- **Required by:** Group communication
- **V2 Status:** Partial - V2 has basic room creation/join
- **Migration Priority:** High

### Room Admin System
- **File:** `routes/socket_rooms.py`, `routes/socket_admin.py`
- **Purpose:** Room creator and moderators, room kick, room freeze/unfreeze
- **Dependencies:** Room System, State
- **Required by:** Room moderation
- **V2 Status:** Missing
- **Migration Priority:** High

### Ephemeral Rooms
- **File:** `state.py`, `routes/socket_rooms.py`
- **Purpose:** TTL-based auto-deletion
- **Dependencies:** Room System, Config
- **Required by:** Temporary rooms
- **V2 Status:** Missing
- **Migration Priority:** Medium

### E2E Encryption for Rooms
- **File:** `static/core/encryption.js`
- **Purpose:** Room message encryption
- **Dependencies:** Web Crypto API, Room System
- **Required by:** Secure rooms
- **V2 Status:** Missing
- **Migration Priority:** Critical

---

## Layer 7: WebRTC Calls (Depends on Layer 2 + Layer 6)

Calls depend on authentication and rooms:

### WebRTC Signaling
- **File:** `routes/socket_webrtc.py`
- **Purpose:** Offer/answer/ICE candidate exchange
- **Dependencies:** Authentication, State, Rate Limiting
- **Required by:** All call features
- **V2 Status:** Missing
- **Migration Priority:** Critical

### Call Session Management
- **File:** `state.py`, `routes/socket_webrtc.py`
- **Purpose:** Call session creation, tracking, teardown
- **Dependencies:** WebRTC Signaling, State
- **Required by:** Call state
- **V2 Status:** Missing
- **Migration Priority:** Critical

### Call Phase Management
- **File:** `state.py`, `routes/socket_webrtc.py`
- **Purpose:** Offer/answer/connected phases
- **Dependencies:** Call Session Management
- **Required by:** Call flow
- **V2 Status:** Missing
- **Migration Priority:** Critical

### Call Tombstone (Reconnect)
- **File:** `state.py`, `routes/socket_webrtc.py`
- **Purpose:** Call state persistence for reconnection
- **Dependencies:** Call Session Management
- **Required by:** Call recovery
- **V2 Status:** Missing
- **Migration Priority:** High

### Offer Lock
- **File:** `state.py`, `routes/socket_webrtc.py`
- **Purpose:** Prevent double calls
- **Dependencies:** Call Session Management
- **Required by:** Call safety
- **V2 Status:** Missing
- **Migration Priority:** Medium

### ICE Config
- **File:** `routes/http.py`, `config.py`
- **Purpose:** TURN/STUN server configuration
- **Dependencies:** Config, HTTP Routes
- **Required by:** NAT traversal
- **V2 Status:** Missing
- **Migration Priority:** High

---

## Layer 8: Admin Tools (Depends on Layer 6)

Admin tools depend on rooms:

### Admin Kick
- **File:** `routes/socket_admin.py`
- **Purpose:** Kick users from rooms
- **Dependencies:** Room System, Authentication
- **Required by:** Room moderation
- **V2 Status:** Missing
- **Migration Priority:** High

### Admin Freeze
- **File:** `routes/socket_admin.py`
- **Purpose:** Freeze rooms to prevent messages
- **Dependencies:** Room System, Authentication
- **Required by:** Room control
- **V2 Status:** Missing
- **Migration Priority:** High

### Shadow Mute
- **File:** `routes/socket_admin.py`, `state.py`
- **Purpose:** Silently mute spammers
- **Dependencies:** State, Authentication
- **Required by:** Spam control
- **V2 Status:** Missing
- **Migration Priority:** High

---

## Layer 9: File Sharing (Depends on Layer 1)

File sharing depends on HTTP routes:

### File Upload
- **File:** `routes/http.py`
- **Purpose:** Accept multipart file uploads
- **Dependencies:** HTTP Routes, Config, State
- **Required by:** File sharing
- **V2 Status:** Missing
- **Migration Priority:** Medium

### File Download
- **File:** `routes/http.py`
- **Purpose:** Serve uploaded files
- **Dependencies:** HTTP Routes, Config
- **Required by:** File sharing
- **V2 Status:** Missing
- **Migration Priority:** Medium

### File Validation
- **File:** `routes/http.py`
- **Purpose:** Validate file types and sizes
- **Dependencies:** Config, File Upload
- **Required by:** Security
- **V2 Status:** Missing
- **Migration Priority:** High

---

## Layer 10: Launcher (Depends on Layer 0)

Launcher depends only on config:

### NEXUS Launcher
- **File:** `launcher.py`
- **Purpose:** GUI launcher with dashboard, ngrok integration, start/stop controls
- **Dependencies:** Config
- **Required by:** Desktop application
- **V2 Status:** Missing
- **Migration Priority:** High

### Ngrok Manager
- **File:** `ngrok_manager.py`
- **Purpose:** Manage ngrok tunnels
- **Dependencies:** Config
- **Required by:** Public access
- **V2 Status:** Missing
- **Migration Priority:** High

---

## Layer 11: Frontend (Depends on Layer 0 + Layer 2)

Frontend depends on config and authentication:

### WhatsApp-style UI
- **File:** `templates/index.html`, `static/style.css`
- **Purpose:** Main UI layout with sidebar, chat area, input bar
- **Dependencies:** Config, Authentication
- **Required by:** User experience
- **V2 Status:** Missing - V2 has basic HTML only
- **Migration Priority:** Critical

### Modular Architecture
- **File:** `static/init.js`, `static/core/`, `static/features/`, `static/ui/`
- **Purpose:** Organized module system
- **Dependencies:** Config
- **Required by:** Maintainability
- **V2 Status:** Missing
- **Migration Priority:** High

### Login Page
- **File:** `static/ui/pages/LoginPage.js`
- **Purpose:** Login interface with username/tag input
- **Dependencies:** Authentication
- **Required by:** User onboarding
- **V2 Status:** Missing
- **Migration Priority:** High

### Chat Page
- **File:** `static/ui/pages/ChatPage.js`
- **Purpose:** Main chat interface
- **Dependencies:** Global Chat, Presence
- **Required by:** Messaging
- **V2 Status:** Missing
- **Migration Priority:** Critical

### Room Page
- **File:** `static/ui/pages/RoomPage.js`
- **Purpose:** Room-specific interface
- **Dependencies:** Room System
- **Required by:** Room management
- **V2 Status:** Missing
- **Migration Priority:** High

### Call UI
- **File:** `static/ui/pages/CallUI.js`
- **Purpose:** Voice/video call interface
- **Dependencies:** WebRTC Calls
- **Required by:** Calling
- **V2 Status:** Missing
- **Migration Priority:** High

### Admin Page
- **File:** `static/ui/pages/AdminPage.js`
- **Purpose:** Admin dashboard
- **Dependencies:** Admin Tools
- **Required by:** Administration
- **V2 Status:** Missing
- **Migration Priority:** High

### UI Components
- **Files:** `static/ui/components/`
- **Purpose:** Reusable components (MessageItem, InputBar, Modal, UserItem)
- **Dependencies:** Config
- **Required by:** UI consistency
- **V2 Status:** Missing
- **Migration Priority:** Medium

---

## Layer 12: Advanced Features (Depends on Multiple Layers)

### Voice Messages
- **File:** `static/features/voiceMessages/voiceMessages.js`
- **Purpose:** Voice recording, playback, waveforms
- **Dependencies:** MediaRecorder API, Audio API, Canvas API
- **Required by:** Voice communication
- **V2 Status:** Missing
- **Migration Priority:** Medium

### Reactions
- **File:** `static/features/reactions/reactions.js`
- **Purpose:** Emoji reactions to messages
- **Dependencies:** Message History
- **Required by:** User engagement
- **V2 Status:** Missing
- **Migration Priority:** Low

### Emoji Picker
- **Files:** `static/emoji-picker.js`, `static/emoji-data.json`
- **Purpose:** Offline emoji picker
- **Dependencies:** None
- **Required by:** Emoji input
- **V2 Status:** Missing
- **Migration Priority:** Low

### PWA Support
- **Files:** `static/manifest.json`, service worker
- **Purpose:** Progressive Web App features
- **Dependencies:** Config
- **Required by:** Mobile experience
- **V2 Status:** Missing
- **Migration Priority:** Low

---

# DEPENDENCY VISUALIZATION

```
Layer 0 (Foundation):
├── Config System
├── Event Schema
├── Database Schema
└── State Management

Layer 1 (Core Infrastructure):
├── HTTP Routes → Config, State
├── Socket.IO Base → Config, State, Event Schema
└── Rate Limiting → Config, State

Layer 2 (Authentication & Presence):
├── Authentication → Config, State, Event Schema, Rate Limiting
└── Presence → Config, State, Authentication

Layer 3 (Messaging Core):
├── Global Chat → Config, State, Authentication, Event Schema
├── Message Editing/Deletion → Global Chat, State
├── Reply System → Global Chat, State
├── Message Status → Global Chat, State
└── Typing Indicators → Authentication, State

Layer 4 (Advanced Messaging):
├── Spam Protection → Message History, Rate Limiting, State
├── Vote-to-Hide → Message History, State
└── Message Length Limits → Config, Message History

Layer 5 (Direct Messages):
├── DM System → Authentication, Message History, State
├── E2E Encryption for DMs → Web Crypto API, DM System
└── Public Key Exchange → E2E Encryption, Authentication

Layer 6 (Rooms):
├── Room System → Authentication, Message History, State
├── Room Admin → Room System, State
├── Ephemeral Rooms → Room System, Config
└── E2E Encryption for Rooms → Web Crypto API, Room System

Layer 7 (WebRTC Calls):
├── WebRTC Signaling → Authentication, State, Rate Limiting
├── Call Session Management → WebRTC Signaling, State
├── Call Phase Management → Call Session Management
├── Call Tombstone → Call Session Management
├── Offer Lock → Call Session Management
└── ICE Config → Config, HTTP Routes

Layer 8 (Admin Tools):
├── Admin Kick → Room System, Authentication
├── Admin Freeze → Room System, Authentication
└── Shadow Mute → State, Authentication

Layer 9 (File Sharing):
├── File Upload → HTTP Routes, Config, State
├── File Download → HTTP Routes, Config
└── File Validation → Config, File Upload

Layer 10 (Launcher):
├── NEXUS Launcher → Config
└── Ngrok Manager → Config

Layer 11 (Frontend):
├── WhatsApp-style UI → Config, Authentication
├── Modular Architecture → Config
├── Login Page → Authentication
├── Chat Page → Global Chat, Presence
├── Room Page → Room System
├── Call UI → WebRTC Calls
├── Admin Page → Admin Tools
└── UI Components → Config

Layer 12 (Advanced Features):
├── Voice Messages → MediaRecorder API, Audio API, Canvas API
├── Reactions → Message History
├── Emoji Picker → None
└── PWA Support → Config
```

---

# CRITICAL DEPENDENCY CHAINS

## Chain 1: Authentication → Messaging
```
Config → State Management → Authentication → Global Chat → All Messaging Features
```

## Chain 2: Encryption → Secure DMs
```
Config → State Management → Authentication → DM System → E2E Encryption → Public Key Exchange → Secure DMs
```

## Chain 3: Rooms → Room Features
```
Config → State Management → Authentication → Room System → Room Admin → Ephemeral Rooms → E2E Encryption
```

## Chain 4: WebRTC → Calls
```
Config → State Management → Authentication → WebRTC Signaling → Call Session Management → Call Phase Management → Call Tombstone → ICE Config
```

## Chain 5: Frontend → UI
```
Config → Authentication → WhatsApp-style UI → Login Page → Chat Page → Room Page → Call UI → Admin Page
```

---

# MIGRATION ORDER RECOMMENDATIONS

## Phase 1: Foundation (Layer 0)
1. Config System
2. Event Schema
3. Database Schema (adapt V1 schema to V2)
4. State Management (migrate identity hierarchy)

## Phase 2: Core Infrastructure (Layer 1)
1. HTTP Routes
2. Socket.IO Base
3. Rate Limiting

## Phase 3: Authentication & Presence (Layer 2)
1. Authentication System
2. Presence System

## Phase 4: Messaging Core (Layer 3)
1. Global Chat
2. Message Editing/Deletion
3. Reply System
4. Message Status Tracking
5. Typing Indicators

## Phase 5: Advanced Messaging (Layer 4)
1. Spam Protection
2. Vote-to-Hide
3. Message Length Limits

## Phase 6: Direct Messages (Layer 5)
1. DM System
2. E2E Encryption for DMs
3. Public Key Exchange

## Phase 7: Rooms (Layer 6)
1. Room System
2. Room Admin System
3. Ephemeral Rooms
4. E2E Encryption for Rooms

## Phase 8: WebRTC Calls (Layer 7)
1. WebRTC Signaling
2. Call Session Management
3. Call Phase Management
4. Call Tombstone
5. Offer Lock
6. ICE Config

## Phase 9: Admin Tools (Layer 8)
1. Admin Kick
2. Admin Freeze
3. Shadow Mute

## Phase 10: File Sharing (Layer 9)
1. File Upload
2. File Download
3. File Validation

## Phase 11: Launcher (Layer 10)
1. NEXUS Launcher
2. Ngrok Manager

## Phase 12: Frontend (Layer 11)
1. WhatsApp-style UI
2. Modular Architecture
3. Login Page
4. Chat Page
5. Room Page
6. Call UI
7. Admin Page
8. UI Components

## Phase 13: Advanced Features (Layer 12)
1. Voice Messages
2. Reactions
3. Emoji Picker
4. PWA Support
