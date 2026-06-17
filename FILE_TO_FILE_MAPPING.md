# LAN CHAT V2 FILE TO FILE MAPPING

**Generated:** May 30, 2026  
**V1 Location:** `c:\Users\AY ADVANCE TECH\Documents\local-whatsapp\lan-chat-final`  
**V2 Location:** `c:\Users\AY ADVANCE TECH\Documents\lan-chat-v2`

---

# EXECUTIVE SUMMARY

This document provides a complete mapping of every important V1 file to its V2 destination. Nothing should remain unmapped.

**Total Files to Migrate:** ~85  
**Backend Files:** 15  
**Frontend Files:** ~60  
**Root Files:** 5  
**Asset Files:** ~5

---

# ROOT FILES

## config.py
**V1 Path:** `config.py` (165 lines, 10386 bytes)  
**V2 Path:** `backend/config.py` (new file)  
**Type:** Configuration  
**Status:** New file required  
**Notes:** Contains all configuration constants, environment variable bindings, Socket.IO settings, file upload limits, chat limits, spam limits, security settings, room settings, ephemeral settings, TURN/STUN settings

---

## events.py
**V1 Path:** `events.py` (815 lines, 21519 bytes)  
**V2 Path:** `backend/events.py` (new file)  
**Type:** Event Schema  
**Status:** New file required  
**Notes:** Contains EventSchema class, event registry (_REGISTRY), validation functions (get, all_events, validate_payload), all V1 event registrations

---

## state.py
**V1 Path:** `state.py` (1510 lines, 61196 bytes)  
**V2 Path:** `backend/core/state.py` (replace existing)  
**Type:** State Management  
**Status:** Replace existing file  
**Notes:** Contains identity authority hierarchy, users dict, user_state proxy, sid_map, uid_sessions, active_sessions, session_tokens, public_keys, message_history, private_history, rooms dict, shadow_muted, spam_tracker, upload_counts, ip_connections, analytics, message_votes, join_tokens, all accessor functions, cleanup worker

---

## server.py
**V1 Path:** `server.py` (9908 bytes)  
**V2 Path:** `backend/main.py` (adapt existing)  
**Type:** Server Entry Point  
**Status:** Adapt existing file  
**Notes:** Contains Flask app initialization, Socket.IO setup, template integrity check, PID file handling, ngrok browser-warning bypass, error handlers, startup logging. Must be adapted for FastAPI

---

## launcher.py
**V1 Path:** `launcher.py` (2757 lines, 129747 bytes)  
**V2 Path:** `launcher.py` (new file in root)  
**Type:** Desktop Launcher  
**Status:** New file required  
**Notes:** Contains NEXUS GUI launcher with tkinter, dashboard stats, start/stop controls, browser launch, log panel, config section, ngrok controls, system tray, QR code display

---

## ngrok_manager.py
**V1 Path:** `ngrok_manager.py` (6594 bytes)  
**V2 Path:** `ngrok_manager.py` (new file in root)  
**Type:** Ngrok Management  
**Status:** New file required  
**Notes:** Contains ngrok process management, ngrok URL detection, ngrok start/stop, ngrok authentication

---

# BACKEND ROUTES

## routes/__init__.py
**V1 Path:** `routes/__init__.py` (568 bytes)  
**V2 Path:** `backend/routes/__init__.py` (new file)  
**Type:** Routes Package  
**Status:** New file required  
**Notes:** Routes package initialization

---

## routes/http.py
**V1 Path:** `routes/http.py` (387 lines, 13791 bytes)  
**V2 Path:** `backend/routes/http.py` (new file)  
**Type:** HTTP Routes  
**Status:** New file required  
**Notes:** Contains GET / (serve SPA), GET /uploads/<name> (serve uploaded files), GET /ice-config (WebRTC ICE/TURN configuration), POST /upload (file upload), security headers (CSP, HSTS, X-Frame-Options, etc.), trusted proxy support, file validation (MIME types, size limits), upload rate limiting. Must be adapted for FastAPI

---

## routes/socket_admin.py
**V1 Path:** `routes/socket_admin.py` (221 lines, 7808 bytes)  
**V2 Path:** `backend/routes/socket_admin.py` (new file)  
**Type:** Admin Socket Routes  
**Status:** New file required  
**Notes:** Contains handle_kick (admin kick), handle_freeze (room freeze), handle_shadow_mute (shadow mute), room admin check, user removal from room, notification to kicked user, notification to room

---

## routes/socket_auth.py
**V1 Path:** `routes/socket_auth.py` (496 lines, 19463 bytes)  
**V2 Path:** `backend/routes/socket_auth.py` (new file)  
**Type:** Authentication Socket Routes  
**Status:** New file required  
**Notes:** Contains handle_connect (connection validation), handle_join (username/tag registration), username/tag generation (generate_tag, unique_username), session token issuance (issue_session_token), session token verification (verify_session_token), server password validation, admin password validation, PUBLIC_MODE enforcement, join rate limiting integration, IP connection limiting, UID generation and tracking, identity registration (register_identity), identity unregistration (unregister_identity), session registration (register_session), session updates (update_session_room), session teardown (mark_session_disconnected, remove_session), session lookup (get_session, find_session_by_uid), user list generation (get_user_list), next_color assignment

---

## routes/socket_messages.py
**V1 Path:** `routes/socket_messages.py` (470 lines, 16872 bytes)  
**V2 Path:** `backend/routes/socket_messages.py` (new file)  
**Type:** Messaging Socket Routes  
**Status:** New file required  
**Notes:** Contains handle_message (message broadcasting), message dispatch (dispatch_message), global message history, message ID tracking, message ACK (tempId), handle_edit_message, handle_delete_message, message finding (_find_message), edit tracking (is_edited, edited_at), delete tracking (is_deleted), handle_reply_message, reply_to field, reply chain tracking, handle_typing, typing events broadcast, typing timeout, handle_dm_message, private_history tracking, private_key generation, append_private, DM target validation, handle_vote_hide, message_votes tracking, HIDE_VOTE_THRESHOLD check

---

## routes/socket_rate_limit.py
**V1 Path:** `routes/socket_rate_limit.py` (5712 bytes)  
**V2 Path:** `backend/routes/socket_rate_limit.py` (new file)  
**Type:** Rate Limiting Socket Routes  
**Status:** New file required  
**Notes:** Contains _check_join_rate (IP-based join limiting), _check_signal_rate (WebRTC signal limiting), _get_client_ip (with trusted proxy support), _uid_last_kick (kick cooldown), _UID_KICK_COOLDOWN constant, _require_member (room membership check)

---

## routes/socket_rooms.py
**V1 Path:** `routes/socket_rooms.py` (413 lines, 14265 bytes)  
**V2 Path:** `backend/routes/socket_rooms.py` (new file)  
**Type:** Rooms Socket Routes  
**Status:** New file required  
**Notes:** Contains handle_room_create, handle_room_join, handle_room_leave, handle_room_list, room password protection, room member list, room history, room creator tracking, room moderator assignment, is_room_admin check, room_member_list, TTL-based room deletion, schedule_room_delete, cancel_room_delete, ROOM_IDLE_GRACE_S, EPHEMERAL_TTLS

---

## routes/socket_webrtc.py
**V1 Path:** `routes/socket_webrtc.py` (335 lines, 11658 bytes)  
**V2 Path:** `backend/routes/socket_webrtc.py` (new file)  
**Type:** WebRTC Socket Routes  
**Status:** New file required  
**Notes:** Contains handle_call_signal, offer/answer/ICE exchange, signal rate limiting, signal size validation

---

## routes/sockets.py
**V1 Path:** `routes/sockets.py` (1726 bytes)  
**V2 Path:** `backend/socket_manager.py` (adapt existing)  
**Type:** Socket.IO Manager  
**Status:** Adapt existing file  
**Notes:** Contains Socket.IO configuration, max_http_buffer_size, ping_timeout, ping_interval, template integrity check, PID file handling, ngrok browser-warning bypass, error handlers (413, 404), startup logging. Must be adapted for FastAPI

---

# BACKEND CORE

## backend/core/state.py
**V1 Path:** `state.py` (identity authority hierarchy)  
**V2 Path:** `backend/core/state.py` (replace existing)  
**Type:** State Management  
**Status:** Replace existing file  
**Notes:** Currently contains simple User class. Must be replaced with V1's identity authority hierarchy, users dict, user_state proxy, sid_map, uid_sessions, active_sessions, session_tokens, public_keys, message_history, private_history, rooms dict, shadow_muted, spam_tracker, upload_counts, ip_connections, analytics, message_votes, join_tokens, all accessor functions, cleanup worker

---

## backend/core/rooms.py
**V1 Path:** `state.py` (rooms dict)  
**V2 Path:** `backend/core/rooms.py` (enhance existing)  
**Type:** Room Management  
**Status:** Enhance existing file  
**Notes:** Currently contains basic Room class. Must be enhanced with V1's room schema (visibility, password, creator_sid, members, admins, ttl, messages, is_frozen, delete_timer), room password protection, room member list, room history, room creator tracking, room moderator assignment, is_room_admin check, TTL-based room deletion, schedule_room_delete, cancel_room_delete

---

## backend/core/presence.py
**V1 Path:** `state.py` (presence tracking)  
**V2 Path:** `backend/core/presence.py` (enhance existing)  
**Type:** Presence Management  
**Status:** Enhance existing file  
**Notes:** Currently contains basic presence tracking. Must be enhanced with user color assignment, reputation system (reputation_label), persona switching, last message tracking, last seen tracking

---

## backend/core/messages.py
**V1 Path:** `state.py` (message history)  
**V2 Path:** `backend/core/messages.py` (enhance existing)  
**Type:** Message Management  
**Status:** Enhance existing file  
**Notes:** Currently contains basic message handling. Must be enhanced with message ID tracking, message ACK (tempId), edit tracking (is_edited, edited_at), delete tracking (is_deleted), reply_to field, reply chain tracking, message delivery status, message read status, read receipts

---

## backend/core/events.py
**V1 Path:** `events.py` (event schema)  
**V2 Path:** `backend/core/events.py` (enhance existing)  
**Type:** Event Management  
**Status:** Enhance existing file  
**Notes:** Currently contains basic event bus. Must be enhanced with EventSchema class, event registry (_REGISTRY), validation functions (get, all_events, validate_payload), all V1 event registrations

---

## backend/core/spam.py
**V1 Path:** `state.py` (spam tracking)  
**V2 Path:** `backend/core/spam.py` (new file)  
**Type:** Spam Protection  
**Status:** New file required  
**Notes:** Contains check_smart_spam, cooldown_remaining, spam_tracker integration, shadow mute detection, repeat message detection

---

## backend/core/calls.py
**V1 Path:** `state.py` (call sessions)  
**V2 Path:** `backend/core/calls.py` (new file)  
**Type:** Call Management  
**Status:** New file required  
**Notes:** Contains create_call_session, get_call_session_id, invalidate_call_session, join_call, leave_call, teardown_call, _call_key_for_room, advance_call_phase, get_call_phase, reset_call_phase, mark_call_active, phase states (offer, answer, connected), write_call_tombstone, find_call_tombstone, consume_call_tombstone, call reconnection logic, is_offer_locked, set_offer_lock, clear_offer_lock

---

# BACKEND EVENTS

## backend/events/chat_events.py
**V1 Path:** `routes/socket_messages.py` (message events)  
**V2 Path:** `backend/events/chat_events.py` (enhance existing)  
**Type:** Chat Events  
**Status:** Enhance existing file  
**Notes:** Currently contains basic chat events. Must be enhanced with all V1 message events (join, connect, disconnect, message, message:edit, message:delete, message:reply, message:ack, typing:start, typing:stop, dm, dm:ack, room:create, room:join, room:leave, room:list, room:members, room:freeze, room:unfreeze, room:promote, room:demote, admin:kick, admin:freeze, admin:shadow_mute, call:offer, call:answer, call:ice, call:leave, call:signal, public_key, public_key:request, message:vote_hide, message:react)

---

# BACKEND DATABASE

## backend/db.py
**V1 Path:** `state.py` (in-memory schema)  
**V2 Path:** `backend/db.py` (adapt existing)  
**Type:** Database Schema  
**Status:** Adapt existing file  
**Notes:** Currently contains basic SQLite schema. Must be adapted to V1's schema: add tables (public_keys, shadow_muted, spam_tracker, upload_counts, ip_connections, active_sessions, analytics, message_votes, join_tokens), add columns to users table (username, tag, display, uid, color, joined_at, msg_count, is_server_admin, persona, presence, last_message, last_message_time, spam_count, room_id), add columns to rooms table (visibility, password, creator_sid, members, admins, ttl, messages, is_frozen, delete_timer), add indexes for performance (sid_map, uid_sessions, message_history)

---

# BACKEND APP

## backend/app.py
**V1 Path:** `server.py` (Flask app)  
**V2 Path:** `backend/app.py` (adapt existing)  
**Type:** FastAPI App  
**Status:** Adapt existing file  
**Notes:** Currently contains basic FastAPI app. Must be adapted to include all V1 HTTP routes, Socket.IO setup, security headers, error handlers, startup logging

---

## backend/main.py
**V1 Path:** `server.py` (server entry point)  
**V2 Path:** `backend/main.py` (adapt existing)  
**Type:** Server Entry Point  
**Status:** Adapt existing file  
**Notes:** Currently contains basic server startup. Must be adapted to include template integrity check, PID file handling, ngrok browser-warning bypass, error handlers, startup logging

---

# FRONTEND ROOT

## templates/index.html
**V1 Path:** `templates/index.html` (3670 lines)  
**V2 Path:** `frontend/index.html` (replace existing)  
**Type:** Main HTML  
**Status:** Replace existing file  
**Notes:** Currently contains simple HTML (399 lines). Must be replaced with V1's complete SPA (3670 lines) with WhatsApp-style layout, sidebar navigation, chat area, input bar, user list panel, iOS meta tags

---

## static/style.css
**V1 Path:** `static/style.css` (44012 bytes)  
**V2 Path:** `frontend/style.css` (new file)  
**Type:** Main CSS  
**Status:** New file required  
**Notes:** Contains complete WhatsApp-style CSS (44012 bytes)

---

## static/app.js
**V1 Path:** `static/app.js` (195491 bytes)  
**V2 Path:** `frontend/app.js` (new file)  
**Type:** Main JavaScript  
**Status:** New file required  
**Notes:** Contains main application logic (195491 bytes). Must be adapted for modular architecture

---

# FRONTEND CORE

## static/init.js
**V1 Path:** `static/init.js` (11292 bytes)  
**V2 Path:** `frontend/init.js` (new file)  
**Type:** Frontend Initialization  
**Status:** New file required  
**Notes:** Contains frontend initialization, module loading, entry point

---

## static/core/index.js
**V1 Path:** `static/core/index.js` (306 bytes)  
**V2 Path:** `frontend/core/index.js` (new file)  
**Type:** Core Package  
**Status:** New file required  
**Notes:** Core package initialization

---

## static/core/config.js
**V1 Path:** `static/core/config.js` (1683 bytes)  
**V2 Path:** `frontend/core/config.js` (new file)  
**Type:** Frontend Config  
**Status:** New file required  
**Notes:** Contains frontend configuration, environment variable bindings

---

## static/core/encryption.js
**V1 Path:** `static/core/encryption.js` (6801 bytes)  
**V2 Path:** `frontend/core/encryption.js` (new file)  
**Type:** Encryption  
**Status:** New file required  
**Notes:** Contains ECDH key generation (Web Crypto API), AES-GCM encryption, AES-GCM decryption, shared secret derivation, public key export/import

---

## static/core/eventBus.js
**V1 Path:** `static/core/eventBus.js` (1619 bytes)  
**V2 Path:** `frontend/core/eventBus.js` (new file)  
**Type:** Event Bus  
**Status:** New file required  
**Notes:** Contains client-side event bus for component communication

---

## static/core/socket.js
**V1 Path:** `static/core/socket.js` (4923 bytes)  
**V2 Path:** `frontend/core/socket.js` (new file)  
**Type:** Socket Client  
**Status:** New file required  
**Notes:** Contains Socket.IO client setup, connection management, event handlers, reconnection logic

---

## static/core/state/
**V1 Path:** `static/core/state/` (5 items)  
**V2 Path:** `frontend/core/state/` (new directory)  
**Type:** Frontend State  
**Status:** New directory required  
**Notes:** Contains client-side state management

---

# FRONTEND FEATURES

## static/features/index.js
**V1 Path:** `static/features/index.js` (282 bytes)  
**V2 Path:** `frontend/features/index.js` (new file)  
**Type:** Features Package  
**Status:** New file required  
**Notes:** Features package initialization

---

## static/features/admin/
**V1 Path:** `static/features/admin/` (2 items)  
**V2 Path:** `frontend/features/admin/` (new directory)  
**Type:** Admin Features  
**Status:** New directory required  
**Notes:** Contains admin.js (3275 bytes), index.js (102 bytes). Admin controls, kick, freeze, shadow mute

---

## static/features/files/
**V1 Path:** `static/features/files/` (2 items)  
**V2 Path:** `frontend/features/files/` (new directory)  
**Type:** File Features  
**Status:** New directory required  
**Notes:** Contains files.js (3181 bytes), index.js (102 bytes). File upload, file download, file validation

---

## static/features/presence/
**V1 Path:** `static/features/presence/` (2 items)  
**V2 Path:** `frontend/features/presence/` (new directory)  
**Type:** Presence Features  
**Status:** New directory required  
**Notes:** Contains presence tracking, online/offline status, user colors, reputation labels

---

## static/features/reactions/
**V1 Path:** `static/features/reactions/` (2 items)  
**V2 Path:** `frontend/features/reactions/` (new directory)  
**Type:** Reactions Features  
**Status:** New directory required  
**Notes:** Contains reactions.js, index.js (102 bytes). Emoji reactions to messages

---

## static/features/typing/
**V1 Path:** `static/features/typing/` (2 items)  
**V2 Path:** `frontend/features/typing/` (new directory)  
**Type:** Typing Features  
**Status:** New directory required  
**Notes:** Contains typing indicators, typing timeout

---

## static/features/voiceMessages/
**V1 Path:** `static/features/voiceMessages/` (2 items)  
**V2 Path:** `frontend/features/voiceMessages/` (new directory)  
**Type:** Voice Message Features  
**Status:** New directory required  
**Notes:** Contains voiceMessages.js (6307 bytes), index.js (135 bytes). Voice recording, voice playback, waveform display

---

## static/messages/
**V1 Path:** `static/messages/` (5 items)  
**V2 Path:** `frontend/messages/` (new directory)  
**Type:** Message Features  
**Status:** New directory required  
**Notes:** Contains message rendering, message editing, message deletion, reply system, message status tracking

---

## static/rooms/
**V1 Path:** `static/rooms/` (4 items)  
**V2 Path:** `frontend/rooms/` (new directory)  
**Type:** Room Features  
**Status:** New directory required  
**Notes:** Contains room list, room creation, room joining, room settings

---

## static/call/
**V1 Path:** `static/call/` (11 items)  
**V2 Path:** `frontend/call/` (new directory)  
**Type:** Call Features  
**Status:** New directory required  
**Notes:** Contains WebRTC signaling, voice calls, video calls, ICE handling

---

# FRONTEND UI

## static/ui/index.js
**V1 Path:** `static/ui/index.js` (233 bytes)  
**V2 Path:** `frontend/ui/index.js` (new file)  
**Type:** UI Package  
**Status:** New file required  
**Notes:** UI package initialization

---

## static/ui/components/index.js
**V1 Path:** `static/ui/components/index.js` (233 bytes)  
**V2 Path:** `frontend/ui/components/index.js` (new file)  
**Type:** Components Package  
**Status:** New file required  
**Notes:** Components package initialization

---

## static/ui/components/InputBar.js
**V1 Path:** `static/ui/components/InputBar.js` (5727 bytes)  
**V2 Path:** `frontend/ui/components/InputBar.js` (new file)  
**Type:** Input Bar Component  
**Status:** New file required  
**Notes:** Contains rich input bar with emoji picker, file upload, voice recording

---

## static/ui/components/MessageItem.js
**V1 Path:** `static/ui/components/MessageItem.js` (9783 bytes)  
**V2 Path:** `frontend/ui/components/MessageItem.js` (new file)  
**Type:** Message Item Component  
**Status:** New file required  
**Notes:** Contains message rendering, edit/delete controls, reply display, reactions display

---

## static/ui/components/Modal.js
**V1 Path:** `static/ui/components/Modal.js` (4768 bytes)  
**V2 Path:** `frontend/ui/components/Modal.js` (new file)  
**Type:** Modal Component  
**Status:** New file required  
**Notes:** Contains reusable modal component for dialogs and confirmations

---

## static/ui/components/UserItem.js
**V1 Path:** `static/ui/components/UserItem.js` (5325 bytes)  
**V2 Path:** `frontend/ui/components/UserItem.js` (new file)  
**Type:** User Item Component  
**Status:** New file required  
**Notes:** Contains user display with color, reputation label, online/offline status

---

## static/ui/pages/index.js
**V1 Path:** `static/ui/pages/index.js` (265 bytes)  
**V2 Path:** `frontend/ui/pages/index.js` (new file)  
**Type:** Pages Package  
**Status:** New file required  
**Notes:** Pages package initialization

---

## static/ui/pages/LoginPage.js
**V1 Path:** `static/ui/pages/LoginPage.js` (3625 bytes)  
**V2 Path:** `frontend/ui/pages/LoginPage.js` (new file)  
**Type:** Login Page  
**Status:** New file required  
**Notes:** Contains login page with username/tag input, server password input, admin password input, login validation, error handling

---

## static/ui/pages/ChatPage.js
**V1 Path:** `static/ui/pages/ChatPage.js` (10485 bytes)  
**V2 Path:** `frontend/ui/pages/ChatPage.js` (new file)  
**Type:** Chat Page  
**Status:** New file required  
**Notes:** Contains chat page with message list, message rendering, input bar, emoji picker integration, file upload integration, voice recording integration, typing indicators, user list

---

## static/ui/pages/RoomPage.js
**V1 Path:** `static/ui/pages/RoomPage.js` (7274 bytes)  
**V2 Path:** `frontend/ui/pages/RoomPage.js` (new file)  
**Type:** Room Page  
**Status:** New file required  
**Notes:** Contains room page with room list, room creation, room joining, room settings, room member list, room admin controls

---

## static/ui/pages/CallUI.js
**V1 Path:** `static/ui/pages/CallUI.js` (4843 bytes)  
**V2 Path:** `frontend/ui/pages/CallUI.js` (new file)  
**Type:** Call UI  
**Status:** New file required  
**Notes:** Contains call UI with call controls (mute, video, hangup), video element, audio element, call status display, WebRTC integration

---

## static/ui/pages/AdminPage.js
**V1 Path:** `static/ui/pages/AdminPage.js` (2772 bytes)  
**V2 Path:** `frontend/ui/pages/AdminPage.js` (new file)  
**Type:** Admin Page  
**Status:** New file required  
**Notes:** Contains admin page with user list, kick controls, freeze controls, shadow mute controls, room list, room controls

---

# FRONTEND UTILS

## static/utils/
**V1 Path:** `static/utils/` (6 items)  
**V2 Path:** `frontend/utils/` (new directory)  
**Type:** Utility Functions  
**Status:** New directory required  
**Notes:** Contains utility functions for date formatting, message formatting, etc.

---

# FRONTEND ASSETS

## static/icon-192.png
**V1 Path:** `static/icon-192.png` (7719 bytes)  
**V2 Path:** `frontend/icon-192.png` (new file)  
**Type:** App Icon  
**Status:** New file required  
**Notes:** 192x192 app icon for PWA

---

## static/icon-512.png
**V1 Path:** `static/icon-512.png` (24529 bytes)  
**V2 Path:** `frontend/icon-512.png` (new file)  
**Type:** App Icon  
**Status:** New file required  
**Notes:** 512x512 app icon for PWA

---

## static/icon.svg
**V1 Path:** `static/icon.svg` (2639 bytes)  
**V2 Path:** `frontend/icon.svg` (new file)  
**Type:** App Icon  
**Status:** New file required  
**Notes:** SVG app icon

---

## static/icon.ico
**V1 Path:** `static/icon.ico` (14234 bytes)  
**V2 Path:** `frontend/icon.ico` (new file)  
**Type:** App Icon  
**Status:** New file required  
**Notes:** ICO app icon for Windows

---

## static/logo.svg
**V1 Path:** `static/logo.svg` (3167 bytes)  
**V2 Path:** `frontend/logo.svg` (new file)  
**Type:** Logo  
**Status:** New file required  
**Notes:** Logo SVG

---

## static/wallpaper.svg
**V1 Path:** `static/wallpaper.svg` (2937 bytes)  
**V2 Path:** `frontend/wallpaper.svg` (new file)  
**Type:** Wallpaper  
**Status:** New file required  
**Notes:** Chat background wallpaper

---

# FRONTEND PWA

## static/manifest.json
**V1 Path:** `static/manifest.json` (646 bytes)  
**V2 Path:** `frontend/manifest.json` (new file)  
**Type:** PWA Manifest  
**Status:** New file required  
**Notes:** PWA manifest for installation

---

## static/service-worker.js
**V1 Path:** `static/` (service-worker.js)  
**V2 Path:** `frontend/service-worker.js` (new file)  
**Type:** Service Worker  
**Status:** New file required  
**Notes:** Service worker for offline support

---

# FRONTEND EMOJI

## static/emoji-picker.js
**V1 Path:** `static/emoji-picker.js` (127 bytes)  
**V2 Path:** `frontend/emoji-picker.js` (new file)  
**Type:** Emoji Picker  
**Status:** New file required  
**Notes:** Emoji picker entry point

---

## static/emoji-picker-picker.js
**V1 Path:** `static/emoji-picker-picker.js` (73480 bytes)  
**V2 Path:** `frontend/emoji-picker-picker.js` (new file)  
**Type:** Emoji Picker  
**Status:** New file required  
**Notes:** Emoji picker implementation

---

## static/emoji-picker-database.js
**V1 Path:** `static/emoji-picker-database.js` (31014 bytes)  
**V2 Path:** `frontend/emoji-picker-database.js` (new file)  
**Type:** Emoji Picker  
**Status:** New file required  
**Notes:** Emoji picker database

---

## static/emoji-data.json
**V1 Path:** `static/emoji-data.json` (439662 bytes)  
**V2 Path:** `frontend/emoji-data.json` (new file)  
**Type:** Emoji Data  
**Status:** New file required  
**Notes:** Emoji database for offline support (439662 bytes)

---

# FRONTEND SOCKET.IO

## static/socket.io.min.js
**V1 Path:** `static/socket.io.min.js` (49739 bytes)  
**V2 Path:** `frontend/socket.io.min.js` (new file)  
**Type:** Socket.IO Client  
**Status:** New file required  
**Notes:** Socket.IO client library

---

# ROOT CONFIGURATION

## launcher_config.json
**V1 Path:** `launcher_config.json` (268 bytes)  
**V2 Path:** `launcher_config.json` (new file in root)  
**Type:** Launcher Config  
**Status:** New file required  
**Notes:** Launcher configuration file

---

## launcher_config.json.example
**V1 Path:** `launcher_config.json.example` (260 bytes)  
**V2 Path:** `launcher_config.json.example` (new file in root)  
**Type:** Launcher Config Example  
**Status:** New file required  
**Notes:** Launcher configuration example file

---

# ROOT SCRIPTS

## start.bat
**V1 Path:** `start.bat` (3207 bytes)  
**V2 Path:** `start.bat` (adapt existing)  
**Type:** Start Script  
**Status:** Adapt existing file  
**Notes:** Contains server startup script. Must be adapted for V2

---

## stop.bat
**V1 Path:** `stop.bat` (3227 bytes)  
**V2 Path:** `stop.bat` (adapt existing)  
**Type:** Stop Script  
**Status:** Adapt existing file  
**Notes:** Contains server stop script. Must be adapted for V2

---

## start_with_ngrok.bat
**V1 Path:** `start_with_ngrok.bat` (7973 bytes)  
**V2 Path:** `start_with_ngrok.bat` (adapt existing)  
**Type:** Start with Ngrok Script  
**Status:** Adapt existing file  
**Notes:** Contains server startup with ngrok script. Must be adapted for V2

---

## launch_control_center.bat
**V1 Path:** `launch_control_center.bat` (169 bytes)  
**V2 Path:** `launch_control_center.bat` (adapt existing)  
**Type:** Launch Control Center Script  
**Status:** Adapt existing file  
**Notes:** Contains launcher startup script. Must be adapted for V2

---

## launch_control_center.vbs
**V1 Path:** `launch_control_center.vbs` (659 bytes)  
**V2 Path:** `launch_control_center.vbs` (adapt existing)  
**Type:** Launch Control Center VBS  
**Status:** Adapt existing file  
**Notes:** Contains launcher startup VBS script. Must be adapted for V2

---

## build-exe.ps1
**V1 Path:** `build-exe.ps1` (1222 bytes)  
**V2 Path:** `build-exe.ps1` (adapt existing)  
**Type:** Build Script  
**Status:** Adapt existing file  
**Notes:** Contains PyInstaller build script. Must be adapted for V2

---

## build312.bat
**V1 Path:** `build312.bat` (326 bytes)  
**V2 Path:** `build312.bat` (adapt existing)  
**Type:** Build Script  
**Status:** Adapt existing file  
**Notes:** Contains PyInstaller build script for Python 3.12. Must be adapted for V2

---

## release.bat
**V1 Path:** `release.bat` (399 bytes)  
**V2 Path:** `release.bat` (adapt existing)  
**Type:** Release Script  
**Status:** Adapt existing file  
**Notes:** Contains release script. Must be adapted for V2

---

## create-shortcut.ps1
**V1 Path:** `create-shortcut.ps1` (605 bytes)  
**V2 Path:** `create-shortcut.ps1` (adapt existing)  
**Type:** Shortcut Script  
**Status:** Adapt existing file  
**Notes:** Contains shortcut creation script. Must be adapted for V2

---

## create-gui-shortcut.ps1
**V1 Path:** `create-gui-shortcut.ps1` (1639 bytes)  
**V2 Path:** `create-gui-shortcut.ps1` (adapt existing)  
**Type:** GUI Shortcut Script  
**Status:** Adapt existing file  
**Notes:** Contains GUI shortcut creation script. Must be adapted for V2

---

# ROOT UTILITIES

## config_manager.py
**V1 Path:** `config_manager.py` (3435 bytes)  
**V2 Path:** `config_manager.py` (adapt existing)  
**Type:** Config Manager  
**Status:** Adapt existing file  
**Notes:** Contains configuration management utilities. Must be adapted for V2

---

## controller.py
**V1 Path:** `controller.py` (10544 bytes)  
**V2 Path:** `controller.py` (adapt existing)  
**Type:** Controller  
**Status:** Adapt existing file  
**Notes:** Contains server controller. Must be adapted for V2

---

## process_manager.py
**V1 Path:** `process_manager.py` (4226 bytes)  
**V2 Path:** `process_manager.py` (adapt existing)  
**Type:** Process Manager  
**Status:** Adapt existing file  
**Notes:** Contains process management utilities. Must be adapted for V2

---

## service_api.py
**V1 Path:** `service_api.py` (9368 bytes)  
**V2 Path:** `service_api.py` (adapt existing)  
**Type:** Service API  
**Status:** Adapt existing file  
**Notes:** Contains service API. Must be adapted for V2

---

## state_tracker.py
**V1 Path:** `state_tracker.py` (6141 bytes)  
**V2 Path:** `state_tracker.py` (adapt existing)  
**Type:** State Tracker  
**Status:** Adapt existing file  
**Notes:** Contains state tracking utilities. Must be adapted for V2

---

## state_log.py
**V1 Path:** `state_log.py` (15609 bytes)  
**V2 Path:** `state_log.py` (adapt existing)  
**Type:** State Log  
**Status:** Adapt existing file  
**Notes:** Contains state logging utilities. Must be adapted for V2

---

## download_assets.py
**V1 Path:** `download_assets.py` (2261 bytes)  
**V2 Path:** `download_assets.py` (adapt existing)  
**Type:** Asset Downloader  
**Status:** Adapt existing file  
**Notes:** Contains asset download utilities. Must be adapted for V2

---

## generate_icons.py
**V1 Path:** `generate_icons.py` (6834 bytes)  
**V2 Path:** `generate_icons.py` (adapt existing)  
**Type:** Icon Generator  
**Status:** Adapt existing file  
**Notes:** Contains icon generation utilities. Must be adapted for V2

---

# ROOT DOCUMENTATION

## README.md
**V1 Path:** `README.md` (6046 bytes)  
**V2 Path:** `README.md` (adapt existing)  
**Type:** Documentation  
**Status:** Adapt existing file  
**Notes:** Contains README documentation. Must be adapted for V2

---

## docs/
**V1 Path:** `docs/` (4 items)  
**V2 Path:** `docs/` (adapt existing)  
**Type:** Documentation  
**Status:** Adapt existing directory  
**Notes:** Contains documentation files. Must be adapted for V2

---

# ROOT TESTS

## tests/
**V1 Path:** `tests/` (12 items)  
**V2 Path:** `tests/` (adapt existing)  
**Type:** Tests  
**Status:** Adapt existing directory  
**Notes:** Contains test files. Must be adapted for V2

---

## run_tests.py
**V1 Path:** `run_tests.py` (605 bytes)  
**V2 Path:** `run_tests.py` (adapt existing)  
**Type:** Test Runner  
**Status:** Adapt existing file  
**Notes:** Contains test runner script. Must be adapted for V2

---

# ROOT BUILD

## .pyinstaller_build/
**V1 Path:** `.pyinstaller_build/` (0 items)  
**V2 Path:** `.pyinstaller_build/` (adapt existing)  
**Type:** Build Directory  
**Status:** Adapt existing directory  
**Notes:** Contains PyInstaller build files. Must be adapted for V2

---

## LanChat.spec
**V1 Path:** `LanChat.spec` (955 bytes)  
**V2 Path:** `LanChat.spec` (adapt existing)  
**Type:** PyInstaller Spec  
**Status:** Adapt existing file  
**Notes:** Contains PyInstaller spec file for LanChat. Must be adapted for V2

---

## Nexus.spec
**V1 Path:** `Nexus.spec` (955 bytes)  
**V2 Path:** `Nexus.spec` (adapt existing)  
**Type:** PyInstaller Spec  
**Status:** Adapt existing file  
**Notes:** Contains PyInstaller spec file for Nexus. Must be adapted for V2

---

## LanChat.exe
**V1 Path:** `LanChat.exe` (18894798 bytes)  
**V2 Path:** `LanChat.exe` (new file)  
**Type:** Executable  
**Status:** Build after migration  
**Notes:** LanChat executable (built after migration)

---

## Nexus.exe
**V1 Path:** `Nexus.exe` (19540025 bytes)  
**V2 Path:** `Nexus.exe` (new file)  
**Type:** Executable  
**Status:** Build after migration  
**Notes:** Nexus executable (built after migration)

---

# ROOT GITHUB

## .github/
**V1 Path:** `.github/` (2 items)  
**V2 Path:** `.github/` (adapt existing)  
**Type:** GitHub Configuration  
**Status:** Adapt existing directory  
**Notes:** Contains GitHub workflows. Must be adapted for V2

---

## .gitignore
**V1 Path:** `.gitignore` (229 bytes)  
**V2 Path:** `.gitignore` (adapt existing)  
**Type:** Git Ignore  
**Status:** Adapt existing file  
**Notes:** Contains git ignore rules. Must be adapted for V2

---

## .gitattributes
**V1 Path:** `.gitattributes`  
**V2 Path:** `.gitattributes` (adapt existing)  
**Type:** Git Attributes  
**Status:** Adapt existing file  
**Notes:** Contains git attributes. Must be adapted for V2

---

# ROOT CLOUD

## cloud-server/
**V1 Path:** `cloud-server/` (1 items)  
**V2 Path:** `cloud-server/` (adapt existing)  
**Type:** Cloud Server  
**Status:** Adapt existing directory  
**Notes:** Contains cloud server files. Must be adapted for V2

---

# ROOT UPLOADS

## uploads/
**V1 Path:** `uploads/` (0 items)  
**V2 Path:** `uploads/` (adapt existing)  
**Type:** Upload Directory  
**Status:** Adapt existing directory  
**Notes:** Contains uploaded files. Must be adapted for V2

---

# SUMMARY

**Total Files Mapped:** ~85  
**New Files Required:** ~60  
**Files to Replace:** 3  
**Files to Adapt:** ~20  
**Directories to Create:** ~15  
**Directories to Adapt:** ~10

**Migration Order:**
1. Root configuration files (config.py, events.py)
2. Backend core files (state.py, db.py)
3. Backend routes files (all routes/)
4. Backend events files (events/)
5. Frontend core files (core/)
6. Frontend features files (features/)
7. Frontend UI files (ui/)
8. Frontend assets (icons, wallpaper, logo)
9. Frontend PWA files (manifest.json, service-worker.js)
10. Frontend emoji files (emoji-picker.js, emoji-data.json)
11. Root launcher files (launcher.py, ngrok_manager.py)
12. Root script files (start.bat, stop.bat, etc.)
13. Root utility files (config_manager.py, controller.py, etc.)
14. Root documentation files (README.md, docs/)
15. Root test files (tests/, run_tests.py)
16. Root build files (.pyinstaller_build/, *.spec)
17. Root GitHub files (.github/, .gitignore, .gitattributes)

**Critical Files:**
- config.py → backend/config.py (foundation)
- state.py → backend/core/state.py (foundation)
- events.py → backend/events.py (foundation)
- db.py → backend/db.py (foundation)
- templates/index.html → frontend/index.html (UI)
- static/style.css → frontend/style.css (UI)
- launcher.py → launcher.py (launcher)

**High-Risk Files:**
- state.py → backend/core/state.py (complex state management)
- routes/socket_auth.py → backend/routes/socket_auth.py (authentication)
- routes/socket_messages.py → backend/routes/socket_messages.py (messaging)
- routes/socket_rooms.py → backend/routes/socket_rooms.py (rooms)
- routes/socket_webrtc.py → backend/routes/socket_webrtc.py (WebRTC)
- static/core/encryption.js → frontend/core/encryption.js (encryption)
- launcher.py → launcher.py (launcher)
