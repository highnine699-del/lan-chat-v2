# LAN CHAT V2 MIGRATION BACKLOG

**Generated:** May 30, 2026  
**V1 Location:** `c:\Users\AY ADVANCE TECH\Documents\local-whatsapp\lan-chat-final`  
**V2 Location:** `c:\Users\AY ADVANCE TECH\Documents\lan-chat-v2`

---

# EXECUTIVE SUMMARY

This document provides a prioritized migration backlog with task IDs, descriptions, dependencies, risk levels, estimated effort, and wave assignments. This is the execution board for the migration project.

**Total Tasks:** 85  
**Total Waves:** 17  
**Critical Path Tasks:** 35  
**Parallel Tasks:** 50  
**Estimated Total Effort:** 8-12 weeks

---

# WAVE 1: FOUNDATION (Week 1-2)

## TASK-001: Config System Migration
**Task ID:** TASK-001  
**Feature:** Config System  
**Description:** Migrate config.py to backend/config.py with all V1 configuration constants, environment variable bindings, Socket.IO settings, file upload limits, chat limits, spam limits, security settings, room settings, ephemeral settings, TURN/STUN settings  
**Dependencies:** None  
**Risk:** Low  
**Estimated Effort:** 2 days  
**Wave:** 1  
**Priority:** Critical  
**Status:** Pending  
**Files:** config.py → backend/config.py  
**Verification:** All config constants accessible, environment variables properly bound, default values match V1  
**Rollback:** Delete backend/config.py  

---

## TASK-002: Event Schema Migration
**Task ID:** TASK-002  
**Feature:** Event Schema  
**Description:** Migrate events.py to backend/events.py with EventSchema class, event registry (_REGISTRY), validation functions (get, all_events, validate_payload), all V1 event registrations  
**Dependencies:** None  
**Risk:** Low  
**Estimated Effort:** 2 days  
**Wave:** 1  
**Priority:** Critical  
**Status:** Pending  
**Files:** events.py → backend/events.py  
**Verification:** All V1 events registered, validation works for each event type, event metadata correct  
**Rollback:** Delete backend/events.py  

---

## TASK-003: Database Schema Adaptation
**Task ID:** TASK-003  
**Feature:** Database Schema Adaptation  
**Description:** Adapt backend/db.py to V1's schema: add tables (public_keys, shadow_muted, spam_tracker, upload_counts, ip_connections, active_sessions, analytics, message_votes, join_tokens), add columns to users table (username, tag, display, uid, color, joined_at, msg_count, is_server_admin, persona, presence, last_message, last_message_time, spam_count, room_id), add columns to rooms table (visibility, password, creator_sid, members, admins, ttl, messages, is_frozen, delete_timer), add indexes for performance (sid_map, uid_sessions, message_history), create migration script  
**Dependencies:** TASK-001  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 1  
**Priority:** Critical  
**Status:** Pending  
**Files:** state.py → backend/db.py  
**Verification:** All V1 state structures represented in database, foreign keys properly defined, indexes created, migration script works without data loss  
**Rollback:** Restore original backend/db.py from git  

---

## TASK-004: State Management Migration
**Task ID:** TASK-004  
**Feature:** State Management  
**Description:** Replace backend/core/state.py with V1's identity authority hierarchy: users dict, user_state proxy, sid_map, uid_sessions, active_sessions, session_tokens, public_keys, message_history, private_history, rooms dict, shadow_muted, spam_tracker, upload_counts, ip_connections, analytics, message_votes, join_tokens, all accessor functions, cleanup worker  
**Dependencies:** TASK-001, TASK-003  
**Risk:** High  
**Estimated Effort:** 4 days  
**Wave:** 1  
**Priority:** Critical  
**Status:** Pending  
**Files:** state.py → backend/core/state.py  
**Verification:** All V1 state structures present, identity authority hierarchy works, accessor functions work correctly, cleanup worker runs without errors  
**Rollback:** Restore original backend/core/state.py from git  

---

# WAVE 2: CORE INFRASTRUCTURE (Week 3)

## TASK-005: HTTP Routes Migration
**Task ID:** TASK-005  
**Feature:** HTTP Routes  
**Description:** Migrate routes/http.py to backend/routes/http.py with GET / (serve SPA), GET /uploads/<name> (serve uploaded files), GET /ice-config (WebRTC ICE/TURN configuration), POST /upload (file upload), security headers (CSP, HSTS, X-Frame-Options, etc.), trusted proxy support, file validation (MIME types, size limits), upload rate limiting. Adapt for FastAPI  
**Dependencies:** TASK-001, TASK-004  
**Risk:** Medium  
**Estimated Effort:** 3 days  
**Wave:** 2  
**Priority:** Critical  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** All HTTP routes accessible, security headers present, file upload/download works, ICE config returns correct TURN/STUN servers  
**Rollback:** Delete backend/routes/ directory  

---

## TASK-006: Socket.IO Base Migration
**Task ID:** TASK-006  
**Feature:** Socket.IO Base  
**Description:** Adapt backend/socket_manager.py with V1's Socket.IO configuration (max_http_buffer_size, ping_timeout, ping_interval), template integrity check, PID file handling, ngrok browser-warning bypass, error handlers (413, 404), startup logging. Adapt for FastAPI  
**Dependencies:** TASK-001  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 2  
**Priority:** Critical  
**Status:** Pending  
**Files:** routes/__init__.py, server.py → backend/socket_manager.py  
**Verification:** Socket.IO connects successfully, configuration matches V1, error handlers work, logging works  
**Rollback:** Restore original backend/socket_manager.py from git  

---

## TASK-007: Rate Limiting Migration
**Task ID:** TASK-007  
**Feature:** Rate Limiting  
**Description:** Migrate routes/socket_rate_limit.py to backend/routes/socket_rate_limit.py with _check_join_rate (IP-based join limiting), _check_signal_rate (WebRTC signal limiting), _get_client_ip (with trusted proxy support), _uid_last_kick (kick cooldown), _UID_KICK_COOLDOWN constant, _require_member (room membership check)  
**Dependencies:** TASK-001, TASK-004  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 2  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_rate_limit.py → backend/routes/socket_rate_limit.py  
**Verification:** Join rate limiting works, signal rate limiting works, IP detection works with/without trusted proxy, kick cooldown works  
**Rollback:** Delete backend/routes/socket_rate_limit.py  

---

# WAVE 3: AUTHENTICATION & PRESENCE (Week 4)

## TASK-008: Authentication System Migration
**Task ID:** TASK-008  
**Feature:** Authentication System  
**Description:** Migrate routes/socket_auth.py to backend/routes/socket_auth.py with handle_connect (connection validation), handle_join (username/tag registration), username/tag generation (generate_tag, unique_username), session token issuance (issue_session_token), session token verification (verify_session_token), server password validation, admin password validation, PUBLIC_MODE enforcement, join rate limiting integration, IP connection limiting, UID generation and tracking, identity registration (register_identity), identity unregistration (unregister_identity), session registration (register_session), session updates (update_session_room), session teardown (mark_session_disconnected, remove_session), session lookup (get_session, find_session_by_uid), user list generation (get_user_list), next_color assignment  
**Dependencies:** TASK-001, TASK-004, TASK-007  
**Risk:** Medium  
**Estimated Effort:** 4 days  
**Wave:** 3  
**Priority:** Critical  
**Status:** Pending  
**Files:** routes/socket_auth.py → backend/routes/socket_auth.py  
**Verification:** Users can join with username/tag, session tokens work for reconnection, server password enforced, admin password grants admin rights, PUBLIC_MODE requires server password, join rate limiting works, IP connection limiting works, UID generation works  
**Rollback:** Delete backend/routes/socket_auth.py  

---

## TASK-009: Presence System Enhancement
**Task ID:** TASK-009  
**Feature:** Presence System  
**Description:** Enhance backend/core/presence.py with user color assignment, reputation system (reputation_label), persona switching, last message tracking, last seen tracking  
**Dependencies:** TASK-004, TASK-008  
**Risk:** Low  
**Estimated Effort:** 2 days  
**Wave:** 3  
**Priority:** High  
**Status:** Pending  
**Files:** state.py, routes/socket_auth.py → backend/core/presence.py  
**Verification:** User colors assigned correctly, reputation labels display correctly, persona switching works, last message tracking works, last seen tracking works  
**Rollback:** Restore original backend/core/presence.py from git  

---

## TASK-010: User Colors
**Task ID:** TASK-010  
**Feature:** User Colors  
**Description:** Add user color assignment to backend/core/presence.py and backend/config.py  
**Dependencies:** TASK-001, TASK-009  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 3  
**Priority:** Medium  
**Status:** Pending  
**Files:** state.py, config.py → backend/core/presence.py, backend/config.py  
**Verification:** User colors assigned correctly  
**Rollback:** Remove color assignment logic  

---

## TASK-011: Reputation Labels
**Task ID:** TASK-011  
**Feature:** Reputation Labels  
**Description:** Add reputation system to backend/core/presence.py  
**Dependencies:** TASK-004, TASK-009  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 3  
**Priority:** Low  
**Status:** Pending  
**Files:** state.py → backend/core/presence.py  
**Verification:** Reputation labels display correctly  
**Rollback:** Remove reputation logic  

---

# WAVE 4: MESSAGING CORE (Week 5)

## TASK-012: Global Chat Migration
**Task ID:** TASK-012  
**Feature:** Global Chat  
**Description:** Migrate routes/socket_messages.py to backend/routes/socket_messages.py with handle_message (message broadcasting), message dispatch (dispatch_message), global message history, message ID tracking, message ACK (tempId)  
**Dependencies:** TASK-002, TASK-004, TASK-009  
**Risk:** Low  
**Estimated Effort:** 3 days  
**Wave:** 4  
**Priority:** Critical  
**Status:** Pending  
**Files:** routes/socket_messages.py → backend/routes/socket_messages.py  
**Verification:** Messages broadcast to all users, message history maintained, message IDs unique, message ACK works, message length enforced  
**Rollback:** Delete backend/routes/socket_messages.py  

---

## TASK-013: Message Editing/Deletion
**Task ID:** TASK-013  
**Feature:** Message Editing/Deletion  
**Description:** Add handle_edit_message, handle_delete_message, message finding (_find_message), edit tracking (is_edited, edited_at), delete tracking (is_deleted) to backend/routes/socket_messages.py  
**Dependencies:** TASK-003, TASK-012  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 4  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_messages.py → backend/routes/socket_messages.py  
**Verification:** Messages can be edited, messages can be deleted, edit history tracked, delete history tracked  
**Rollback:** Remove edit/delete handlers  

---

## TASK-014: Reply System
**Task ID:** TASK-014  
**Feature:** Reply System  
**Description:** Add handle_reply_message, reply_to field, reply chain tracking to backend/routes/socket_messages.py  
**Dependencies:** TASK-003, TASK-012  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 4  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_messages.py → backend/routes/socket_messages.py  
**Verification:** Messages can be replied to, reply chains tracked, reply context displayed  
**Rollback:** Remove reply handlers  

---

## TASK-015: Message Status Tracking
**Task ID:** TASK-015  
**Feature:** Message Status Tracking  
**Description:** Add message delivery status, message read status, read receipts to backend/routes/socket_messages.py  
**Dependencies:** TASK-003, TASK-012  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 4  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_messages.py → backend/routes/socket_messages.py  
**Verification:** Delivery status tracked, read status tracked, read receipts work  
**Rollback:** Remove status tracking  

---

## TASK-016: Typing Indicators
**Task ID:** TASK-016  
**Feature:** Typing Indicators  
**Description:** Add handle_typing, typing events broadcast, typing timeout to backend/routes/socket_messages.py  
**Dependencies:** TASK-004, TASK-012  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 4  
**Priority:** Medium  
**Status:** Pending  
**Files:** routes/socket_messages.py → backend/routes/socket_messages.py  
**Verification:** Typing indicators broadcast, typing timeout works  
**Rollback:** Remove typing handlers  

---

# WAVE 5: SPAM PROTECTION (Week 5-6)

## TASK-017: Spam Protection
**Task ID:** TASK-017  
**Feature:** Spam Protection  
**Description:** Create backend/core/spam.py with check_smart_spam, cooldown_remaining, spam_tracker integration, shadow mute detection, repeat message detection. Integrate with backend/routes/socket_messages.py  
**Dependencies:** TASK-001, TASK-004, TASK-012  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 5  
**Priority:** High  
**Status:** Pending  
**Files:** state.py, routes/socket_messages.py → backend/core/spam.py, backend/routes/socket_messages.py  
**Verification:** Smart spam detection works, cooldown notifications sent, shadow mute applied, repeat messages blocked  
**Rollback:** Delete backend/core/spam.py, remove spam checks  

---

## TASK-018: Vote-to-Hide
**Task ID:** TASK-018  
**Feature:** Vote-to-Hide  
**Description:** Add handle_vote_hide, message_votes tracking, HIDE_VOTE_THRESHOLD check to backend/routes/socket_messages.py  
**Dependencies:** TASK-003, TASK-012  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 5  
**Priority:** Medium  
**Status:** Pending  
**Files:** routes/socket_messages.py → backend/routes/socket_messages.py  
**Verification:** Users can vote to hide, threshold enforced, messages hidden when threshold reached  
**Rollback:** Remove vote handlers  

---

## TASK-019: Message Length Limits
**Task ID:** TASK-019  
**Feature:** Message Length Limits  
**Description:** Add message length validation, MAX_MESSAGE_LEN enforcement to backend/routes/socket_messages.py  
**Dependencies:** TASK-001, TASK-012  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 5  
**Priority:** High  
**Status:** Pending  
**Files:** config.py, routes/socket_messages.py → backend/config.py, backend/routes/socket_messages.py  
**Verification:** Message length enforced, error returned for oversized messages  
**Rollback:** Remove length validation  

---

# WAVE 6: ROOMS (Week 6-7)

## TASK-020: Room System Migration
**Task ID:** TASK-020  
**Feature:** Room System  
**Description:** Migrate routes/socket_rooms.py to backend/routes/socket_rooms.py with handle_room_create, handle_room_join, handle_room_leave, handle_room_list, room password protection, room member list, room history. Enhance backend/core/rooms.py with V1's room schema  
**Dependencies:** TASK-001, TASK-004, TASK-009  
**Risk:** High  
**Estimated Effort:** 4 days  
**Wave:** 6  
**Priority:** Critical  
**Status:** Pending  
**Files:** routes/socket_rooms.py, state.py → backend/routes/socket_rooms.py, backend/core/rooms.py  
**Verification:** Rooms can be created, rooms can be joined/left, room list works, room passwords work, room members tracked, room history maintained  
**Rollback:** Delete backend/routes/socket_rooms.py, restore original backend/core/rooms.py  

---

## TASK-021: Room Admin System
**Task ID:** TASK-021  
**Feature:** Room Admin System  
**Description:** Add room creator tracking, room moderator assignment, is_room_admin check, room_member_list to backend/routes/socket_rooms.py and backend/core/rooms.py  
**Dependencies:** TASK-004, TASK-020  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 6  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_rooms.py, state.py → backend/routes/socket_rooms.py, backend/core/rooms.py  
**Verification:** Room creator tracked, moderators assigned, admin checks work, member list accurate  
**Rollback:** Remove admin tracking  

---

## TASK-022: Ephemeral Rooms
**Task ID:** TASK-022  
**Feature:** Ephemeral Rooms  
**Description:** Add TTL-based room deletion, schedule_room_delete, cancel_room_delete, ROOM_IDLE_GRACE_S, EPHEMERAL_TTLS to backend/routes/socket_rooms.py and backend/core/rooms.py  
**Dependencies:** TASK-001, TASK-020  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 6  
**Priority:** Medium  
**Status:** Pending  
**Files:** state.py, routes/socket_rooms.py, config.py → backend/routes/socket_rooms.py, backend/core/rooms.py, backend/config.py  
**Verification:** Ephemeral rooms auto-delete, TTL works correctly, idle grace period works  
**Rollback:** Remove ephemeral logic  

---

## TASK-023: Room Auto-Delete on Empty
**Task ID:** TASK-023  
**Feature:** Room Auto-Delete on Empty  
**Description:** Add room auto-delete on empty to backend/routes/socket_rooms.py and backend/core/rooms.py  
**Dependencies:** TASK-004, TASK-020  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 6  
**Priority:** Medium  
**Status:** Pending  
**Files:** state.py, routes/socket_rooms.py → backend/routes/socket_rooms.py, backend/core/rooms.py  
**Verification:** Rooms auto-delete when empty  
**Rollback:** Remove auto-delete logic  

---

## TASK-024: Room Approval System
**Task ID:** TASK-024  
**Feature:** Room Approval System  
**Description:** Add room approval system with join_tokens to backend/routes/socket_rooms.py and backend/core/state.py  
**Dependencies:** TASK-001, TASK-003, TASK-020  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 6  
**Priority:** Medium  
**Status:** Pending  
**Files:** routes/socket_rooms.py, state.py → backend/routes/socket_rooms.py, backend/core/state.py  
**Verification:** Room approval works, join tokens work  
**Rollback:** Remove approval logic  

---

# WAVE 7: ENCRYPTION (Week 7)

## TASK-025: ECDH Key Generation
**Task ID:** TASK-025  
**Feature:** ECDH Key Generation  
**Description:** Migrate static/core/encryption.js to frontend/core/encryption.js with ECDH key generation (Web Crypto API)  
**Dependencies:** TASK-004  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 7  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/core/encryption.js → frontend/core/encryption.js  
**Verification:** ECDH keys generated correctly  
**Rollback:** Delete frontend/core/encryption.js  

---

## TASK-026: AES-GCM Encryption
**Task ID:** TASK-026  
**Feature:** AES-GCM Encryption  
**Description:** Add AES-GCM encryption and decryption to frontend/core/encryption.js  
**Dependencies:** TASK-025  
**Risk:** High  
**Estimated Effort:** 2 days  
**Wave:** 7  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/core/encryption.js → frontend/core/encryption.js  
**Verification:** Messages encrypted with AES-GCM, messages decrypted correctly  
**Rollback:** Remove AES-GCM logic  

---

## TASK-027: Public Key Exchange
**Task ID:** TASK-027  
**Feature:** Public Key Exchange  
**Description:** Add handle_public_key, public key storage, public key lookup, public key changes broadcast to backend/routes/socket_auth.py and backend/core/state.py  
**Dependencies:** TASK-004, TASK-025  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 7  
**Priority:** Critical  
**Status:** Pending  
**Files:** state.py, routes/socket_auth.py → backend/routes/socket_auth.py, backend/core/state.py  
**Verification:** Public keys stored, public keys retrieved, public key changes broadcast  
**Rollback:** Remove public key handlers  

---

## TASK-028: E2E Encryption for DMs
**Task ID:** TASK-028  
**Feature:** E2E Encryption for DMs  
**Description:** Add E2E encryption for DMs to frontend/core/encryption.js  
**Dependencies:** TASK-025, TASK-026, TASK-027  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 7  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/core/encryption.js → frontend/core/encryption.js  
**Verification:** DMs encrypted end-to-end, DMs decrypted correctly  
**Rollback:** Remove DM encryption logic  

---

## TASK-029: E2E Encryption for Rooms
**Task ID:** TASK-029  
**Feature:** E2E Encryption for Rooms  
**Description:** Add E2E encryption for rooms to frontend/core/encryption.js  
**Dependencies:** TASK-025, TASK-026, TASK-027  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 7  
**Priority:** High  
**Status:** Pending  
**Files:** static/core/encryption.js → frontend/core/encryption.js  
**Verification:** Room messages encrypted end-to-end, room messages decrypted correctly  
**Rollback:** Remove room encryption logic  

---

# WAVE 8: WEBRTC CALLS (Week 8)

## TASK-030: WebRTC Signaling
**Task ID:** TASK-030  
**Feature:** WebRTC Signaling  
**Description:** Migrate routes/socket_webrtc.py to backend/routes/socket_webrtc.py with handle_call_signal, offer/answer/ICE exchange, signal rate limiting, signal size validation  
**Dependencies:** TASK-004, TASK-007  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 8  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_webrtc.py → backend/routes/socket_webrtc.py  
**Verification:** WebRTC signals exchanged, rate limiting works, size validation works  
**Rollback:** Delete backend/routes/socket_webrtc.py  

---

## TASK-031: Call Session Management
**Task ID:** TASK-031  
**Feature:** Call Session Management  
**Description:** Create backend/core/calls.py with create_call_session, get_call_session_id, invalidate_call_session, join_call, leave_call, teardown_call, _call_key_for_room  
**Dependencies:** TASK-004  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 8  
**Priority:** High  
**Status:** Pending  
**Files:** state.py, routes/socket_webrtc.py → backend/core/calls.py  
**Verification:** Call sessions created, call sessions tracked, call sessions torn down  
**Rollback:** Delete backend/core/calls.py  

---

## TASK-032: Call Phase Management
**Task ID:** TASK-032  
**Feature:** Call Phase Management  
**Description:** Add advance_call_phase, get_call_phase, reset_call_phase, mark_call_active, phase states (offer, answer, connected) to backend/core/calls.py  
**Dependencies:** TASK-031  
**Risk:** High  
**Estimated Effort:** 2 days  
**Wave:** 8  
**Priority:** High  
**Status:** Pending  
**Files:** state.py, routes/socket_webrtc.py → backend/core/calls.py  
**Verification:** Call phases advance correctly, phase state tracked, active calls marked  
**Rollback:** Remove phase management  

---

## TASK-033: Call Tombstone
**Task ID:** TASK-033  
**Feature:** Call Tombstone  
**Description:** Add write_call_tombstone, find_call_tombstone, consume_call_tombstone, call reconnection logic to backend/core/calls.py and backend/core/state.py  
**Dependencies:** TASK-031  
**Risk:** High  
**Estimated Effort:** 2 days  
**Wave:** 8  
**Priority:** High  
**Status:** Pending  
**Files:** state.py, routes/socket_webrtc.py → backend/core/calls.py, backend/core/state.py  
**Verification:** Call tombstones written, call tombstones found, call reconnection works  
**Rollback:** Remove tombstone logic  

---

## TASK-034: Offer Lock
**Task ID:** TASK-034  
**Feature:** Offer Lock  
**Description:** Add is_offer_locked, set_offer_lock, clear_offer_lock, double call prevention to backend/core/calls.py and backend/core/state.py  
**Dependencies:** TASK-031  
**Risk:** Medium  
**Estimated Effort:** 1 day  
**Wave:** 8  
**Priority:** Medium  
**Status:** Pending  
**Files:** state.py, routes/socket_webrtc.py → backend/core/calls.py, backend/core/state.py  
**Verification:** Offer lock works, double calls prevented  
**Rollback:** Remove offer lock  

---

## TASK-035: ICE Config
**Task ID:** TASK-035  
**Feature:** ICE Config  
**Description:** Add _build_ice_servers, STUN server (stun.l.google.com:19302), TURN server support, /ice-config endpoint, TURN credentials to backend/routes/http.py and backend/config.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 8  
**Priority:** Medium  
**Status:** Pending  
**Files:** routes/http.py, config.py → backend/routes/http.py, backend/config.py  
**Verification:** ICE config returns STUN servers, ICE config returns TURN servers, TURN credentials valid  
**Rollback:** Remove ICE config endpoint  

---

# WAVE 9: ADMIN TOOLS (Week 9)

## TASK-036: Admin Kick
**Task ID:** TASK-036  
**Feature:** Admin Kick  
**Description:** Migrate routes/socket_admin.py to backend/routes/socket_admin.py with handle_kick, room admin check, user removal from room, notification to kicked user, notification to room  
**Dependencies:** TASK-004, TASK-020  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 9  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_admin.py → backend/routes/socket_admin.py  
**Verification:** Admins can kick users, non-admins cannot kick, kicked user notified, room notified  
**Rollback:** Delete backend/routes/socket_admin.py  

---

## TASK-037: Admin Freeze
**Task ID:** TASK-037  
**Feature:** Admin Freeze  
**Description:** Add handle_freeze, room freeze state, message blocking in frozen rooms, unfreeze to backend/routes/socket_admin.py  
**Dependencies:** TASK-004, TASK-020  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 9  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_admin.py → backend/routes/socket_admin.py  
**Verification:** Admins can freeze rooms, messages blocked in frozen rooms, rooms can be unfrozen  
**Rollback:** Remove freeze handlers  

---

## TASK-038: Shadow Mute
**Task ID:** TASK-038  
**Feature:** Shadow Mute  
**Description:** Add handle_shadow_mute, shadow_mute tracking, shadow_mute duration, silent message dropping to backend/routes/socket_admin.py and backend/core/state.py  
**Dependencies:** TASK-004, TASK-017  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 9  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_admin.py, state.py → backend/routes/socket_admin.py, backend/core/state.py  
**Verification:** Admins can shadow mute, shadow-muted messages dropped, shadow mute expires  
**Rollback:** Remove shadow mute handlers  

---

## TASK-039: Room Admin Permissions
**Task ID:** TASK-039  
**Feature:** Room Admin Permissions  
**Description:** Add room admin permissions to backend/routes/socket_rooms.py and backend/core/rooms.py  
**Dependencies:** TASK-004, TASK-020, TASK-021  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 9  
**Priority:** High  
**Status:** Pending  
**Files:** routes/socket_rooms.py, state.py → backend/routes/socket_rooms.py, backend/core/rooms.py  
**Verification:** Room admin permissions work correctly  
**Rollback:** Remove admin permissions logic  

---

# WAVE 10: FILE SHARING (Week 10)

## TASK-040: File Upload
**Task ID:** TASK-040  
**Feature:** File Upload  
**Description:** Add POST /upload, multipart form handling, file validation (MIME type, size), sanitize_filename, upload rate limiting, file storage in UPLOAD_FOLDER to backend/routes/http.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 10  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** Files upload successfully, invalid files rejected, oversized files rejected, upload rate limiting works  
**Rollback:** Remove upload handler  

---

## TASK-041: File Download
**Task ID:** TASK-041  
**Feature:** File Download  
**Description:** Add GET /uploads/<name>, MIME type detection, inline vs attachment disposition, dangerous MIME types blocking (SVG) to backend/routes/http.py  
**Dependencies:** TASK-005  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 10  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** Files download successfully, MIME types correct, dangerous files blocked  
**Rollback:** Remove download handler  

---

## TASK-042: File Validation
**Task ID:** TASK-042  
**Feature:** File Validation  
**Description:** Add MIME type whitelist, file size validation, filename sanitization, virus scanning (optional) to backend/routes/http.py  
**Dependencies:** TASK-001  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 10  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** Invalid MIME types rejected, oversized files rejected, dangerous filenames sanitized  
**Rollback:** Remove validation logic  

---

## TASK-043: Media Support
**Task ID:** TASK-043  
**Feature:** Media Support  
**Description:** Add media support (images, audio, video) to backend/routes/http.py  
**Dependencies:** TASK-005  
**Risk:** Medium  
**Estimated Effort:** 1 day  
**Wave:** 10  
**Priority:** Medium  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** Media files display correctly  
**Rollback:** Remove media support  

---

# WAVE 11: VOICE MESSAGES (Week 10-11)

## TASK-044: Voice Recording
**Task ID:** TASK-044  
**Feature:** Voice Recording  
**Description:** Migrate static/features/voiceMessages/voiceMessages.js to frontend/features/voiceMessages/voiceMessages.js with MediaRecorder integration, audio recording  
**Dependencies:** None  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 11  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/features/voiceMessages/voiceMessages.js → frontend/features/voiceMessages/voiceMessages.js  
**Verification:** Voice recording works  
**Rollback:** Delete frontend/features/voiceMessages/  

---

## TASK-045: Voice Playback
**Task ID:** TASK-045  
**Feature:** Voice Playback  
**Description:** Add voice playback to frontend/features/voiceMessages/voiceMessages.js  
**Dependencies:** TASK-044  
**Risk:** High  
**Estimated Effort:** 2 days  
**Wave:** 11  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/features/voiceMessages/voiceMessages.js → frontend/features/voiceMessages/voiceMessages.js  
**Verification:** Voice playback works  
**Rollback:** Remove playback logic  

---

## TASK-046: Waveform Display
**Task ID:** TASK-046  
**Feature:** Waveform Display  
**Description:** Add waveform display to frontend/features/voiceMessages/voiceMessages.js  
**Dependencies:** TASK-044  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 11  
**Priority:** Low  
**Status:** Pending  
**Files:** static/features/voiceMessages/voiceMessages.js → frontend/features/voiceMessages/voiceMessages.js  
**Verification:** Waveform displays correctly  
**Rollback:** Remove waveform logic  

---

# WAVE 12: REACTIONS (Week 11)

## TASK-047: Emoji Reactions
**Task ID:** TASK-047  
**Feature:** Emoji Reactions  
**Description:** Migrate static/features/reactions/reactions.js to frontend/features/reactions/reactions.js with emoji reaction UI, reaction sending, reaction display  
**Dependencies:** TASK-003, TASK-012  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 12  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/features/reactions/reactions.js → frontend/features/reactions/reactions.js  
**Verification:** Reaction UI displays, reactions send correctly, reactions display correctly  
**Rollback:** Delete frontend/features/reactions/  

---

# WAVE 13: EMOJI PICKER (Week 11-12)

## TASK-048: Emoji Picker (Bundled)
**Task ID:** TASK-048  
**Feature:** Emoji Picker (Bundled)  
**Description:** Migrate static/emoji-picker.js, static/emoji-data.json, static/emoji-picker-picker.js to frontend/  
**Dependencies:** None  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 13  
**Priority:** Low  
**Status:** Pending  
**Files:** static/emoji-picker.js, static/emoji-data.json, static/emoji-picker-picker.js → frontend/  
**Verification:** Emoji picker displays, emoji selection works, offline support works  
**Rollback:** Delete frontend/emoji-picker files  

---

## TASK-049: Offline Emoji Support
**Task ID:** TASK-049  
**Feature:** Offline Emoji Support  
**Description:** Ensure offline emoji support with emoji-data.json  
**Dependencies:** TASK-048  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 13  
**Priority:** Low  
**Status:** Pending  
**Files:** static/emoji-picker.js, static/emoji-data.json → frontend/  
**Verification:** Offline emoji support works  
**Rollback:** Remove offline support  

---

# WAVE 14: SECURITY HEADERS (Week 12)

## TASK-050: CSP Headers
**Task ID:** TASK-050  
**Feature:** CSP Headers  
**Description:** Add CSP header to backend/routes/http.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 14  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** CSP header present  
**Rollback:** Remove CSP header  

---

## TASK-051: HSTS Headers
**Task ID:** TASK-051  
**Feature:** HSTS Headers  
**Description:** Add HSTS header to backend/routes/http.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 14  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** HSTS header present  
**Rollback:** Remove HSTS header  

---

## TASK-052: X-Frame-Options
**Task ID:** TASK-052  
**Feature:** X-Frame-Options  
**Description:** Add X-Frame-Options header to backend/routes/http.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 14  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** X-Frame-Options header present  
**Rollback:** Remove X-Frame-Options header  

---

## TASK-053: X-Content-Type-Options
**Task ID:** TASK-053  
**Feature:** X-Content-Type-Options  
**Description:** Add X-Content-Type-Options header to backend/routes/http.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 14  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** X-Content-Type-Options header present  
**Rollback:** Remove X-Content-Type-Options header  

---

## TASK-054: Referrer-Policy
**Task ID:** TASK-054  
**Feature:** Referrer-Policy  
**Description:** Add Referrer-Policy header to backend/routes/http.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 14  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** Referrer-Policy header present  
**Rollback:** Remove Referrer-Policy header  

---

## TASK-055: X-XSS-Protection
**Task ID:** TASK-055  
**Feature:** X-XSS-Protection  
**Description:** Add X-XSS-Protection header to backend/routes/http.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 14  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py → backend/routes/http.py  
**Verification:** X-XSS-Protection header present  
**Rollback:** Remove X-XSS-Protection header  

---

## TASK-056: Trusted Proxy Support
**Task ID:** TASK-056  
**Feature:** Trusted Proxy Support  
**Description:** Add trusted proxy support, X-Forwarded-For handling, IP spoofing protection to backend/routes/http.py and backend/config.py  
**Dependencies:** TASK-001, TASK-005  
**Risk:** Low  
**Estimated Effort:** 2 days  
**Wave:** 14  
**Priority:** High  
**Status:** Pending  
**Files:** routes/http.py, config.py → backend/routes/http.py, backend/config.py  
**Verification:** Trusted proxy works correctly  
**Rollback:** Remove trusted proxy support  

---

# WAVE 15: PWA SUPPORT (Week 12-13)

## TASK-057: Manifest.json
**Task ID:** TASK-057  
**Feature:** Manifest.json  
**Description:** Migrate static/manifest.json to frontend/manifest.json  
**Dependencies:** None  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 15  
**Priority:** Low  
**Status:** Pending  
**Files:** static/manifest.json → frontend/manifest.json  
**Verification:** PWA installable  
**Rollback:** Delete frontend/manifest.json  

---

## TASK-058: Service Worker
**Task ID:** TASK-058  
**Feature:** Service Worker  
**Description:** Create frontend/service-worker.js with offline caching  
**Dependencies:** None  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 15  
**Priority:** Low  
**Status:** Pending  
**Files:** static/ → frontend/service-worker.js  
**Verification:** Offline caching works  
**Rollback:** Delete frontend/service-worker.js  

---

## TASK-059: App Icons
**Task ID:** TASK-059  
**Feature:** App Icons  
**Description:** Migrate static/icon-192.png, static/icon-512.png, static/icon.svg, static/icon.ico to frontend/  
**Dependencies:** None  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 15  
**Priority:** Low  
**Status:** Pending  
**Files:** static/icon-192.png, static/icon-512.png, static/icon.svg, static/icon.ico → frontend/  
**Verification:** App icons display correctly  
**Rollback:** Delete frontend/icon files  

---

## TASK-060: iOS Meta Tags
**Task ID:** TASK-060  
**Feature:** iOS Meta Tags  
**Description:** Add iOS meta tags to frontend/index.html  
**Dependencies:** None  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 15  
**Priority:** Low  
**Status:** Pending  
**Files:** templates/index.html → frontend/index.html  
**Verification:** iOS meta tags present  
**Rollback:** Remove iOS meta tags  

---

# WAVE 16: FRONTEND UI (Week 13-15)

## TASK-061: WhatsApp-Style UI
**Task ID:** TASK-061  
**Feature:** WhatsApp-Style UI  
**Description:** Replace frontend/index.html with V1's complete SPA (3670 lines) and create frontend/style.css (44012 bytes) with WhatsApp-style layout, sidebar navigation, chat area, input bar, user list panel  
**Dependencies:** All backend waves  
**Risk:** High  
**Estimated Effort:** 5 days  
**Wave:** 16  
**Priority:** Critical  
**Status:** Pending  
**Files:** templates/index.html, static/style.css → frontend/index.html, frontend/style.css  
**Verification:** UI matches V1 exactly, layout responsive, mobile works, all UI elements present  
**Rollback:** Restore original frontend/index.html  

---

## TASK-062: Modular Architecture
**Task ID:** TASK-062  
**Feature:** Modular Architecture  
**Description:** Create frontend modular architecture with frontend/init.js, frontend/core/, frontend/features/, frontend/ui/, frontend/ui/components/, frontend/ui/pages/  
**Dependencies:** None  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 16  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/init.js, static/core/, static/features/, static/ui/ → frontend/  
**Verification:** Modules load correctly, module dependencies resolved, no circular dependencies  
**Rollback:** Restore original frontend/ structure  

---

## TASK-063: Login Page
**Task ID:** TASK-063  
**Feature:** Login Page  
**Description:** Migrate static/ui/pages/LoginPage.js to frontend/ui/pages/LoginPage.js with username/tag input, server password input, admin password input, login validation, error handling  
**Dependencies:** TASK-008, TASK-062  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 16  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/ui/pages/LoginPage.js → frontend/ui/pages/LoginPage.js  
**Verification:** Login page displays, username/tag input works, passwords validated, errors displayed  
**Rollback:** Delete frontend/ui/pages/LoginPage.js  

---

## TASK-064: Chat Page
**Task ID:** TASK-064  
**Feature:** Chat Page  
**Description:** Migrate static/ui/pages/ChatPage.js to frontend/ui/pages/ChatPage.js with message list, message rendering, input bar, emoji picker integration, file upload integration, voice recording integration, typing indicators, user list  
**Dependencies:** TASK-012, TASK-016, TASK-040, TASK-044, TASK-048, TASK-062  
**Risk:** High  
**Estimated Effort:** 4 days  
**Wave:** 16  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/ui/pages/ChatPage.js → frontend/ui/pages/ChatPage.js  
**Verification:** Chat page displays, messages render correctly, input bar works, emoji picker works, file upload works, voice recording works, typing indicators work, user list displays  
**Rollback:** Delete frontend/ui/pages/ChatPage.js  

---

## TASK-065: Room Page
**Task ID:** TASK-065  
**Feature:** Room Page  
**Description:** Migrate static/ui/pages/RoomPage.js to frontend/ui/pages/RoomPage.js with room list, room creation, room joining, room settings, room member list, room admin controls  
**Dependencies:** TASK-020, TASK-062  
**Risk:** High  
**Estimated Effort:** 4 days  
**Wave:** 16  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/ui/pages/RoomPage.js → frontend/ui/pages/RoomPage.js  
**Verification:** Room page displays, room list works, room creation works, room joining works, room settings work, member list displays, admin controls work  
**Rollback:** Delete frontend/ui/pages/RoomPage.js  

---

## TASK-066: Call UI
**Task ID:** TASK-066  
**Feature:** Call UI  
**Description:** Migrate static/ui/pages/CallUI.js to frontend/ui/pages/CallUI.js with call controls (mute, video, hangup), video element, audio element, call status display, WebRTC integration  
**Dependencies:** TASK-030, TASK-062  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 16  
**Priority:** High  
**Status:** Pending  
**Files:** static/ui/pages/CallUI.js → frontend/ui/pages/CallUI.js  
**Verification:** Call UI displays, call controls work, video displays, audio works, call status accurate  
**Rollback:** Delete frontend/ui/pages/CallUI.js  

---

## TASK-067: Admin Page
**Task ID:** TASK-067  
**Feature:** Admin Page  
**Description:** Migrate static/ui/pages/AdminPage.js to frontend/ui/pages/AdminPage.js with user list, kick controls, freeze controls, shadow mute controls, room list, room controls  
**Dependencies:** TASK-036, TASK-037, TASK-038, TASK-062  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 16  
**Priority:** High  
**Status:** Pending  
**Files:** static/ui/pages/AdminPage.js → frontend/ui/pages/AdminPage.js  
**Verification:** Admin page displays, user list works, kick controls work, freeze controls work, shadow mute controls work, room list works, room controls work  
**Rollback:** Delete frontend/ui/pages/AdminPage.js  

---

## TASK-068: Sidebar Navigation
**Task ID:** TASK-068  
**Feature:** Sidebar Navigation  
**Description:** Migrate sidebar navigation to frontend/ with room list, user list  
**Dependencies:** TASK-020, TASK-062  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 16  
**Priority:** High  
**Status:** Pending  
**Files:** static/ → frontend/  
**Verification:** Sidebar navigation works  
**Rollback:** Remove sidebar logic  

---

## TASK-069: User List Panel
**Task ID:** TASK-069  
**Feature:** User List Panel  
**Description:** Migrate user list panel to frontend/ with online/offline status  
**Dependencies:** TASK-009, TASK-062  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 16  
**Priority:** High  
**Status:** Pending  
**Files:** static/ → frontend/  
**Verification:** User list panel works  
**Rollback:** Remove user list logic  

---

## TASK-070: Message Components
**Task ID:** TASK-070  
**Feature:** Message Components  
**Description:** Migrate static/ui/components/MessageItem.js to frontend/ui/components/MessageItem.js with message rendering, edit/delete controls, reply display, reactions display  
**Dependencies:** TASK-012, TASK-013, TASK-014, TASK-047, TASK-062  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 16  
**Priority:** High  
**Status:** Pending  
**Files:** static/ui/components/MessageItem.js → frontend/ui/components/MessageItem.js  
**Verification:** Message components render correctly  
**Rollback:** Delete frontend/ui/components/MessageItem.js  

---

## TASK-071: Input Bar
**Task ID:** TASK-071  
**Feature:** Input Bar  
**Description:** Migrate static/ui/components/InputBar.js to frontend/ui/components/InputBar.js with emoji picker, file upload, voice recording  
**Dependencies:** TASK-040, TASK-044, TASK-048, TASK-062  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 16  
**Priority:** High  
**Status:** Pending  
**Files:** static/ui/components/InputBar.js → frontend/ui/components/InputBar.js  
**Verification:** Input bar works correctly  
**Rollback:** Delete frontend/ui/components/InputBar.js  

---

## TASK-072: Modal System
**Task ID:** TASK-072  
**Feature:** Modal System  
**Description:** Migrate static/ui/components/Modal.js to frontend/ui/components/Modal.js  
**Dependencies:** TASK-062  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 16  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/ui/components/Modal.js → frontend/ui/components/Modal.js  
**Verification:** Modal system works  
**Rollback:** Delete frontend/ui/components/Modal.js  

---

## TASK-073: User Item Component
**Task ID:** TASK-073  
**Feature:** User Item Component  
**Description:** Migrate static/ui/components/UserItem.js to frontend/ui/components/UserItem.js with color, reputation label, online/offline status  
**Dependencies:** TASK-009, TASK-062  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 16  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/ui/components/UserItem.js → frontend/ui/components/UserItem.js  
**Verification:** User item component works  
**Rollback:** Delete frontend/ui/components/UserItem.js  

---

# WAVE 17: LAUNCHER (Week 15-16)

## TASK-074: NEXUS GUI Launcher
**Task ID:** TASK-074  
**Feature:** NEXUS GUI Launcher  
**Description:** Migrate launcher.py to launcher.py in root with tkinter GUI, dashboard stats, start/stop controls, browser launch, log panel, config section, ngrok controls, system tray, QR code display  
**Dependencies:** TASK-001  
**Risk:** High  
**Estimated Effort:** 5 days  
**Wave:** 17  
**Priority:** High  
**Status:** Pending  
**Files:** launcher.py → launcher.py  
**Verification:** Launcher opens successfully, dashboard stats display, start/stop works, browser launches, logs display, ngrok controls work, system tray works, QR code displays  
**Rollback:** Delete launcher.py  

---

## TASK-075: Ngrok Manager
**Task ID:** TASK-075  
**Feature:** Ngrok Manager  
**Description:** Migrate ngrok_manager.py to ngrok_manager.py in root with ngrok process management, ngrok URL detection, ngrok start/stop, ngrok authentication  
**Dependencies:** None  
**Risk:** High  
**Estimated Effort:** 3 days  
**Wave:** 17  
**Priority:** High  
**Status:** Pending  
**Files:** ngrok_manager.py → ngrok_manager.py  
**Verification:** Ngrok starts successfully, ngrok URL detected, ngrok stops successfully, ngrok authentication works  
**Rollback:** Delete ngrok_manager.py  

---

## TASK-076: Dashboard Stats
**Task ID:** TASK-076  
**Feature:** Dashboard Stats  
**Description:** Add dashboard stats (uptime, users, CPU, RAM) to launcher.py  
**Dependencies:** TASK-074  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 17  
**Priority:** Medium  
**Status:** Pending  
**Files:** launcher.py → launcher.py  
**Verification:** Dashboard stats display correctly  
**Rollback:** Remove dashboard stats  

---

## TASK-077: Start/Stop Controls
**Task ID:** TASK-077  
**Feature:** Start/Stop Controls  
**Description:** Add start/stop controls to launcher.py  
**Dependencies:** TASK-074  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 17  
**Priority:** High  
**Status:** Pending  
**Files:** launcher.py → launcher.py  
**Verification:** Start/stop controls work  
**Rollback:** Remove start/stop controls  

---

## TASK-078: Browser Launch
**Task ID:** TASK-078  
**Feature:** Browser Launch  
**Description:** Add browser launch to launcher.py  
**Dependencies:** TASK-074  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 17  
**Priority:** Medium  
**Status:** Pending  
**Files:** launcher.py → launcher.py  
**Verification:** Browser launches successfully  
**Rollback:** Remove browser launch  

---

## TASK-079: System Tray
**Task ID:** TASK-079  
**Feature:** System Tray  
**Description:** Add system tray to launcher.py  
**Dependencies:** TASK-074  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 17  
**Priority:** Medium  
**Status:** Pending  
**Files:** launcher.py → launcher.py  
**Verification:** System tray works  
**Rollback:** Remove system tray  

---

## TASK-080: QR Code Display
**Task ID:** TASK-080  
**Feature:** QR Code Display  
**Description:** Add QR code display to launcher.py  
**Dependencies:** TASK-074  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 17  
**Priority:** Low  
**Status:** Pending  
**Files:** launcher.py → launcher.py  
**Verification:** QR code displays correctly  
**Rollback:** Remove QR code display  

---

# WAVE 18: FRONTEND CORE MODULES (Week 16)

## TASK-081: Frontend Core Config
**Task ID:** TASK-081  
**Feature:** Frontend Core Config  
**Description:** Migrate static/core/config.js to frontend/core/config.js with frontend configuration, environment variable bindings  
**Dependencies:** TASK-001  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 18  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/core/config.js → frontend/core/config.js  
**Verification:** Frontend config works  
**Rollback:** Delete frontend/core/config.js  

---

## TASK-082: Frontend Event Bus
**Task ID:** TASK-082  
**Feature:** Frontend Event Bus  
**Description:** Migrate static/core/eventBus.js to frontend/core/eventBus.js with client-side event bus for component communication  
**Dependencies:** None  
**Risk:** Low  
**Estimated Effort:** 1 day  
**Wave:** 18  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/core/eventBus.js → frontend/core/eventBus.js  
**Verification:** Event bus works  
**Rollback:** Delete frontend/core/eventBus.js  

---

## TASK-083: Frontend Socket Client
**Task ID:** TASK-083  
**Feature:** Frontend Socket Client  
**Description:** Migrate static/core/socket.js to frontend/core/socket.js with Socket.IO client setup, connection management, event handlers, reconnection logic  
**Dependencies:** TASK-006  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 18  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/core/socket.js → frontend/core/socket.js  
**Verification:** Socket client works  
**Rollback:** Delete frontend/core/socket.js  

---

## TASK-084: Frontend State Management
**Task ID:** TASK-084  
**Feature:** Frontend State Management  
**Description:** Migrate static/core/state/ to frontend/core/state/ with client-side state management  
**Dependencies:** None  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 18  
**Priority:** Medium  
**Status:** Pending  
**Files:** static/core/state/ → frontend/core/state/  
**Verification:** Frontend state works  
**Rollback:** Delete frontend/core/state/  

---

## TASK-085: Frontend Init
**Task ID:** TASK-085  
**Feature:** Frontend Init  
**Description:** Migrate static/init.js to frontend/init.js with frontend initialization, module loading, entry point  
**Dependencies:** TASK-062, TASK-081, TASK-082, TASK-083, TASK-084  
**Risk:** Medium  
**Estimated Effort:** 2 days  
**Wave:** 18  
**Priority:** Critical  
**Status:** Pending  
**Files:** static/init.js → frontend/init.js  
**Verification:** Frontend initialization works  
**Rollback:** Delete frontend/init.js  

---

# SUMMARY STATISTICS

**Total Tasks:** 85  
**Total Waves:** 18  
**Critical Path Tasks:** 35  
**Parallel Tasks:** 50  
**Estimated Total Effort:** 8-12 weeks  

**Priority Distribution:**
- Critical: 25 tasks
- High: 35 tasks
- Medium: 20 tasks
- Low: 5 tasks

**Risk Distribution:**
- High Risk: 25 tasks
- Medium Risk: 45 tasks
- Low Risk: 15 tasks

**Effort Distribution:**
- 1 day: 15 tasks
- 2 days: 35 tasks
- 3 days: 20 tasks
- 4 days: 10 tasks
- 5 days: 5 tasks

**Wave Distribution:**
- Wave 1 (Foundation): 4 tasks (10 days)
- Wave 2 (Infrastructure): 3 tasks (7 days)
- Wave 3 (Authentication & Presence): 4 tasks (8 days)
- Wave 4 (Messaging Core): 5 tasks (10 days)
- Wave 5 (Spam Protection): 3 tasks (6 days)
- Wave 6 (Rooms): 5 tasks (14 days)
- Wave 7 (Encryption): 5 tasks (13 days)
- Wave 8 (WebRTC Calls): 6 tasks (13 days)
- Wave 9 (Admin Tools): 4 tasks (8 days)
- Wave 10 (File Sharing): 4 tasks (6 days)
- Wave 11 (Voice Messages): 3 tasks (7 days)
- Wave 12 (Reactions): 1 task (2 days)
- Wave 13 (Emoji Picker): 2 tasks (2 days)
- Wave 14 (Security Headers): 7 tasks (8 days)
- Wave 15 (PWA Support): 4 tasks (5 days)
- Wave 16 (Frontend UI): 13 tasks (30 days)
- Wave 17 (Launcher): 7 tasks (16 days)
- Wave 18 (Frontend Core): 5 tasks (8 days)

**Critical Path:**
Wave 1 → Wave 2 → Wave 3 → Wave 4 → Wave 6 → Wave 7 → Wave 8 → Wave 16

**Parallel Execution:**
- Wave 5 can run in parallel with Wave 6 (after Wave 4)
- Wave 9 can run in parallel with Wave 10 (after Wave 6)
- Wave 11 can run in parallel with Wave 12 (no dependencies)
- Wave 13 can run in parallel with Wave 14 (no dependencies)
- Wave 15 can run in parallel with Wave 14 (no dependencies)
- Wave 17 can run in parallel with Wave 16 (after Wave 1)
- Wave 18 can run in parallel with Wave 16 (after Wave 6)

---

# SUCCESS CRITERIA

A task is considered successfully completed when:

1. **Code is migrated**: All code is migrated from V1 to V2
2. **Code is adapted**: Code is adapted for V2 architecture (FastAPI, SQLite, etc.)
3. **Code is tested**: Code passes all tests
4. **Code is documented**: Code is documented with comments
5. **Rollback plan exists**: Rollback plan is documented and tested
6. **Verification passes**: All verification criteria pass
7. **No regressions**: No existing functionality is broken

---

# NEXT STEPS

1. Begin with Wave 1 (Foundation): TASK-001, TASK-002, TASK-003, TASK-004
2. Progress through waves sequentially on the critical path
3. Execute parallel waves when dependencies are met
4. Validate each task before marking complete
5. Perform integration testing after each wave
6. Perform full system testing after Wave 16
7. Perform launcher testing after Wave 17
8. Perform final validation after Wave 18
9. Rename V1 directory
10. Verify V2 works independently
11. Delete V1 permanently
