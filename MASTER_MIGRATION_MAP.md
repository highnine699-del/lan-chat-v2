# LAN CHAT V2 MASTER MIGRATION MAP

**Generated:** May 30, 2026  
**V1 Location:** `c:\Users\AY ADVANCE TECH\Documents\local-whatsapp\lan-chat-final`  
**V2 Location:** `c:\Users\AY ADVANCE TECH\Documents\lan-chat-v2`

---

# EXECUTIVE SUMMARY

This document provides the definitive migration map for migrating all V1 features to V2. It converts feature-level analysis from the audit phase into file-level execution plans.

**Total Features to Migrate:** 103  
**Total Files to Migrate:** ~85  
**Estimated Duration:** 8-12 weeks  
**Critical Path:** Foundation → Authentication → Encryption → Messaging → Rooms → Calls → Frontend → Launcher

---

# PHASE 1 — FOUNDATION FEATURES

## Config System

**Feature Name:** Config System  
**Category:** Foundation  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `config.py` (165 lines)  
**V2 Destination Files:** `backend/config.py` (new file)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** None  
**Required Database Changes:** None  
**Required APIs:** None  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Medium  
**Migration Wave:** 1

---

## Event Schema

**Feature Name:** Event Schema  
**Category:** Foundation  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `events.py` (815 lines)  
**V2 Destination Files:** `backend/events.py` (new file)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** None  
**Required Database Changes:** None  
**Required APIs:** None  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Medium  
**Migration Wave:** 1

---

## Database Schema Adaptation

**Feature Name:** Database Schema Adaptation  
**Category:** Foundation  
**Priority:** Critical  
**Exists in V1:** ✓ (in-memory)  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `state.py` (in-memory schema)  
**V2 Destination Files:** `backend/db.py` (adapt existing)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** None  
**Required Database Changes:** Add tables: public_keys, shadow_muted, spam_tracker, upload_counts, ip_connections, active_sessions, analytics, message_votes, join_tokens. Add columns to users and rooms tables.  
**Required APIs:** None  
**Dependencies:** Config System  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 1

---

## State Management

**Feature Name:** State Management  
**Category:** Foundation  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `state.py` (1510 lines)  
**V2 Destination Files:** `backend/core/state.py` (replace existing)  
**Required Backend Modules:** Config System, Database  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None  
**Dependencies:** Config System, Database Schema  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 1

---

# PHASE 2 — CORE INFRASTRUCTURE

## HTTP Routes

**Feature Name:** HTTP Routes  
**Category:** Infrastructure  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/http.py` (387 lines)  
**V2 Destination Files:** `backend/routes/http.py` (new file)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** GET /, GET /uploads/<name>, GET /ice-config, POST /upload  
**Dependencies:** Config System, State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 2

---

## Socket.IO Base

**Feature Name:** Socket.IO Base  
**Category:** Infrastructure  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/__init__.py`, `server.py`  
**V2 Destination Files:** `backend/socket_manager.py` (adapt existing)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None  
**Dependencies:** Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 2

---

## Rate Limiting

**Feature Name:** Rate Limiting  
**Category:** Infrastructure  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rate_limit.py`  
**V2 Destination Files:** `backend/routes/socket_rate_limit.py` (new file)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None  
**Dependencies:** Config System, State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 2

---

# PHASE 3 — AUTHENTICATION & PRESENCE

## Username Registration

**Feature Name:** Username Registration  
**Category:** Authentication  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_auth.py`  
**V2 Destination Files:** `backend/routes/socket_auth.py` (new file)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** LoginPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: join  
**Dependencies:** State Management, Config System  
**Risk Level:** Low  
**Estimated Complexity:** Medium  
**Migration Wave:** 3

---

## Tag System

**Feature Name:** Tag System (#1234)  
**Category:** Authentication  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`  
**V2 Destination Files:** `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** LoginPage.js, ChatPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: join  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Medium  
**Migration Wave:** 3

---

## Session Tokens

**Feature Name:** Session Tokens (Reconnect)  
**Category:** Authentication  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `state.py`, `routes/socket_auth.py`  
**V2 Destination Files:** `backend/routes/socket_auth.py` (extend), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** socket.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect, socket: disconnect  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 3

---

## Server Password Protection

**Feature Name:** Server Password Protection  
**Category:** Authentication  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_auth.py`, `config.py`  
**V2 Destination Files:** `backend/routes/socket_auth.py` (extend), `backend/config.py` (extend)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** LoginPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect, socket: join  
**Dependencies:** Config System, State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 3

---

## Admin Password

**Feature Name:** Admin Password  
**Category:** Authentication  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_auth.py`, `config.py`  
**V2 Destination Files:** `backend/routes/socket_auth.py` (extend), `backend/config.py` (extend)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** LoginPage.js, AdminPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: join  
**Dependencies:** Config System, State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 3

---

## Join Rate Limiting

**Feature Name:** Join Rate Limiting  
**Category:** Authentication  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rate_limit.py`  
**V2 Destination Files:** `backend/routes/socket_rate_limit.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect, socket: join  
**Dependencies:** State Management, Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 3

---

## IP Connection Limits

**Feature Name:** IP Connection Limits  
**Category:** Authentication  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rate_limit.py`, `config.py`  
**V2 Destination Files:** `backend/routes/socket_rate_limit.py` (extend), `backend/config.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect  
**Dependencies:** State Management, Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 3

---

## Join Tokens

**Feature Name:** Join Tokens (Approval)  
**Category:** Authentication  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_rooms.py`  
**V2 Destination Files:** `backend/core/state.py` (extend), `backend/routes/socket_rooms.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** join_tokens table  
**Required APIs:** socket: room:join, socket: room:create  
**Dependencies:** State Management, Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 3

---

## UID Generation

**Feature Name:** UID Generation  
**Category:** Authentication  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`  
**V2 Destination Files:** `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: join  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 3

---

## Public Mode Enforcement

**Feature Name:** Public Mode Enforcement  
**Category:** Authentication  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_auth.py`, `config.py`  
**V2 Destination Files:** `backend/routes/socket_auth.py` (extend), `backend/config.py` (extend)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** LoginPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect, socket: join  
**Dependencies:** Config System, State Management  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 3

---

## User Presence Tracking

**Feature Name:** User Presence Tracking  
**Category:** Presence  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `state.py`, `routes/socket_auth.py`  
**V2 Destination Files:** `backend/core/presence.py` (enhance existing), `backend/routes/socket_auth.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** presence/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect, socket: disconnect  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 3

---

## Online/Offline Status

**Feature Name:** Online/Offline Status  
**Category:** Presence  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `state.py`, `routes/socket_auth.py`  
**V2 Destination Files:** `backend/core/presence.py` (enhance existing), `backend/routes/socket_auth.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** presence/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect, socket: disconnect, socket: user:list  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 3

---

## User Colors

**Feature Name:** User Colors  
**Category:** Presence  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `config.py`  
**V2 Destination Files:** `backend/core/presence.py` (extend), `backend/config.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** presence/, UserItem.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: user:list  
**Dependencies:** State Management, Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 3

---

## Reputation Labels

**Feature Name:** Reputation Labels  
**Category:** Presence  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`  
**V2 Destination Files:** `backend/core/presence.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** presence/, UserItem.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: user:list  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 3

---

# PHASE 4 — MESSAGING CORE

## Global Chat

**Feature Name:** Global Chat  
**Category:** Messaging  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (new file)  
**Required Backend Modules:** State Management, Event Schema  
**Required Frontend Modules:** messages/, ChatPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message  
**Dependencies:** State Management, Event Schema  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 4

---

## Direct Messages

**Feature Name:** Direct Messages (DMs)  
**Category:** Messaging  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_messages.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management, Encryption  
**Required Frontend Modules:** messages/, ChatPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: dm  
**Dependencies:** State Management, Encryption  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 6

---

## Room Messages

**Feature Name:** Room Messages  
**Category:** Messaging  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management, Rooms  
**Required Frontend Modules:** messages/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message (room-scoped)  
**Dependencies:** State Management, Rooms  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 4

---

## Message Editing

**Feature Name:** Message Editing  
**Category:** Messaging  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management, Database  
**Required Frontend Modules:** messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add is_edited, edited_at columns to messages table  
**Required APIs:** socket: message:edit  
**Dependencies:** State Management, Database  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 4

---

## Message Deletion

**Feature Name:** Message Deletion  
**Category:** Messaging  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management, Database  
**Required Frontend Modules:** messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add is_deleted column to messages table  
**Required APIs:** socket: message:delete  
**Dependencies:** State Management, Database  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 4

---

## Reply System

**Feature Name:** Reply System  
**Category:** Messaging  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management, Database  
**Required Frontend Modules:** messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add reply_to column to messages table  
**Required APIs:** socket: message:reply  
**Dependencies:** State Management, Database  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 4

---

## Message ID Tracking

**Feature Name:** Message ID Tracking  
**Category:** Messaging  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_messages.py`  
**V2 Destination Files:** `backend/core/state.py` (extend), `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** messages/, socket.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 4

---

## Message ACK

**Feature Name:** Message ACK (tempId)  
**Category:** Messaging  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** messages/, socket.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message, socket: message:ack  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 4

---

## Typing Indicators

**Feature Name:** Typing Indicators  
**Category:** Messaging  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** typing/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: typing:start, socket: typing:stop  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 4

---

# PHASE 5 — SPAM PROTECTION

## Smart Spam Detection

**Feature Name:** Smart Spam Detection  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_messages.py`  
**V2 Destination Files:** `backend/core/spam.py` (new file), `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** spam_tracker table  
**Required APIs:** socket: message  
**Dependencies:** State Management, Config System  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 5

---

## Shadow Muting

**Feature Name:** Shadow Muting  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_admin.py`  
**V2 Destination Files:** `backend/core/state.py` (extend), `backend/routes/socket_admin.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** admin/, AdminPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** shadow_muted table  
**Required APIs:** socket: admin:shadow_mute  
**Dependencies:** State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 5

---

## Cooldown Notifications

**Feature Name:** Cooldown Notifications  
**Category:** Security  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message, socket: error:cooldown  
**Dependencies:** State Management, Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Low  
**Migration Wave:** 5

---

## Message Length Limits

**Feature Name:** Message Length Limits  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `config.py`, `routes/socket_messages.py`  
**V2 Destination Files:** `backend/config.py` (extend), `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** InputBar.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message  
**Dependencies:** Config System, State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 5

---

## Vote-to-Hide

**Feature Name:** Vote-to-Hide  
**Category:** Security  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_messages.py`  
**V2 Destination Files:** `backend/routes/socket_messages.py` (extend)  
**Required Backend Modules:** State Management, Database  
**Required Frontend Modules:** messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** message_votes table  
**Required APIs:** socket: message:vote_hide  
**Dependencies:** State Management, Database  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 5

---

## Reputation System

**Feature Name:** Reputation System  
**Category:** Security  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`  
**V2 Destination Files:** `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** presence/, UserItem.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: user:list  
**Dependencies:** State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Low  
**Migration Wave:** 5

---

# PHASE 6 — ROOMS

## Room Creation

**Feature Name:** Room Creation  
**Category:** Rooms  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (new file), `backend/core/rooms.py` (enhance existing)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:create  
**Dependencies:** State Management, Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Room Joining

**Feature Name:** Room Joining  
**Category:** Rooms  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_rooms.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend)  
**Required Backend Modules:** State Management, Rooms  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:join  
**Dependencies:** State Management, Rooms  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Room Leaving

**Feature Name:** Room Leaving  
**Category:** Rooms  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_rooms.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend)  
**Required Backend Modules:** State Management, Rooms  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:leave  
**Dependencies:** State Management, Rooms  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Public Rooms

**Feature Name:** Public Rooms  
**Category:** Rooms  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (enhance existing)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:list, socket: room:create  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 6

---

## Private Rooms

**Feature Name:** Private Rooms  
**Category:** Rooms  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (enhance existing)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:create, socket: room:join  
**Dependencies:** State Management, Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Room Password Protection

**Feature Name:** Room Password Protection  
**Category:** Rooms  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add password column to rooms table  
**Required APIs:** socket: room:create, socket: room:join  
**Dependencies:** State Management, Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Room List

**Feature Name:** Room List  
**Category:** Rooms  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✓ (partial)  
**Current Status:** Partial  
**V1 Source Files:** `routes/socket_rooms.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:list  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 6

---

## Room Members List

**Feature Name:** Room Members List  
**Category:** Rooms  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:members  
**Dependencies:** State Management  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 6

---

## Room Admin

**Feature Name:** Room Admin (Creator/Moderators)  
**Category:** Rooms  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** rooms/, RoomPage.js, admin/, AdminPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add creator_sid, admins columns to rooms table  
**Required APIs:** socket: room:create, socket: room:promote, socket: room:demote  
**Dependencies:** State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Room Freeze

**Feature Name:** Room Freeze  
**Category:** Rooms  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rooms.py`, `routes/socket_admin.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/routes/socket_admin.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** rooms/, RoomPage.js, admin/, AdminPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add is_frozen column to rooms table  
**Required APIs:** socket: room:freeze, socket: room:unfreeze  
**Dependencies:** State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Ephemeral Rooms

**Feature Name:** Ephemeral Rooms (TTL)  
**Category:** Rooms  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_rooms.py`, `config.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (extend), `backend/config.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add ttl, delete_timer columns to rooms table  
**Required APIs:** socket: room:create  
**Dependencies:** State Management, Config System  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 6

---

## Room Auto-Delete on Empty

**Feature Name:** Room Auto-Delete on Empty  
**Category:** Rooms  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_rooms.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (background cleanup)  
**Dependencies:** State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 6

---

## Room Approval System

**Feature Name:** Room Approval System  
**Category:** Rooms  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** join_tokens table  
**Required APIs:** socket: room:join, socket: room:approve  
**Dependencies:** State Management, Config System  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 6

---

# PHASE 7 — ENCRYPTION

## ECDH Key Generation

**Feature Name:** ECDH Key Generation  
**Category:** Encryption  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/core/encryption.js`  
**V2 Destination Files:** `frontend/core/encryption.js` (new file)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** encryption.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** public_keys table  
**Required APIs:** socket: public_key  
**Dependencies:** State Management  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 7

---

## AES-GCM Encryption

**Feature Name:** AES-GCM Encryption  
**Category:** Encryption  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/core/encryption.js`  
**V2 Destination Files:** `frontend/core/encryption.js` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** encryption.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (client-side)  
**Dependencies:** ECDH Key Generation  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 7

---

## Public Key Exchange

**Feature Name:** Public Key Exchange  
**Category:** Encryption  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_auth.py`  
**V2 Destination Files:** `backend/routes/socket_auth.py` (extend), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** encryption.js, socket.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** public_keys table  
**Required APIs:** socket: public_key, socket: public_key:request  
**Dependencies:** State Management, ECDH Key Generation  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 7

---

## E2E Encryption for DMs

**Feature Name:** E2E Encryption for DMs  
**Category:** Encryption  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/core/encryption.js`  
**V2 Destination Files:** `frontend/core/encryption.js` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** encryption.js, messages/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: dm  
**Dependencies:** ECDH Key Generation, AES-GCM Encryption, Public Key Exchange  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 7

---

## E2E Encryption for Rooms

**Feature Name:** E2E Encryption for Rooms  
**Category:** Encryption  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/core/encryption.js`  
**V2 Destination Files:** `frontend/core/encryption.js` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** encryption.js, messages/, rooms/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message (room-scoped)  
**Dependencies:** ECDH Key Generation, AES-GCM Encryption, Public Key Exchange  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 7

---

# PHASE 8 — WEBRTC CALLS

## WebRTC Signaling

**Feature Name:** WebRTC Signaling  
**Category:** Calls  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_webrtc.py`  
**V2 Destination Files:** `backend/routes/socket_webrtc.py` (new file)  
**Required Backend Modules:** State Management, Rate Limiting  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:signal  
**Dependencies:** State Management, Rate Limiting  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 8

---

## Voice Calls

**Feature Name:** Voice Calls  
**Category:** Calls  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_webrtc.py`, `static/webrtc/`  
**V2 Destination Files:** `backend/routes/socket_webrtc.py` (extend), `frontend/call/` (new directory)  
**Required Backend Modules:** State Management, WebRTC Signaling  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:offer, socket: call:answer, socket: call:ice  
**Dependencies:** WebRTC Signaling  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 8

---

## Video Calls

**Feature Name:** Video Calls  
**Category:** Calls  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_webrtc.py`, `static/webrtc/`  
**V2 Destination Files:** `backend/routes/socket_webrtc.py` (extend), `frontend/call/` (extend)  
**Required Backend Modules:** State Management, WebRTC Signaling  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:offer, socket: call:answer, socket: call:ice  
**Dependencies:** WebRTC Signaling  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 8

---

## ICE Handling

**Feature Name:** ICE Handling  
**Category:** Calls  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_webrtc.py`, `routes/http.py`  
**V2 Destination Files:** `backend/routes/socket_webrtc.py` (extend), `backend/routes/http.py` (extend)  
**Required Backend Modules:** State Management, Config System  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:ice, GET /ice-config  
**Dependencies:** State Management, Config System  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 8

---

## TURN/STUN Support

**Feature Name:** TURN/STUN Support  
**Category:** Calls  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `config.py`, `routes/http.py`  
**V2 Destination Files:** `backend/config.py` (extend), `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** GET /ice-config  
**Dependencies:** Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 8

---

## Call Session Management

**Feature Name:** Call Session Management  
**Category:** Calls  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_webrtc.py`  
**V2 Destination Files:** `backend/core/calls.py` (new file), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:offer, socket: call:answer, socket: call:leave  
**Dependencies:** State Management  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 8

---

## Call Phase Management

**Feature Name:** Call Phase Management  
**Category:** Calls  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_webrtc.py`  
**V2 Destination Files:** `backend/core/calls.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:offer, socket: call:answer  
**Dependencies:** Call Session Management  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 8

---

## Call Tombstone

**Feature Name:** Call Tombstone (Reconnect)  
**Category:** Calls  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_webrtc.py`  
**V2 Destination Files:** `backend/core/calls.py` (extend), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:reconnect  
**Dependencies:** Call Session Management  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 8

---

## Offer Lock

**Feature Name:** Offer Lock (Prevent Double Call)  
**Category:** Calls  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `state.py`, `routes/socket_webrtc.py`  
**V2 Destination Files:** `backend/core/calls.py` (extend), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** call/, CallUI.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:offer  
**Dependencies:** Call Session Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 8

---

# PHASE 9 — ADMIN TOOLS

## Admin Kick

**Feature Name:** Admin Kick  
**Category:** Admin  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_admin.py`  
**V2 Destination Files:** `backend/routes/socket_admin.py` (new file)  
**Required Backend Modules:** State Management, Rooms  
**Required Frontend Modules:** admin/, AdminPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: admin:kick  
**Dependencies:** State Management, Rooms  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 9

---

## Admin Freeze

**Feature Name:** Admin Freeze  
**Category:** Admin  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_admin.py`  
**V2 Destination Files:** `backend/routes/socket_admin.py` (extend)  
**Required Backend Modules:** State Management, Rooms  
**Required Frontend Modules:** admin/, AdminPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: admin:freeze  
**Dependencies:** State Management, Rooms  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 9

---

## Shadow Mute

**Feature Name:** Shadow Mute  
**Category:** Admin  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_admin.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_admin.py` (extend), `backend/core/state.py` (extend)  
**Required Backend Modules:** State Management  
**Required Frontend Modules:** admin/, AdminPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** shadow_muted table  
**Required APIs:** socket: admin:shadow_mute  
**Dependencies:** State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 9

---

## Room Admin Permissions

**Feature Name:** Room Admin Permissions  
**Category:** Admin  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/socket_rooms.py`, `state.py`  
**V2 Destination Files:** `backend/routes/socket_rooms.py` (extend), `backend/core/rooms.py` (extend)  
**Required Backend Modules:** State Management, Rooms  
**Required Frontend Modules:** admin/, AdminPage.js, rooms/, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:promote, socket: room:demote  
**Dependencies:** State Management, Rooms  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 9

---

# PHASE 10 — FILE SHARING

## File Upload

**Feature Name:** File Upload  
**Category:** Files  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** files/, InputBar.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** upload_counts table  
**Required APIs:** POST /upload  
**Dependencies:** Config System, State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 10

---

## File Download

**Feature Name:** File Download  
**Category:** Files  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System, State Management  
**Required Frontend Modules:** files/, messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** GET /uploads/<name>  
**Dependencies:** Config System, State Management  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 10

---

## File Validation

**Feature Name:** File Validation  
**Category:** Files  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** files/, InputBar.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** POST /upload  
**Dependencies:** Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 10

---

## Media Support

**Feature Name:** Media Support  
**Category:** Files  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** files/, messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** GET /uploads/<name>  
**Dependencies:** Config System  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 10

---

# PHASE 11 — VOICE MESSAGES

## Voice Recording

**Feature Name:** Voice Recording  
**Category:** Voice  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/features/voiceMessages/voiceMessages.js`  
**V2 Destination Files:** `frontend/features/voiceMessages/voiceMessages.js` (new file)  
**Required Backend Modules:** None  
**Required Frontend Modules:** voiceMessages/, InputBar.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (client-side)  
**Dependencies:** None  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 11

---

## Voice Playback

**Feature Name:** Voice Playback  
**Category:** Voice  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/features/voiceMessages/voiceMessages.js`  
**V2 Destination Files:** `frontend/features/voiceMessages/voiceMessages.js` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** voiceMessages/, messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (client-side)  
**Dependencies:** Voice Recording  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 11

---

## Waveform Display

**Feature Name:** Waveform Display  
**Category:** Voice  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/features/voiceMessages/voiceMessages.js`  
**V2 Destination Files:** `frontend/features/voiceMessages/voiceMessages.js` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** voiceMessages/, messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (client-side)  
**Dependencies:** Voice Recording  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 11

---

# PHASE 12 — REACTIONS

## Emoji Reactions

**Feature Name:** Emoji Reactions  
**Category:** Reactions  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/features/reactions/reactions.js`  
**V2 Destination Files:** `frontend/features/reactions/reactions.js` (new file)  
**Required Backend Modules:** State Management, Database  
**Required Frontend Modules:** reactions/, messages/, ChatPage.js, RoomPage.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** Add reactions column to messages table  
**Required APIs:** socket: message:react  
**Dependencies:** State Management, Database  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 12

---

# PHASE 13 — EMOJI PICKER

## Emoji Picker (Bundled)

**Feature Name:** Emoji Picker (Bundled)  
**Category:** Emoji  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/emoji-picker.js`, `static/emoji-data.json`, `static/emoji-picker-picker.js`  
**V2 Destination Files:** `frontend/emoji-picker.js`, `frontend/emoji-data.json`, `frontend/emoji-picker-picker.js` (new files)  
**Required Backend Modules:** None  
**Required Frontend Modules:** InputBar.js  
**Required Assets:** emoji-data.json (439662 bytes)  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (client-side)  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 13

---

## Offline Emoji Support

**Feature Name:** Offline Emoji Support  
**Category:** Emoji  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/emoji-picker.js`, `static/emoji-data.json`  
**V2 Destination Files:** `frontend/emoji-picker.js`, `frontend/emoji-data.json` (new files)  
**Required Backend Modules:** None  
**Required Frontend Modules:** InputBar.js  
**Required Assets:** emoji-data.json (439662 bytes)  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (client-side)  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 13

---

# PHASE 14 — SECURITY HEADERS

## CSP Headers

**Feature Name:** CSP Headers  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All HTTP routes  
**Dependencies:** Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 14

---

## HSTS Headers

**Feature Name:** HSTS Headers  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All HTTP routes  
**Dependencies:** Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 14

---

## X-Frame-Options

**Feature Name:** X-Frame-Options  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All HTTP routes  
**Dependencies:** Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 14

---

## X-Content-Type-Options

**Feature Name:** X-Content-Type-Options  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All HTTP routes  
**Dependencies:** Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 14

---

## Referrer-Policy

**Feature Name:** Referrer-Policy  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All HTTP routes  
**Dependencies:** Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 14

---

## X-XSS-Protection

**Feature Name:** X-XSS-Protection  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All HTTP routes  
**Dependencies:** Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 14

---

## Trusted Proxy Support

**Feature Name:** Trusted Proxy Support  
**Category:** Security  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `routes/http.py`, `config.py`  
**V2 Destination Files:** `backend/routes/http.py` (extend), `backend/config.py` (extend)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All HTTP routes  
**Dependencies:** Config System  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 14

---

# PHASE 15 — PWA SUPPORT

## Manifest.json

**Feature Name:** Manifest.json  
**Category:** PWA  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/manifest.json`  
**V2 Destination Files:** `frontend/manifest.json` (new file)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** icon-192.png, icon-512.png  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** GET /manifest.json  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 15

---

## Service Worker

**Feature Name:** Service Worker  
**Category:** PWA  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/` (service-worker.js)  
**V2 Destination Files:** `frontend/service-worker.js` (new file)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** GET /service-worker.js  
**Dependencies:** None  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 15

---

## App Icons

**Feature Name:** App Icons  
**Category:** PWA  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/icon-192.png`, `static/icon-512.png`, `static/icon.svg`, `static/icon.ico`  
**V2 Destination Files:** `frontend/icon-192.png`, `frontend/icon-512.png`, `frontend/icon.svg`, `frontend/icon.ico` (new files)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** icon-192.png, icon-512.png, icon.svg, icon.ico  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** GET /icon-192.png, GET /icon-512.png, etc.  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 15

---

## iOS Meta Tags

**Feature Name:** iOS Meta Tags  
**Category:** PWA  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `templates/index.html`  
**V2 Destination Files:** `frontend/index.html` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (HTML meta tags)  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 15

---

# PHASE 16 — FRONTEND UI

## WhatsApp-Style UI

**Feature Name:** WhatsApp-Style UI  
**Category:** Frontend  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `templates/index.html` (3670 lines), `static/style.css` (44012 bytes)  
**V2 Destination Files:** `frontend/index.html` (replace), `frontend/style.css` (new file)  
**Required Backend Modules:** All backend modules  
**Required Frontend Modules:** All frontend modules  
**Required Assets:** icon-192.png, icon-512.png, wallpaper.svg, logo.svg  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** All APIs  
**Dependencies:** All backend features  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 16

---

## Modular Architecture

**Feature Name:** Modular Architecture  
**Category:** Frontend  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/init.js`, `static/core/`, `static/features/`, `static/ui/`  
**V2 Destination Files:** `frontend/init.js`, `frontend/core/`, `frontend/features/`, `frontend/ui/` (new structure)  
**Required Backend Modules:** None  
**Required Frontend Modules:** All frontend modules  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (architecture)  
**Dependencies:** None  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 16

---

## Login Page

**Feature Name:** Login Page  
**Category:** Frontend  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/pages/LoginPage.js`  
**V2 Destination Files:** `frontend/ui/pages/LoginPage.js` (new file)  
**Required Backend Modules:** Authentication  
**Required Frontend Modules:** core/socket.js, core/config.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: connect, socket: join  
**Dependencies:** Authentication  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 16

---

## Chat Page

**Feature Name:** Chat Page  
**Category:** Frontend  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/pages/ChatPage.js`  
**V2 Destination Files:** `frontend/ui/pages/ChatPage.js` (new file)  
**Required Backend Modules:** Messaging, Presence  
**Required Frontend Modules:** core/socket.js, messages/, typing/, presence/, components/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message, socket: user:list, socket: typing:start, socket: typing:stop  
**Dependencies:** Messaging, Presence  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 16

---

## Room Page

**Feature Name:** Room Page  
**Category:** Frontend  
**Priority:** Critical  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/pages/RoomPage.js`  
**V2 Destination Files:** `frontend/ui/pages/RoomPage.js` (new file)  
**Required Backend Modules:** Rooms, Messaging  
**Required Frontend Modules:** core/socket.js, rooms/, messages/, typing/, components/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:create, socket: room:join, socket: room:leave, socket: room:list, socket: message  
**Dependencies:** Rooms, Messaging  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 16

---

## Call UI

**Feature Name:** Call UI  
**Category:** Frontend  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/pages/CallUI.js`  
**V2 Destination Files:** `frontend/ui/pages/CallUI.js` (new file)  
**Required Backend Modules:** WebRTC Calls  
**Required Frontend Modules:** call/, core/socket.js  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: call:offer, socket: call:answer, socket: call:ice, socket: call:leave  
**Dependencies:** WebRTC Calls  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 16

---

## Admin Page

**Feature Name:** Admin Page  
**Category:** Frontend  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/pages/AdminPage.js`  
**V2 Destination Files:** `frontend/ui/pages/AdminPage.js` (new file)  
**Required Backend Modules:** Admin Tools  
**Required Frontend Modules:** admin/, core/socket.js, rooms/, components/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: admin:kick, socket: admin:freeze, socket: admin:shadow_mute, socket: room:list  
**Dependencies:** Admin Tools  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 16

---

## Sidebar Navigation

**Feature Name:** Sidebar Navigation  
**Category:** Frontend  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/` (sidebar implementation)  
**V2 Destination Files:** `frontend/` (sidebar implementation)  
**Required Backend Modules:** Rooms, Messaging  
**Required Frontend Modules:** rooms/, messages/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: room:list  
**Dependencies:** Rooms, Messaging  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 16

---

## User List Panel

**Feature Name:** User List Panel  
**Category:** Frontend  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/` (user list implementation)  
**V2 Destination Files:** `frontend/` (user list implementation)  
**Required Backend Modules:** Presence  
**Required Frontend Modules:** presence/, components/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: user:list  
**Dependencies:** Presence  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 16

---

## Message Components

**Feature Name:** Message Components  
**Category:** Frontend  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/components/MessageItem.js`  
**V2 Destination Files:** `frontend/ui/components/MessageItem.js` (new file)  
**Required Backend Modules:** Messaging  
**Required Frontend Modules:** messages/, reactions/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (component)  
**Dependencies:** Messaging  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 16

---

## Input Bar

**Feature Name:** Input Bar  
**Category:** Frontend  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/components/InputBar.js`  
**V2 Destination Files:** `frontend/ui/components/InputBar.js` (new file)  
**Required Backend Modules:** Messaging, File Sharing, Voice Messages  
**Required Frontend Modules:** messages/, files/, voiceMessages/, emoji-picker  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** socket: message, POST /upload  
**Dependencies:** Messaging, File Sharing, Voice Messages  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 16

---

## Modal System

**Feature Name:** Modal System  
**Category:** Frontend  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/components/Modal.js`  
**V2 Destination Files:** `frontend/ui/components/Modal.js` (new file)  
**Required Backend Modules:** None  
**Required Frontend Modules:** All pages  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (component)  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 16

---

## User Item Component

**Feature Name:** User Item Component  
**Category:** Frontend  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `static/ui/components/UserItem.js`  
**V2 Destination Files:** `frontend/ui/components/UserItem.js` (new file)  
**Required Backend Modules:** Presence  
**Required Frontend Modules:** presence/  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (component)  
**Dependencies:** Presence  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 16

---

# PHASE 17 — LAUNCHER

## NEXUS GUI Launcher

**Feature Name:** NEXUS GUI Launcher  
**Category:** Launcher  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `launcher.py` (2757 lines)  
**V2 Destination Files:** `launcher.py` (new file in root)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** icon.ico, icon.svg  
**Required Config Files:** launcher_config.json  
**Required Database Changes:** None  
**Required APIs:** None (desktop app)  
**Dependencies:** Config System  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 17

---

## Dashboard Stats

**Feature Name:** Dashboard Stats  
**Category:** Launcher  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `launcher.py`  
**V2 Destination Files:** `launcher.py` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (desktop app)  
**Dependencies:** None  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 17

---

## Ngrok Integration

**Feature Name:** Ngrok Integration  
**Category:** Launcher  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `launcher.py`, `ngrok_manager.py`  
**V2 Destination Files:** `launcher.py` (extend), `ngrok_manager.py` (new file in root)  
**Required Backend Modules:** Config System  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (desktop app)  
**Dependencies:** Config System  
**Risk Level:** High  
**Estimated Complexity:** High  
**Migration Wave:** 17

---

## Start/Stop Controls

**Feature Name:** Start/Stop Controls  
**Category:** Launcher  
**Priority:** High  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `launcher.py`  
**V2 Destination Files:** `launcher.py` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (desktop app)  
**Dependencies:** None  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 17

---

## Browser Launch

**Feature Name:** Browser Launch  
**Category:** Launcher  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `launcher.py`  
**V2 Destination Files:** `launcher.py` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (desktop app)  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 17

---

## System Tray

**Feature Name:** System Tray  
**Category:** Launcher  
**Priority:** Medium  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `launcher.py`  
**V2 Destination Files:** `launcher.py` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** icon.ico  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (desktop app)  
**Dependencies:** None  
**Risk Level:** Medium  
**Estimated Complexity:** Medium  
**Migration Wave:** 17

---

## QR Code Display

**Feature Name:** QR Code Display  
**Category:** Launcher  
**Priority:** Low  
**Exists in V1:** ✓  
**Exists in V2:** ✗  
**Current Status:** Missing  
**V1 Source Files:** `launcher.py`  
**V2 Destination Files:** `launcher.py` (extend)  
**Required Backend Modules:** None  
**Required Frontend Modules:** None  
**Required Assets:** None  
**Required Config Files:** Config  
**Required Database Changes:** None  
**Required APIs:** None (desktop app)  
**Dependencies:** None  
**Risk Level:** Low  
**Estimated Complexity:** Low  
**Migration Wave:** 17

---

# SUMMARY STATISTICS

**Total Features:** 103  
**Total Migration Waves:** 17  
**Critical Features:** 35  
**High Priority Features:** 40  
**Medium Priority Features:** 22  
**Low Priority Features:** 6  

**Risk Distribution:**
- High Risk: 25 features
- Medium Risk: 58 features
- Low Risk: 20 features

**Complexity Distribution:**
- High Complexity: 35 features
- Medium Complexity: 48 features
- Low Complexity: 20 features

**Dependencies:**
- Foundation features (Wave 1): 4 features, no dependencies
- Infrastructure features (Wave 2): 3 features, depend on Wave 1
- Authentication & Presence (Wave 3): 12 features, depend on Waves 1-2
- Messaging Core (Wave 4): 8 features, depend on Waves 1-3
- Spam Protection (Wave 5): 6 features, depend on Waves 1-4
- Rooms (Wave 6): 10 features, depend on Waves 1-4
- Encryption (Wave 7): 5 features, depend on Waves 1-3
- WebRTC Calls (Wave 8): 9 features, depend on Waves 1-3
- Admin Tools (Wave 9): 4 features, depend on Waves 1-6
- File Sharing (Wave 10): 4 features, depend on Waves 1-2
- Voice Messages (Wave 11): 3 features, no backend dependencies
- Reactions (Wave 12): 1 feature, depend on Waves 1-4
- Emoji Picker (Wave 13): 2 features, no dependencies
- Security Headers (Wave 14): 7 features, depend on Wave 1
- PWA Support (Wave 15): 4 features, no dependencies
- Frontend UI (Wave 16): 10 features, depend on all backend waves
- Launcher (Wave 17): 7 features, depend on Wave 1

---

# CRITICAL PATH ANALYSIS

The critical path for migration is:

1. **Wave 1 (Foundation)**: Config System, Event Schema, Database Schema, State Management
2. **Wave 2 (Infrastructure)**: HTTP Routes, Socket.IO Base, Rate Limiting
3. **Wave 3 (Authentication & Presence)**: All authentication and presence features
4. **Wave 4 (Messaging Core)**: Global Chat, Room Messages, Message Editing/Deletion, Reply System, Message ID Tracking, Message ACK, Typing Indicators
5. **Wave 6 (Rooms)**: All room features
6. **Wave 7 (Encryption)**: All encryption features
7. **Wave 8 (WebRTC Calls)**: All WebRTC features
8. **Wave 16 (Frontend UI)**: All frontend UI components

Waves 5, 9-15, and 17 can be executed in parallel with the critical path once their dependencies are met.

---

# SUCCESS CRITERIA

A feature is considered successfully migrated when:

1. **Backend exists in V2**: All backend code is migrated and functional
2. **Frontend exists in V2**: All frontend code is migrated and functional
3. **UI exists in V2**: All UI components are migrated and functional
4. **Workflow matches V1**: User workflows are identical to V1
5. **UX matches V1**: User experience is identical to V1
6. **Security behavior matches V1**: Security features work identically to V1
7. **Feature passes testing**: All tests pass for the feature
8. **V1 can be deleted without breaking it**: The feature works independently of V1

---

# NEXT STEPS

1. Review this MASTER MIGRATION MAP for completeness
2. Generate FILE_TO_FILE_MAPPING.md with complete file mapping
3. Generate MIGRATION_BACKLOG.md with prioritized tasks
4. Generate DATABASE_INTEGRATION_PLAN.md with schema analysis
5. Generate BLOCKER_ANALYSIS.md with risk assessment
6. Begin migration execution following the wave order
