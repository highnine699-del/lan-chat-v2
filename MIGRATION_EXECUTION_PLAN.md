# LAN CHAT V2 MIGRATION EXECUTION PLAN

**Generated:** May 30, 2026  
**V1 Location:** `c:\Users\AY ADVANCE TECH\Documents\local-whatsapp\lan-chat-final`  
**V2 Location:** `c:\Users\AY ADVANCE TECH\Documents\lan-chat-v2`

---

# EXECUTIVE SUMMARY

This plan is based on **actual code examination** of both V1 and V2 codebases. It provides a phased approach to migrating all V1 features into V2 while respecting dependency chains and minimizing risk.

**Total Features to Migrate:** 103  
**Estimated Duration:** 8-12 weeks (depending on team size)  
**Critical Path:** Foundation → Authentication → Encryption → Messaging → Rooms → Calls → Frontend → Launcher

---

# PHASE 1: FOUNDATION (Week 1-2)

**Goal:** Establish the core infrastructure that all other features depend on.

**Duration:** 2 weeks  
**Risk:** Low  
**Dependencies:** None

## Tasks

### 1.1 Config System Migration
**Source:** `config.py` (165 lines)  
**Destination:** `backend/config.py` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create `backend/config.py` with all V1 configuration constants
2. Add environment variable bindings
3. Add PUBLIC_MODE, DEBUG, SECRET_KEY, ADMIN_PASSWORD, SERVER_PASSWORD
4. Add Socket.IO configuration (MAX_HTTP_BUFFER_SIZE, PING_TIMEOUT, PING_INTERVAL)
5. Add file upload limits (MAX_UPLOAD_BYTES, UPLOAD_FOLDER)
6. Add chat limits (MAX_USERNAME_LEN, MAX_MESSAGE_LEN, MAX_GLOBAL_HISTORY, MAX_PRIVATE_HISTORY)
7. Add spam limits (SPAM_MSG_LIMIT, SPAM_WINDOW_S, SPAM_COOLDOWN_S, SPAM_REPEAT_LIMIT)
8. Add security settings (ALLOWED_ORIGINS, MAX_CONNECTIONS_PER_IP, TRUSTED_PROXY)
9. Add room settings (MAX_ROOM_NAME_LEN, MAX_ROOMS, ROOM_IDLE_GRACE_S, ROOM_HISTORY_SIZE)
10. Add ephemeral settings (EPHEMERAL_TTLS, JOIN_TOKEN_TTL_S)
11. Add TURN/STUN settings (TURN_CREDENTIALS, TURN_URL_TCP, TURN_URL_UDP)

**Verification:**
- All config constants accessible
- Environment variables properly bound
- Default values match V1

**Rollback:** Delete `backend/config.py`

---

### 1.2 Event Schema Migration
**Source:** `events.py` (815 lines)  
**Destination:** `backend/events.py` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create `backend/events.py` with EventSchema class
2. Implement event registry (_REGISTRY)
3. Implement validation functions (get, all_events, validate_payload)
4. Register all V1 events (join, connect, disconnect, message, room:create, room:join, etc.)
5. Add event documentation for each event

**Verification:**
- All V1 events registered
- Validation works for each event type
- Event metadata (direction, auth, scope, payload) correct

**Rollback:** Delete `backend/events.py`

---

### 1.3 Database Schema Adaptation
**Source:** `state.py` (in-memory schema)  
**Destination:** `backend/db.py` (adapt existing)  
**Complexity:** High  
**Steps:**
1. Review existing V2 database schema
2. Add missing tables: public_keys, shadow_muted, spam_tracker, upload_counts, ip_connections, active_sessions, analytics, message_votes, join_tokens
3. Add missing columns to users table: username, tag, display, uid, color, joined_at, msg_count, is_server_admin, persona, presence, last_message, last_message_time, spam_count, room_id
4. Add missing columns to rooms table: visibility, password, creator_sid, members, admins, ttl, messages, is_frozen, delete_timer
5. Add indexes for performance (sid_map, uid_sessions, message_history)
6. Migrate V2's simple schema to V1's complex schema
7. Add migration script to convert existing data

**Verification:**
- All V1 state structures represented in database
- Foreign keys properly defined
- Indexes created for performance
- Migration script works without data loss

**Rollback:** Restore original `backend/db.py` from git

---

### 1.4 State Management Migration
**Source:** `state.py` (1510 lines)  
**Destination:** `backend/core/state.py` (replace existing)  
**Complexity:** High  
**Steps:**
1. Replace simple User class with V1's identity authority hierarchy
2. Implement users dict (primary source of truth)
3. Implement user_state proxy (backward compatibility)
4. Implement sid_map (display → sid reverse index)
5. Implement uid_sessions (uid → sid reverse index)
6. Implement active_sessions (disconnect-safe view)
7. Implement session_tokens (reconnect auth)
8. Implement public_keys (ECDH key storage)
9. Implement message_history (global deque)
10. Implement private_history (per-conversation deques)
11. Implement rooms dict with full schema
12. Implement shadow_muted dict
13. Implement spam_tracker dict
14. Implement upload_counts dict
15. Implement ip_connections dict
16. Implement analytics dict
17. Implement message_votes dict
18. Implement join_tokens dict
19. Implement all accessor functions (register_identity, unregister_identity, set_presence, set_user_room, etc.)
20. Implement cleanup worker

**Verification:**
- All V1 state structures present
- Identity authority hierarchy works
- Accessor functions work correctly
- Cleanup worker runs without errors

**Rollback:** Restore original `backend/core/state.py` from git

---

## PHASE 2: CORE INFRASTRUCTURE (Week 3)

**Goal:** Establish HTTP routes, Socket.IO base, and rate limiting.

**Duration:** 1 week  
**Risk:** Low  
**Dependencies:** Phase 1

## Tasks

### 2.1 HTTP Routes Migration
**Source:** `routes/http.py` (387 lines)  
**Destination:** `backend/routes/http.py` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create `backend/routes/` directory
2. Create `backend/routes/__init__.py`
3. Create `backend/routes/http.py` with all V1 HTTP routes
4. Implement GET / (serve SPA)
5. Implement GET /uploads/<name> (serve uploaded files)
6. Implement GET /ice-config (WebRTC ICE/TURN configuration)
7. Implement POST /upload (file upload)
8. Add security headers (CSP, HSTS, X-Frame-Options, etc.)
9. Add trusted proxy support
10. Add file validation (MIME types, size limits)
11. Add rate limiting for uploads
12. Integrate with FastAPI instead of Flask

**Verification:**
- All HTTP routes accessible
- Security headers present
- File upload/download works
- ICE config returns correct TURN/STUN servers

**Rollback:** Delete `backend/routes/` directory

---

### 2.2 Socket.IO Base Migration
**Source:** `routes/__init__.py`, `server.py`  
**Destination:** `backend/socket_manager.py` (adapt existing)  
**Complexity:** Medium  
**Steps:**
1. Review existing V2 Socket.IO setup
2. Add V1's Socket.IO configuration (max_http_buffer_size, ping_timeout, ping_interval)
3. Add template integrity check
4. Add PID file handling
5. Add ngrok browser-warning bypass
6. Add error handlers (413, 404)
7. Add startup logging
8. Integrate with FastAPI instead of Flask

**Verification:**
- Socket.IO connects successfully
- Configuration matches V1
- Error handlers work
- Logging works

**Rollback:** Restore original `backend/socket_manager.py` from git

---

### 2.3 Rate Limiting Migration
**Source:** `routes/socket_rate_limit.py`  
**Destination:** `backend/routes/socket_rate_limit.py` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create `backend/routes/socket_rate_limit.py`
2. Implement _check_join_rate (IP-based join limiting)
3. Implement _check_signal_rate (WebRTC signal limiting)
4. Implement _get_client_ip (with trusted proxy support)
5. Implement _uid_last_kick (kick cooldown)
6. Implement _UID_KICK_COOLDOWN constant
7. Implement _require_member (room membership check)

**Verification:**
- Join rate limiting works
- Signal rate limiting works
- IP detection works with/without trusted proxy
- Kick cooldown works

**Rollback:** Delete `backend/routes/socket_rate_limit.py`

---

## PHASE 3: AUTHENTICATION & PRESENCE (Week 4)

**Goal:** Implement user authentication and presence tracking.

**Duration:** 1 week  
**Risk:** Medium  
**Dependencies:** Phase 1, Phase 2

## Tasks

### 3.1 Authentication System Migration
**Source:** `routes/socket_auth.py` (496 lines)  
**Destination:** `backend/routes/socket_auth.py` (new file)  
**Complexity:** High  
**Steps:**
1. Create `backend/routes/socket_auth.py`
2. Implement handle_connect (connection validation)
3. Implement handle_join (username/tag registration)
4. Implement username/tag generation (generate_tag, unique_username)
5. Implement session token issuance (issue_session_token)
6. Implement session token verification (verify_session_token)
7. Implement server password validation
8. Implement admin password validation
9. Implement PUBLIC_MODE enforcement
10. Implement join rate limiting integration
11. Implement IP connection limiting
12. Implement UID generation and tracking
13. Implement identity registration (register_identity)
14. Implement identity unregistration (unregister_identity)
15. Implement session registration (register_session)
16. Implement session updates (update_session_room)
17. Implement session teardown (mark_session_disconnected, remove_session)
18. Implement session lookup (get_session, find_session_by_uid)
19. Implement user list generation (get_user_list)
20. Implement next_color assignment

**Verification:**
- Users can join with username/tag
- Session tokens work for reconnection
- Server password enforced
- Admin password grants admin rights
- PUBLIC_MODE requires server password
- Join rate limiting works
- IP connection limiting works
- UID generation works

**Rollback:** Delete `backend/routes/socket_auth.py`

---

### 3.2 Presence System Migration
**Source:** `routes/socket_auth.py`, `state.py`  
**Destination:** `backend/core/presence.py` (enhance existing)  
**Complexity:** Medium  
**Steps:**
1. Enhance existing `backend/core/presence.py`
2. Add user color assignment
3. Add reputation system (reputation_label)
4. Add persona switching
5. Add last message tracking
6. Add last seen tracking
7. Integrate with state management

**Verification:**
- User colors assigned correctly
- Reputation labels display correctly
- Persona switching works
- Last message tracking works
- Last seen tracking works

**Rollback:** Restore original `backend/core/presence.py` from git

---

## PHASE 4: MESSAGING CORE (Week 5)

**Goal:** Implement core messaging features.

**Duration:** 1 week  
**Risk:** Medium  
**Dependencies:** Phase 3

## Tasks

### 4.1 Global Chat Migration
**Source:** `routes/socket_messages.py` (470 lines)  
**Destination:** `backend/routes/socket_messages.py` (new file)  
**Complexity:** High  
**Steps:**
1. Create `backend/routes/socket_messages.py`
2. Implement handle_message (message broadcasting)
3. Implement message dispatch (dispatch_message)
4. Implement global message history
5. Implement message ID tracking
6. Implement message ACK (tempId)
7. Integrate with state management
8. Integrate with event schema
9. Add message length validation

**Verification:**
- Messages broadcast to all users
- Message history maintained
- Message IDs unique
- Message ACK works
- Message length enforced

**Rollback:** Delete `backend/routes/socket_messages.py`

---

### 4.2 Message Editing/Deletion
**Source:** `routes/socket_messages.py`  
**Destination:** `backend/routes/socket_messages.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement handle_edit_message
2. Implement handle_delete_message
3. Implement message finding (_find_message)
4. Add edit tracking (is_edited, edited_at)
5. Add delete tracking (is_deleted)
6. Integrate with database

**Verification:**
- Messages can be edited
- Messages can be deleted
- Edit history tracked
- Delete history tracked

**Rollback:** Remove edit/delete handlers

---

### 4.3 Reply System
**Source:** `routes/socket_messages.py`  
**Destination:** `backend/routes/socket_messages.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement handle_reply_message
2. Add reply_to field to message schema
3. Implement reply chain tracking
4. Integrate with database

**Verification:**
- Messages can be replied to
- Reply chains tracked
- Reply context displayed

**Rollback:** Remove reply handlers

---

### 4.4 Message Status Tracking
**Source:** `routes/socket_messages.py`  
**Destination:** `backend/routes/socket_messages.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement message delivery status
2. Implement message read status
3. Implement read receipts
4. Integrate with database

**Verification:**
- Delivery status tracked
- Read status tracked
- Read receipts work

**Rollback:** Remove status tracking

---

### 4.5 Typing Indicators
**Source:** `routes/socket_messages.py`  
**Destination:** `backend/routes/socket_messages.py` (extend)  
**Complexity:** Low  
**Steps:**
1. Implement handle_typing
2. Broadcast typing events to room
3. Add typing timeout

**Verification:**
- Typing indicators broadcast
- Typing timeout works

**Rollback:** Remove typing handlers

---

## PHASE 5: ADVANCED MESSAGING (Week 6)

**Goal:** Implement spam protection and advanced messaging features.

**Duration:** 1 week  
**Risk:** Medium  
**Dependencies:** Phase 4

## Tasks

### 5.1 Spam Protection
**Source:** `state.py`, `routes/socket_messages.py`  
**Destination:** `backend/core/spam.py` (new file), `backend/routes/socket_messages.py` (extend)  
**Complexity:** High  
**Steps:**
1. Create `backend/core/spam.py`
2. Implement check_smart_spam
3. Implement cooldown_remaining
4. Implement spam_tracker integration
5. Add shadow mute detection
6. Add repeat message detection
7. Integrate with message handlers

**Verification:**
- Smart spam detection works
- Cooldown notifications sent
- Shadow mute applied
- Repeat messages blocked

**Rollback:** Delete `backend/core/spam.py`, remove spam checks

---

### 5.2 Vote-to-Hide
**Source:** `routes/socket_messages.py`  
**Destination:** `backend/routes/socket_messages.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement handle_vote_hide
2. Implement message_votes tracking
3. Add HIDE_VOTE_THRESHOLD check
4. Hide message when threshold reached

**Verification:**
- Users can vote to hide
- Threshold enforced
- Messages hidden when threshold reached

**Rollback:** Remove vote handlers

---

### 5.3 Message Length Limits
**Source:** `config.py`, `routes/socket_messages.py`  
**Destination:** `backend/config.py` (already done), `backend/routes/socket_messages.py` (extend)  
**Complexity:** Low  
**Steps:**
1. Add message length validation
2. Enforce MAX_MESSAGE_LEN
3. Return error for oversized messages

**Verification:**
- Message length enforced
- Error returned for oversized messages

**Rollback:** Remove length validation

---

## PHASE 6: DIRECT MESSAGES (Week 7)

**Goal:** Implement encrypted direct messaging.

**Duration:** 1 week  
**Risk:** High  
**Dependencies:** Phase 4, Phase 5

## Tasks

### 6.1 DM System
**Source:** `routes/socket_messages.py`, `state.py`  
**Destination:** `backend/routes/socket_messages.py` (extend)  
**Complexity:** High  
**Steps:**
1. Implement handle_dm_message
2. Implement private_history tracking
3. Implement private_key generation
4. Implement append_private
5. Add DM target validation
6. Integrate with database

**Verification:**
- DMs sent to target only
- Private history maintained
- DMs not broadcast to global

**Rollback:** Remove DM handlers

---

### 6.2 E2E Encryption for DMs
**Source:** `static/core/encryption.js` (6801 bytes)  
**Destination:** `frontend/core/encryption.js` (new file)  
**Complexity:** High  
**Steps:**
1. Create `frontend/core/encryption.js`
2. Implement ECDH key generation (Web Crypto API)
3. Implement AES-GCM encryption
4. Implement AES-GCM decryption
5. Implement shared secret derivation
6. Implement public key export/import
7. Integrate with DM handlers

**Verification:**
- ECDH keys generated
- Messages encrypted with AES-GCM
- Messages decrypted correctly
- Public keys exchanged

**Rollback:** Delete `frontend/core/encryption.js`

---

### 6.3 Public Key Exchange
**Source:** `state.py`, `routes/socket_auth.py`  
**Destination:** `backend/routes/socket_auth.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement handle_public_key
2. Store public keys in state
3. Implement public key lookup
4. Broadcast public key changes

**Verification:**
- Public keys stored
- Public keys retrieved
- Public key changes broadcast

**Rollback:** Remove public key handlers

---

## PHASE 7: ROOMS (Week 8)

**Goal:** Implement full room system with encryption.

**Duration:** 1 week  
**Risk:** High  
**Dependencies:** Phase 4, Phase 5

## Tasks

### 7.1 Room System
**Source:** `routes/socket_rooms.py` (413 lines), `state.py`  
**Destination:** `backend/routes/socket_rooms.py` (new file)  
**Complexity:** High  
**Steps:**
1. Create `backend/routes/socket_rooms.py`
2. Implement handle_room_create
3. Implement handle_room_join
4. Implement handle_room_leave
5. Implement handle_room_list
6. Implement room password protection
7. Implement room member list
8. Implement room history
9. Integrate with state management
10. Integrate with database

**Verification:**
- Rooms can be created
- Rooms can be joined/left
- Room list works
- Room passwords work
- Room members tracked
- Room history maintained

**Rollback:** Delete `backend/routes/socket_rooms.py`

---

### 7.2 Room Admin System
**Source:** `routes/socket_rooms.py`, `routes/socket_admin.py`  
**Destination:** `backend/routes/socket_rooms.py` (extend), `backend/routes/socket_admin.py` (new file)  
**Complexity:** High  
**Steps:**
1. Implement room creator tracking
2. Implement room moderator assignment
3. Implement is_room_admin check
4. Implement room_member_list
5. Integrate with admin handlers

**Verification:**
- Room creator tracked
- Moderators assigned
- Admin checks work
- Member list accurate

**Rollback:** Remove admin tracking

---

### 7.3 Ephemeral Rooms
**Source:** `state.py`, `routes/socket_rooms.py`, `config.py`  
**Destination:** `backend/routes/socket_rooms.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement TTL-based room deletion
2. Implement schedule_room_delete
3. Implement cancel_room_delete
4. Implement ROOM_IDLE_GRACE_S
5. Implement EPHEMERAL_TTLS

**Verification:**
- Ephemeral rooms auto-delete
- TTL works correctly
- Idle grace period works

**Rollback:** Remove ephemeral logic

---

### 7.4 E2E Encryption for Rooms
**Source:** `static/core/encryption.js`  
**Destination:** `frontend/core/encryption.js` (extend)  
**Complexity:** High  
**Steps:**
1. Extend encryption.js for room messages
2. Implement room key derivation
3. Implement room message encryption
4. Implement room message decryption
5. Integrate with room handlers

**Verification:**
- Room keys derived
- Room messages encrypted
- Room messages decrypted

**Rollback:** Remove room encryption

---

## PHASE 8: WEBRTC CALLS (Week 9)

**Goal:** Implement voice/video calling.

**Duration:** 1 week  
**Risk:** High  
**Dependencies:** Phase 3, Phase 7

## Tasks

### 8.1 WebRTC Signaling
**Source:** `routes/socket_webrtc.py` (335 lines)  
**Destination:** `backend/routes/socket_webrtc.py` (new file)  
**Complexity:** High  
**Steps:**
1. Create `backend/routes/socket_webrtc.py`
2. Implement handle_call_signal
3. Implement offer/answer/ICE exchange
4. Implement signal rate limiting
5. Implement signal size validation
6. Integrate with state management

**Verification:**
- WebRTC signals exchanged
- Rate limiting works
- Size validation works

**Rollback:** Delete `backend/routes/socket_webrtc.py`

---

### 8.2 Call Session Management
**Source:** `state.py`, `routes/socket_webrtc.py`  
**Destination:** `backend/core/calls.py` (new file)  
**Complexity:** High  
**Steps:**
1. Create `backend/core/calls.py`
2. Implement create_call_session
3. Implement get_call_session_id
4. Implement invalidate_call_session
5. Implement join_call
6. Implement leave_call
7. Implement teardown_call
8. Implement _call_key_for_room

**Verification:**
- Call sessions created
- Call sessions tracked
- Call sessions torn down

**Rollback:** Delete `backend/core/calls.py`

---

### 8.3 Call Phase Management
**Source:** `state.py`, `routes/socket_webrtc.py`  
**Destination:** `backend/core/calls.py` (extend)  
**Complexity:** High  
**Steps:**
1. Implement advance_call_phase
2. Implement get_call_phase
3. Implement reset_call_phase
4. Implement mark_call_active
5. Implement phase states (offer, answer, connected)

**Verification:**
- Call phases advance correctly
- Phase state tracked
- Active calls marked

**Rollback:** Remove phase management

---

### 8.4 Call Tombstone
**Source:** `state.py`, `routes/socket_webrtc.py`  
**Destination:** `backend/core/calls.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement write_call_tombstone
2. Implement find_call_tombstone
3. Implement consume_call_tombstone
4. Implement call reconnection logic

**Verification:**
- Call tombstones written
- Call tombstones found
- Call reconnection works

**Rollback:** Remove tombstone logic

---

### 8.5 Offer Lock
**Source:** `state.py`, `routes/socket_webrtc.py`  
**Destination:** `backend/core/calls.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement is_offer_locked
2. Implement set_offer_lock
3. Implement clear_offer_lock
4. Prevent double calls

**Verification:**
- Offer lock works
- Double calls prevented

**Rollback:** Remove offer lock

---

### 8.6 ICE Config
**Source:** `routes/http.py`, `config.py`  
**Destination:** `backend/routes/http.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement _build_ice_servers
2. Add STUN server (stun.l.google.com:19302)
3. Add TURN server support
4. Implement /ice-config endpoint
5. Add TURN credentials

**Verification:**
- ICE config returns STUN servers
- ICE config returns TURN servers
- TURN credentials valid

**Rollback:** Remove ICE config endpoint

---

## PHASE 9: ADMIN TOOLS (Week 10)

**Goal:** Implement admin moderation tools.

**Duration:** 1 week  
**Risk:** Medium  
**Dependencies:** Phase 7

## Tasks

### 9.1 Admin Kick
**Source:** `routes/socket_admin.py` (221 lines)  
**Destination:** `backend/routes/socket_admin.py` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create `backend/routes/socket_admin.py`
2. Implement handle_kick
3. Implement room admin check
4. Implement user removal from room
5. Implement notification to kicked user
6. Implement notification to room

**Verification:**
- Admins can kick users
- Non-admins cannot kick
- Kicked user notified
- Room notified

**Rollback:** Delete `backend/routes/socket_admin.py`

---

### 9.2 Admin Freeze
**Source:** `routes/socket_admin.py`  
**Destination:** `backend/routes/socket_admin.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement handle_freeze
2. Implement room freeze state
3. Prevent messages in frozen rooms
4. Implement unfreeze

**Verification:**
- Admins can freeze rooms
- Messages blocked in frozen rooms
- Rooms can be unfrozen

**Rollback:** Remove freeze handlers

---

### 9.3 Shadow Mute
**Source:** `routes/socket_admin.py`, `state.py`  
**Destination:** `backend/routes/socket_admin.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement handle_shadow_mute
2. Implement shadow_mute tracking
3. Implement shadow_mute duration
4. Silently drop shadow-muted messages

**Verification:**
- Admins can shadow mute
- Shadow-muted messages dropped
- Shadow mute expires

**Rollback:** Remove shadow mute handlers

---

## PHASE 10: FILE SHARING (Week 11)

**Goal:** Implement file upload/download.

**Duration:** 1 week  
**Risk:** Medium  
**Dependencies:** Phase 2

## Tasks

### 10.1 File Upload
**Source:** `routes/http.py`  
**Destination:** `backend/routes/http.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement POST /upload
2. Implement multipart form handling
3. Implement file validation (MIME type, size)
4. Implement sanitize_filename
5. Implement upload rate limiting
6. Store files in UPLOAD_FOLDER

**Verification:**
- Files upload successfully
- Invalid files rejected
- Oversized files rejected
- Upload rate limiting works

**Rollback:** Remove upload handler

---

### 10.2 File Download
**Source:** `routes/http.py`  
**Destination:** `backend/routes/http.py` (extend)  
**Complexity:** Low  
**Steps:**
1. Implement GET /uploads/<name>
2. Implement MIME type detection
3. Implement inline vs attachment disposition
4. Block dangerous MIME types (SVG)

**Verification:**
- Files download successfully
- MIME types correct
- Dangerous files blocked

**Rollback:** Remove download handler

---

### 10.3 File Validation
**Source:** `routes/http.py`  
**Destination:** `backend/routes/http.py` (extend)  
**Complexity:** Medium  
**Steps:**
1. Implement MIME type whitelist
2. Implement file size validation
3. Implement filename sanitization
4. Implement virus scanning (optional)

**Verification:**
- Invalid MIME types rejected
- Oversized files rejected
- Dangerous filenames sanitized

**Rollback:** Remove validation logic

---

## PHASE 11: LAUNCHER (Week 12)

**Goal:** Implement NEXUS GUI launcher.

**Duration:** 1 week  
**Risk:** High  
**Dependencies:** Phase 1

## Tasks

### 11.1 NEXUS Launcher
**Source:** `launcher.py` (2757 lines)  
**Destination:** `launcher.py` (new file in root)  
**Complexity:** High  
**Steps:**
1. Create `launcher.py` in root directory
2. Implement GUI with tkinter
3. Implement dashboard stats (uptime, users, CPU, RAM)
4. Implement start/stop controls
5. Implement browser launch
6. Implement log panel
7. Implement config section
8. Implement ngrok controls
9. Implement system tray
10. Implement QR code display

**Verification:**
- Launcher opens successfully
- Dashboard stats display
- Start/stop works
- Browser launches
- Logs display
- Ngrok controls work
- System tray works
- QR code displays

**Rollback:** Delete `launcher.py`

---

### 11.2 Ngrok Manager
**Source:** `ngrok_manager.py`  
**Destination:** `ngrok_manager.py` (new file in root)  
**Complexity:** High  
**Steps:**
1. Create `ngrok_manager.py`
2. Implement ngrok process management
3. Implement ngrok URL detection
4. Implement ngrok start/stop
5. Implement ngrok authentication

**Verification:**
- Ngrok starts successfully
- Ngrok URL detected
- Ngrok stops successfully
- Ngrok authentication works

**Rollback:** Delete `ngrok_manager.py`

---

## PHASE 12: FRONTEND (Week 13-14)

**Goal:** Implement complete WhatsApp-style UI.

**Duration:** 2 weeks  
**Risk:** High  
**Dependencies:** All previous phases

## Tasks

### 12.1 WhatsApp-style UI
**Source:** `templates/index.html` (3670 lines), `static/style.css` (44012 bytes)  
**Destination:** `frontend/index.html` (replace), `frontend/style.css` (new file)  
**Complexity:** High  
**Steps:**
1. Replace simple HTML with V1's complete SPA
2. Copy V1's CSS (44012 bytes)
3. Implement WhatsApp-style layout
4. Implement sidebar navigation
5. Implement chat area
6. Implement input bar
7. Implement user list panel
8. Implement responsive design
9. Implement mobile support

**Verification:**
- UI matches V1 exactly
- Layout responsive
- Mobile works
- All UI elements present

**Rollback:** Restore original `frontend/index.html`

---

### 12.2 Modular Architecture
**Source:** `static/init.js`, `static/core/`, `static/features/`, `static/ui/`  
**Destination:** `frontend/` (restructure)  
**Complexity:** High  
**Steps:**
1. Create `frontend/core/` directory
2. Create `frontend/features/` directory
3. Create `frontend/ui/` directory
4. Create `frontend/ui/components/` directory
5. Create `frontend/ui/pages/` directory
6. Copy V1's modular structure
7. Implement init.js entry point
8. Implement module loading

**Verification:**
- Modules load correctly
- Module dependencies resolved
- No circular dependencies

**Rollback:** Restore original `frontend/` structure

---

### 12.3 Login Page
**Source:** `static/ui/pages/LoginPage.js`  
**Destination:** `frontend/ui/pages/LoginPage.js` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create LoginPage.js
2. Implement username/tag input
3. Implement server password input
4. Implement admin password input
5. Implement login validation
6. Implement error handling

**Verification:**
- Login page displays
- Username/tag input works
- Passwords validated
- Errors displayed

**Rollback:** Delete LoginPage.js

---

### 12.4 Chat Page
**Source:** `static/ui/pages/ChatPage.js`  
**Destination:** `frontend/ui/pages/ChatPage.js` (new file)  
**Complexity:** High  
**Steps:**
1. Create ChatPage.js
2. Implement message list
3. Implement message rendering
4. Implement input bar
5. Implement emoji picker integration
6. Implement file upload integration
7. Implement voice recording integration
8. Implement typing indicators
9. Implement user list

**Verification:**
- Chat page displays
- Messages render correctly
- Input bar works
- Emoji picker works
- File upload works
- Voice recording works
- Typing indicators work
- User list displays

**Rollback:** Delete ChatPage.js

---

### 12.5 Room Page
**Source:** `static/ui/pages/RoomPage.js`  
**Destination:** `frontend/ui/pages/RoomPage.js` (new file)  
**Complexity:** High  
**Steps:**
1. Create RoomPage.js
2. Implement room list
3. Implement room creation
4. Implement room joining
5. Implement room settings
6. Implement room member list
7. Implement room admin controls

**Verification:**
- Room page displays
- Room list works
- Room creation works
- Room joining works
- Room settings work
- Member list displays
- Admin controls work

**Rollback:** Delete RoomPage.js

---

### 12.6 Call UI
**Source:** `static/ui/pages/CallUI.js`  
**Destination:** `frontend/ui/pages/CallUI.js` (new file)  
**Complexity:** High  
**Steps:**
1. Create CallUI.js
2. Implement call controls (mute, video, hangup)
3. Implement video element
4. Implement audio element
5. Implement call status display
6. Implement WebRTC integration

**Verification:**
- Call UI displays
- Call controls work
- Video displays
- Audio works
- Call status accurate

**Rollback:** Delete CallUI.js

---

### 12.7 Admin Page
**Source:** `static/ui/pages/AdminPage.js`  
**Destination:** `frontend/ui/pages/AdminPage.js` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create AdminPage.js
2. Implement user list
3. Implement kick controls
4. Implement freeze controls
5. Implement shadow mute controls
6. Implement room list
7. Implement room controls

**Verification:**
- Admin page displays
- User list works
- Kick controls work
- Freeze controls work
- Shadow mute controls work
- Room list works
- Room controls work

**Rollback:** Delete AdminPage.js

---

### 12.8 UI Components
**Source:** `static/ui/components/`  
**Destination:** `frontend/ui/components/` (new files)  
**Complexity:** Medium  
**Steps:**
1. Create MessageItem.js
2. Create InputBar.js
3. Create Modal.js
4. Create UserItem.js
5. Implement component reusability
6. Implement component props

**Verification:**
- Components render correctly
- Components reusable
- Props work correctly

**Rollback:** Delete component files

---

## PHASE 13: ADVANCED FEATURES (Week 15)

**Goal:** Implement voice messages, reactions, emoji picker, PWA.

**Duration:** 1 week  
**Risk:** Low  
**Dependencies:** Phase 12

## Tasks

### 13.1 Voice Messages
**Source:** `static/features/voiceMessages/voiceMessages.js`  
**Destination:** `frontend/features/voiceMessages/voiceMessages.js` (new file)  
**Complexity:** Medium  
**Steps:**
1. Create voiceMessages.js
2. Implement MediaRecorder integration
3. Implement audio recording
4. Implement audio playback
5. Implement waveform display
6. Integrate with input bar

**Verification:**
- Voice recording works
- Voice playback works
- Waveform displays

**Rollback:** Delete voiceMessages.js

---

### 13.2 Reactions
**Source:** `static/features/reactions/reactions.js`  
**Destination:** `frontend/features/reactions/reactions.js` (new file)  
**Complexity:** Low  
**Steps:**
1. Create reactions.js
2. Implement emoji reaction UI
3. Implement reaction sending
4. Implement reaction display
5. Integrate with message components

**Verification:**
- Reaction UI displays
- Reactions send correctly
- Reactions display correctly

**Rollback:** Delete reactions.js

---

### 13.3 Emoji Picker
**Source:** `static/emoji-picker.js`, `static/emoji-data.json`, `static/emoji-picker-picker.js`  
**Destination:** `frontend/emoji-picker.js`, `frontend/emoji-data.json`, `frontend/emoji-picker-picker.js` (new files)  
**Complexity:** Low  
**Steps:**
1. Copy emoji-picker.js
2. Copy emoji-data.json
3. Copy emoji-picker-picker.js
4. Integrate with input bar
5. Ensure offline support

**Verification:**
- Emoji picker displays
- Emoji selection works
- Offline support works

**Rollback:** Delete emoji files

---

### 13.4 PWA Support
**Source:** `static/manifest.json`, service worker  
**Destination:** `frontend/manifest.json`, `frontend/service-worker.js` (new files)  
**Complexity:** Medium  
**Steps:**
1. Copy manifest.json
2. Create service-worker.js
3. Implement offline caching
4. Add iOS meta tags
5. Add app icons

**Verification:**
- PWA installable
- Offline caching works
- iOS meta tags present
- App icons display

**Rollback:** Delete PWA files

---

# SUMMARY

**Total Phases:** 13  
**Total Duration:** 15 weeks  
**Total Features:** 103  
**Critical Path:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 6 → Phase 7 → Phase 8 → Phase 12

**Success Criteria:**
- All V1 features migrated to V2
- V2 works independently of V1
- Users cannot tell the difference between V1 and V2
- V1 can be deleted after migration

**Rollback Strategy:**
- Each task has explicit rollback steps
- Git commits at each phase completion
- Database backups before schema changes
- Feature flags for gradual rollout
