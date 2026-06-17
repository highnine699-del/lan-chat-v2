# LAN CHAT V2 DATABASE INTEGRATION PLAN

**Generated:** May 30, 2026  
**V1 Location:** `c:\Users\AY ADVANCE TECH\Documents\local-whatsapp\lan-chat-final`  
**V2 Location:** `c:\Users\AY ADVANCE TECH\Documents\lan-chat-v2`

---

# EXECUTIVE SUMMARY

This document analyzes how V1 features should integrate with V2 SQLite persistence. V1 uses in-memory state (Python dicts), while V2 uses SQLite for persistence. This plan defines the required schema changes, migration strategies, and integration approaches for all major features.

**Total Schema Changes:** 11 new tables, 15 new columns, 8 new indexes  
**Migration Strategy:** Incremental migration with backward compatibility  
**Data Loss Risk:** Low (migration script with rollback)  
**Estimated Effort:** 3 days

---

# CURRENT V1 STATE STRUCTURE

V1 uses in-memory Python dictionaries for all state management:

```python
# V1 State Structure (from state.py)
users = {}  # sid -> User object
sid_map = {}  # display -> sid
uid_sessions = {}  # uid -> sid
active_sessions = {}  # sid -> Session object
session_tokens = {}  # token -> sid
public_keys = {}  # sid -> public key
message_history = deque(maxlen=MAX_GLOBAL_HISTORY)
private_history = {}  # conversation_id -> deque
rooms = {}  # room_id -> Room object
shadow_muted = {}  # sid -> mute expiry
spam_tracker = {}  # sid -> spam data
upload_counts = {}  # sid -> upload count
ip_connections = {}  # ip -> connection count
analytics = {}  # analytics data
message_votes = {}  # message_id -> votes
join_tokens = {}  # token -> room_id
```

---

# CURRENT V2 DATABASE SCHEMA

V2 currently has a basic SQLite schema with limited tables:

```sql
-- Current V2 Schema (from backend/db.py)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sid TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    room_id INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);
```

---

# REQUIRED SCHEMA CHANGES

## NEW TABLES

### 1. public_keys Table

**Purpose:** Store ECDH public keys for end-to-end encryption  
**V1 Equivalent:** `public_keys = {}` (sid -> public key)  
**Schema:**
```sql
CREATE TABLE public_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sid TEXT UNIQUE NOT NULL,
    public_key TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sid) REFERENCES users(sid) ON DELETE CASCADE
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on key rotation

**Indexes:**
```sql
CREATE INDEX idx_public_keys_sid ON public_keys(sid);
```

---

### 2. shadow_muted Table

**Purpose:** Track shadow-muted users for spam control  
**V1 Equivalent:** `shadow_muted = {}` (sid -> mute expiry)  
**Schema:**
```sql
CREATE TABLE shadow_muted (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sid TEXT UNIQUE NOT NULL,
    muted_until TIMESTAMP NOT NULL,
    muted_by TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sid) REFERENCES users(sid) ON DELETE CASCADE,
    FOREIGN KEY (muted_by) REFERENCES users(sid) ON DELETE SET NULL
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Clean up expired entries periodically

**Indexes:**
```sql
CREATE INDEX idx_shadow_muted_sid ON shadow_muted(sid);
CREATE INDEX idx_shadow_muted_muted_until ON shadow_muted(muted_until);
```

---

### 3. spam_tracker Table

**Purpose:** Track spam attempts for smart spam detection  
**V1 Equivalent:** `spam_tracker = {}` (sid -> spam data)  
**Schema:**
```sql
CREATE TABLE spam_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sid TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    last_message_time TIMESTAMP,
    repeat_count INTEGER DEFAULT 0,
    last_message_content TEXT,
    cooldown_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sid) REFERENCES users(sid) ON DELETE CASCADE
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on each message
- Clean up old entries periodically

**Indexes:**
```sql
CREATE INDEX idx_spam_tracker_sid ON spam_tracker(sid);
CREATE INDEX idx_spam_tracker_cooldown_until ON spam_tracker(cooldown_until);
```

---

### 4. upload_counts Table

**Purpose:** Track upload rates per user  
**V1 Equivalent:** `upload_counts = {}` (sid -> upload count)  
**Schema:**
```sql
CREATE TABLE upload_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sid TEXT UNIQUE NOT NULL,
    upload_count INTEGER DEFAULT 0,
    last_upload_time TIMESTAMP,
    window_start TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sid) REFERENCES users(sid) ON DELETE CASCADE
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on each upload
- Reset window periodically

**Indexes:**
```sql
CREATE INDEX idx_upload_counts_sid ON upload_counts(sid);
CREATE INDEX idx_upload_counts_window_start ON upload_counts(window_start);
```

---

### 5. ip_connections Table

**Purpose:** Track connections per IP for rate limiting  
**V1 Equivalent:** `ip_connections = {}` (ip -> connection count)  
**Schema:**
```sql
CREATE TABLE ip_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    connection_count INTEGER DEFAULT 0,
    last_connection_time TIMESTAMP,
    window_start TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on each connection
- Reset window periodically

**Indexes:**
```sql
CREATE INDEX idx_ip_connections_ip_address ON ip_connections(ip_address);
CREATE INDEX idx_ip_connections_window_start ON ip_connections(window_start);
```

---

### 6. active_sessions Table

**Purpose:** Track active sessions for disconnect-safe view  
**V1 Equivalent:** `active_sessions = {}` (sid -> Session object)  
**Schema:**
```sql
CREATE TABLE active_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sid TEXT UNIQUE NOT NULL,
    uid TEXT NOT NULL,
    username TEXT NOT NULL,
    display TEXT NOT NULL,
    room_id TEXT,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_online BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (sid) REFERENCES users(sid) ON DELETE CASCADE
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on connect/disconnect
- Clean up stale entries periodically

**Indexes:**
```sql
CREATE INDEX idx_active_sessions_sid ON active_sessions(sid);
CREATE INDEX idx_active_sessions_uid ON active_sessions(uid);
CREATE INDEX idx_active_sessions_room_id ON active_sessions(room_id);
CREATE INDEX idx_active_sessions_last_seen ON active_sessions(last_seen);
```

---

### 7. analytics Table

**Purpose:** Track usage analytics  
**V1 Equivalent:** `analytics = {}` (analytics data)  
**Schema:**
```sql
CREATE TABLE analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    event_data TEXT,
    user_sid TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_sid) REFERENCES users(sid) ON DELETE SET NULL
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Insert on each analytics event
- Archive old entries periodically

**Indexes:**
```sql
CREATE INDEX idx_analytics_event_type ON analytics(event_type);
CREATE INDEX idx_analytics_timestamp ON analytics(timestamp);
CREATE INDEX idx_analytics_user_sid ON analytics(user_sid);
```

---

### 8. message_votes Table

**Purpose:** Track votes to hide messages  
**V1 Equivalent:** `message_votes = {}` (message_id -> votes)  
**Schema:**
```sql
CREATE TABLE message_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    voter_sid TEXT NOT NULL,
    vote_type TEXT DEFAULT 'hide',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (voter_sid) REFERENCES users(sid) ON DELETE CASCADE,
    UNIQUE(message_id, voter_sid)
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Insert on each vote
- Clean up after message deletion

**Indexes:**
```sql
CREATE INDEX idx_message_votes_message_id ON message_votes(message_id);
CREATE INDEX idx_message_votes_voter_sid ON message_votes(voter_sid);
```

---

### 9. join_tokens Table

**Purpose:** Track join tokens for room approval  
**V1 Equivalent:** `join_tokens = {}` (token -> room_id)  
**Schema:**
```sql
CREATE TABLE join_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    room_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(sid) ON DELETE CASCADE,
    FOREIGN KEY (used_by) REFERENCES users(sid) ON DELETE SET NULL
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Insert on token creation
- Update on token use
- Clean up expired tokens periodically

**Indexes:**
```sql
CREATE INDEX idx_join_tokens_token ON join_tokens(token);
CREATE INDEX idx_join_tokens_room_id ON join_tokens(room_id);
CREATE INDEX idx_join_tokens_expires_at ON join_tokens(expires_at);
```

---

### 10. session_tokens Table

**Purpose:** Track session tokens for reconnection  
**V1 Equivalent:** `session_tokens = {}` (token -> sid)  
**Schema:**
```sql
CREATE TABLE session_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    sid TEXT NOT NULL,
    uid TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_used TIMESTAMP,
    FOREIGN KEY (sid) REFERENCES users(sid) ON DELETE CASCADE
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Insert on token issuance
- Update on token use
- Clean up expired tokens periodically

**Indexes:**
```sql
CREATE INDEX idx_session_tokens_token ON session_tokens(token);
CREATE INDEX idx_session_tokens_sid ON session_tokens(sid);
CREATE INDEX idx_session_tokens_expires_at ON session_tokens(expires_at);
```

---

### 11. private_history Table

**Purpose:** Track private message history per conversation  
**V1 Equivalent:** `private_history = {}` (conversation_id -> deque)  
**Schema:**
```sql
CREATE TABLE private_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    sender_sid TEXT NOT NULL,
    receiver_sid TEXT NOT NULL,
    content TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_sid) REFERENCES users(sid) ON DELETE CASCADE,
    FOREIGN KEY (receiver_sid) REFERENCES users(sid) ON DELETE CASCADE
);
```

**Migration Strategy:**  
- Create table during Wave 1 (Foundation)
- Populate from V1 state during migration
- Insert on each DM
- Clean up old entries periodically

**Indexes:**
```sql
CREATE INDEX idx_private_history_conversation_id ON private_history(conversation_id);
CREATE INDEX idx_private_history_sender_sid ON private_history(sender_sid);
CREATE INDEX idx_private_history_receiver_sid ON private_history(receiver_sid);
CREATE INDEX idx_private_history_created_at ON private_history(created_at);
```

---

## EXTENDED COLUMNS

### users Table Extensions

**Current V2 Schema:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sid TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Required Additions:**
```sql
ALTER TABLE users ADD COLUMN username TEXT;
ALTER TABLE users ADD COLUMN tag INTEGER;
ALTER TABLE users ADD COLUMN display TEXT;
ALTER TABLE users ADD COLUMN uid TEXT UNIQUE;
ALTER TABLE users ADD COLUMN color TEXT;
ALTER TABLE users ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN msg_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN is_server_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN persona TEXT DEFAULT 'default';
ALTER TABLE users ADD COLUMN presence TEXT DEFAULT 'offline';
ALTER TABLE users ADD COLUMN last_message TEXT;
ALTER TABLE users ADD COLUMN last_message_time TIMESTAMP;
ALTER TABLE users ADD COLUMN spam_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN room_id TEXT;
```

**Migration Strategy:**  
- Add columns during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on user state changes

**Indexes:**
```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_uid ON users(uid);
CREATE INDEX idx_users_room_id ON users(room_id);
CREATE INDEX idx_users_presence ON users(presence);
```

---

### rooms Table Extensions

**Current V2 Schema:**
```sql
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Required Additions:**
```sql
ALTER TABLE rooms ADD COLUMN visibility TEXT DEFAULT 'public';
ALTER TABLE rooms ADD COLUMN password TEXT;
ALTER TABLE rooms ADD COLUMN creator_sid TEXT;
ALTER TABLE rooms ADD COLUMN members TEXT; -- JSON array
ALTER TABLE rooms ADD COLUMN admins TEXT; -- JSON array
ALTER TABLE rooms ADD COLUMN ttl INTEGER;
ALTER TABLE rooms ADD COLUMN messages TEXT; -- JSON array (in-memory cache)
ALTER TABLE rooms ADD COLUMN is_frozen BOOLEAN DEFAULT FALSE;
ALTER TABLE rooms ADD COLUMN delete_timer TIMESTAMP;
```

**Migration Strategy:**  
- Add columns during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on room state changes

**Indexes:**
```sql
CREATE INDEX idx_rooms_visibility ON rooms(visibility);
CREATE INDEX idx_rooms_creator_sid ON rooms(creator_sid);
CREATE INDEX idx_rooms_delete_timer ON rooms(delete_timer);
```

---

### messages Table Extensions

**Current V2 Schema:**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    room_id INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);
```

**Required Additions:**
```sql
ALTER TABLE messages ADD COLUMN message_id TEXT UNIQUE; -- Client-side message ID
ALTER TABLE messages ADD COLUMN temp_id TEXT; -- Client-side temporary ID
ALTER TABLE messages ADD COLUMN reply_to INTEGER; -- Reply to message ID
ALTER TABLE messages ADD COLUMN is_edited BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN edited_at TIMESTAMP;
ALTER TABLE messages ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE messages ADD COLUMN delivery_status TEXT DEFAULT 'pending';
ALTER TABLE messages ADD COLUMN read_status TEXT DEFAULT 'unread';
ALTER TABLE messages ADD COLUMN read_at TIMESTAMP;
ALTER TABLE messages ADD COLUMN encrypted BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN reactions TEXT; -- JSON object
ALTER TABLE messages ADD COLUMN conversation_id TEXT; -- For DMs
```

**Migration Strategy:**  
- Add columns during Wave 1 (Foundation)
- Populate from V1 state during migration
- Update on message state changes

**Indexes:**
```sql
CREATE INDEX idx_messages_message_id ON messages(message_id);
CREATE INDEX idx_messages_temp_id ON messages(temp_id);
CREATE INDEX idx_messages_reply_to ON messages(reply_to);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

---

# MIGRATION STRATEGY

## Phase 1: Schema Creation (Wave 1)

**Tasks:**
1. Create all new tables (public_keys, shadow_muted, spam_tracker, upload_counts, ip_connections, active_sessions, analytics, message_votes, join_tokens, session_tokens, private_history)
2. Add all new columns to users table
3. Add all new columns to rooms table
4. Add all new columns to messages table
5. Create all indexes

**Script:** `migrations/001_create_v1_schema.sql`

```sql
-- Create new tables
CREATE TABLE IF NOT EXISTS public_keys (...);
CREATE TABLE IF NOT EXISTS shadow_muted (...);
CREATE TABLE IF NOT EXISTS spam_tracker (...);
CREATE TABLE IF NOT EXISTS upload_counts (...);
CREATE TABLE IF NOT EXISTS ip_connections (...);
CREATE TABLE IF NOT EXISTS active_sessions (...);
CREATE TABLE IF NOT EXISTS analytics (...);
CREATE TABLE IF NOT EXISTS message_votes (...);
CREATE TABLE IF NOT EXISTS join_tokens (...);
CREATE TABLE IF NOT EXISTS session_tokens (...);
CREATE TABLE IF NOT EXISTS private_history (...);

-- Add columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;
-- ... (all other columns)

-- Add columns to rooms table
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'public';
-- ... (all other columns)

-- Add columns to messages table
ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_id TEXT UNIQUE;
-- ... (all other columns)

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_public_keys_sid ON public_keys(sid);
-- ... (all other indexes)
```

**Rollback:** `migrations/001_rollback_v1_schema.sql`

---

## Phase 2: Data Migration (Wave 1)

**Tasks:**
1. Migrate users from V1 state to V2 database
2. Migrate rooms from V1 state to V2 database
3. Migrate messages from V1 state to V2 database
4. Migrate public_keys from V1 state to V2 database
5. Migrate shadow_muted from V1 state to V2 database
6. Migrate spam_tracker from V1 state to V2 database
7. Migrate upload_counts from V1 state to V2 database
8. Migrate ip_connections from V1 state to V2 database
9. Migrate active_sessions from V1 state to V2 database
10. Migrate analytics from V1 state to V2 database
11. Migrate message_votes from V1 state to V2 database
12. Migrate join_tokens from V1 state to V2 database
13. Migrate session_tokens from V1 state to V2 database
14. Migrate private_history from V1 state to V2 database

**Script:** `migrations/002_migrate_v1_data.py`

```python
import sqlite3
from datetime import datetime

def migrate_v1_to_v2(v1_state, v2_db_path):
    conn = sqlite3.connect(v2_db_path)
    cursor = conn.cursor()
    
    # Migrate users
    for sid, user in v1_state['users'].items():
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (sid, username, tag, display, uid, color, joined_at, msg_count, 
             is_server_admin, persona, presence, last_message, last_message_time, 
             spam_count, room_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sid, user.username, user.tag, user.display, user.uid, user.color,
            user.joined_at, user.msg_count, user.is_server_admin, user.persona,
            user.presence, user.last_message, user.last_message_time,
            user.spam_count, user.room_id
        ))
    
    # Migrate rooms
    for room_id, room in v1_state['rooms'].items():
        cursor.execute("""
            INSERT OR REPLACE INTO rooms 
            (id, name, visibility, password, creator_sid, members, admins, 
             ttl, messages, is_frozen, delete_timer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            room_id, room.name, room.visibility, room.password, room.creator_sid,
            json.dumps(room.members), json.dumps(room.admins), room.ttl,
            json.dumps(room.messages), room.is_frozen, room.delete_timer
        ))
    
    # Migrate messages
    for message in v1_state['message_history']:
        cursor.execute("""
            INSERT INTO messages 
            (user_id, room_id, content, message_id, temp_id, reply_to, 
             is_edited, edited_at, is_deleted, deleted_at, delivery_status, 
             read_status, read_at, encrypted, reactions, conversation_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.user_id, message.room_id, message.content, message.message_id,
            message.temp_id, message.reply_to, message.is_edited, message.edited_at,
            message.is_deleted, message.deleted_at, message.delivery_status,
            message.read_status, message.read_at, message.encrypted,
            json.dumps(message.reactions), message.conversation_id
        ))
    
    # Migrate other tables...
    # (similar pattern for public_keys, shadow_muted, spam_tracker, etc.)
    
    conn.commit()
    conn.close()
```

**Rollback:** Delete and recreate database from backup

---

## Phase 3: Validation (Wave 1)

**Tasks:**
1. Validate all users migrated correctly
2. Validate all rooms migrated correctly
3. Validate all messages migrated correctly
4. Validate all auxiliary data migrated correctly
5. Validate foreign key constraints
6. Validate data integrity

**Script:** `migrations/003_validate_migration.py`

```python
import sqlite3

def validate_migration(v2_db_path):
    conn = sqlite3.connect(v2_db_path)
    cursor = conn.cursor()
    
    # Validate users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"Users migrated: {user_count}")
    
    # Validate rooms
    cursor.execute("SELECT COUNT(*) FROM rooms")
    room_count = cursor.fetchone()[0]
    print(f"Rooms migrated: {room_count}")
    
    # Validate messages
    cursor.execute("SELECT COUNT(*) FROM messages")
    message_count = cursor.fetchone()[0]
    print(f"Messages migrated: {message_count}")
    
    # Validate foreign keys
    cursor.execute("PRAGMA foreign_key_check")
    fk_errors = cursor.fetchall()
    if fk_errors:
        print("Foreign key errors:", fk_errors)
        return False
    
    conn.close()
    return True
```

---

# FEATURE INTEGRATION

## Messages

**V1 Behavior:** In-memory deque with maxlen=MAX_GLOBAL_HISTORY  
**V2 Schema:** messages table with created_at index  
**Integration Strategy:**
- Store all messages in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Clean up old messages periodically based on MAX_GLOBAL_HISTORY

**Query Pattern:**
```python
# Get recent messages (in-memory cache)
recent_messages = message_history[-100:]

# Get historical messages (database)
cursor.execute("""
    SELECT * FROM messages 
    WHERE room_id = ? 
    ORDER BY created_at DESC 
    LIMIT 100
""", (room_id,))
```

---

## Rooms

**V1 Behavior:** In-memory dict with room objects  
**V2 Schema:** rooms table with JSON columns for members/admins  
**Integration Strategy:**
- Store room metadata in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Sync cache with database on changes

**Query Pattern:**
```python
# Get room (in-memory cache)
room = rooms.get(room_id)

# Get room (database)
cursor.execute("""
    SELECT * FROM rooms WHERE id = ?
""", (room_id,))
```

---

## Users

**V1 Behavior:** In-memory dict with user objects  
**V2 Schema:** users table with extended columns  
**Integration Strategy:**
- Store user metadata in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Sync cache with database on changes

**Query Pattern:**
```python
# Get user (in-memory cache)
user = users.get(sid)

# Get user (database)
cursor.execute("""
    SELECT * FROM users WHERE sid = ?
""", (sid,))
```

---

## Direct Messages

**V1 Behavior:** In-memory dict of deques per conversation  
**V2 Schema:** private_history table with conversation_id  
**Integration Strategy:**
- Store all DMs in database
- Maintain in-memory cache per conversation
- Use database for persistence across restarts
- Clean up old messages based on MAX_PRIVATE_HISTORY

**Query Pattern:**
```python
# Get DM history (in-memory cache)
dm_history = private_history.get(conversation_id, deque())

# Get DM history (database)
cursor.execute("""
    SELECT * FROM private_history 
    WHERE conversation_id = ? 
    ORDER BY created_at DESC 
    LIMIT 100
""", (conversation_id,))
```

---

## Public Keys

**V1 Behavior:** In-memory dict mapping sid to public key  
**V2 Schema:** public_keys table with sid and public_key  
**Integration Strategy:**
- Store all public keys in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Update on key rotation

**Query Pattern:**
```python
# Get public key (in-memory cache)
public_key = public_keys.get(sid)

# Get public key (database)
cursor.execute("""
    SELECT public_key FROM public_keys WHERE sid = ?
""", (sid,))
```

---

## Session Tokens

**V1 Behavior:** In-memory dict mapping token to sid  
**V2 Schema:** session_tokens table with token, sid, uid, expires_at  
**Integration Strategy:**
- Store all session tokens in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Clean up expired tokens periodically

**Query Pattern:**
```python
# Validate session token (in-memory cache)
sid = session_tokens.get(token)

# Validate session token (database)
cursor.execute("""
    SELECT sid FROM session_tokens 
    WHERE token = ? AND expires_at > ?
""", (token, datetime.now()))
```

---

## Shadow Muted

**V1 Behavior:** In-memory dict mapping sid to mute expiry  
**V2 Schema:** shadow_muted table with sid, muted_until  
**Integration Strategy:**
- Store all shadow mutes in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Clean up expired mutes periodically

**Query Pattern:**
```python
# Check if shadow muted (in-memory cache)
is_muted = shadow_muted.get(sid, 0) > time.time()

# Check if shadow muted (database)
cursor.execute("""
    SELECT muted_until FROM shadow_muted 
    WHERE sid = ? AND muted_until > ?
""", (sid, datetime.now()))
```

---

## Spam Tracker

**V1 Behavior:** In-memory dict mapping sid to spam data  
**V2 Schema:** spam_tracker table with sid, message_count, last_message_time  
**Integration Strategy:**
- Store all spam data in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Clean up old entries periodically

**Query Pattern:**
```python
# Check spam status (in-memory cache)
spam_data = spam_tracker.get(sid)

# Check spam status (database)
cursor.execute("""
    SELECT * FROM spam_tracker WHERE sid = ?
""", (sid,))
```

---

## Upload Counts

**V1 Behavior:** In-memory dict mapping sid to upload count  
**V2 Schema:** upload_counts table with sid, upload_count, window_start  
**Integration Strategy:**
- Store all upload counts in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Reset window periodically

**Query Pattern:**
```python
# Check upload count (in-memory cache)
upload_count = upload_counts.get(sid, 0)

# Check upload count (database)
cursor.execute("""
    SELECT upload_count FROM upload_counts 
    WHERE sid = ? AND window_start > ?
""", (sid, time.time() - WINDOW_DURATION))
```

---

## IP Connections

**V1 Behavior:** In-memory dict mapping ip to connection count  
**V2 Schema:** ip_connections table with ip_address, connection_count  
**Integration Strategy:**
- Store all IP connections in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Reset window periodically

**Query Pattern:**
```python
# Check connection count (in-memory cache)
connection_count = ip_connections.get(ip, 0)

# Check connection count (database)
cursor.execute("""
    SELECT connection_count FROM ip_connections 
    WHERE ip_address = ? AND window_start > ?
""", (ip, time.time() - WINDOW_DURATION))
```

---

## Active Sessions

**V1 Behavior:** In-memory dict mapping sid to Session object  
**V2 Schema:** active_sessions table with sid, uid, room_id, is_online  
**Integration Strategy:**
- Store all active sessions in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Update on connect/disconnect
- Clean up stale entries periodically

**Query Pattern:**
```python
# Get active sessions (in-memory cache)
sessions = active_sessions

# Get active sessions (database)
cursor.execute("""
    SELECT * FROM active_sessions WHERE is_online = TRUE
""")
```

---

## Analytics

**V1 Behavior:** In-memory dict with analytics data  
**V2 Schema:** analytics table with event_type, event_data, timestamp  
**Integration Strategy:**
- Store all analytics events in database
- No in-memory cache (write-only)
- Use database for persistence and analysis
- Archive old entries periodically

**Query Pattern:**
```python
# Log analytics event (database)
cursor.execute("""
    INSERT INTO analytics (event_type, event_data, user_sid)
    VALUES (?, ?, ?)
""", (event_type, json.dumps(event_data), user_sid))
```

---

## Message Votes

**V1 Behavior:** In-memory dict mapping message_id to votes  
**V2 Schema:** message_votes table with message_id, voter_sid, vote_type  
**Integration Strategy:**
- Store all votes in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Clean up after message deletion

**Query Pattern:**
```python
# Get vote count (in-memory cache)
vote_count = len(message_votes.get(message_id, []))

# Get vote count (database)
cursor.execute("""
    SELECT COUNT(*) FROM message_votes WHERE message_id = ?
""", (message_id,))
```

---

## Join Tokens

**V1 Behavior:** In-memory dict mapping token to room_id  
**V2 Schema:** join_tokens table with token, room_id, expires_at  
**Integration Strategy:**
- Store all join tokens in database
- Maintain in-memory cache for performance
- Use database for persistence across restarts
- Clean up expired tokens periodically

**Query Pattern:**
```python
# Validate join token (in-memory cache)
room_id = join_tokens.get(token)

# Validate join token (database)
cursor.execute("""
    SELECT room_id FROM join_tokens 
    WHERE token = ? AND expires_at > ? AND used = FALSE
""", (token, datetime.now()))
```

---

# PERFORMANCE CONSIDERATIONS

## Index Strategy

**Critical Indexes:**
- `idx_users_sid` - User lookups (high frequency)
- `idx_users_uid` - UID lookups (medium frequency)
- `idx_rooms_id` - Room lookups (high frequency)
- `idx_messages_room_id` - Message queries (high frequency)
- `idx_messages_created_at` - Message history (high frequency)
- `idx_private_history_conversation_id` - DM history (high frequency)
- `idx_session_tokens_token` - Token validation (high frequency)
- `idx_active_sessions_sid` - Session lookups (high frequency)

**Secondary Indexes:**
- `idx_users_presence` - Presence queries (medium frequency)
- `idx_rooms_visibility` - Room list (medium frequency)
- `idx_messages_message_id` - Message ACK (medium frequency)
- `idx_shadow_muted_sid` - Spam checks (medium frequency)
- `idx_spam_tracker_sid` - Spam checks (medium frequency)

---

## Caching Strategy

**In-Memory Cache:**
- Users dict (primary cache)
- Rooms dict (primary cache)
- Message history deque (primary cache)
- Private history dict (primary cache)
- Public keys dict (primary cache)
- Session tokens dict (primary cache)
- Shadow muted dict (primary cache)
- Spam tracker dict (primary cache)
- Upload counts dict (primary cache)
- IP connections dict (primary cache)
- Active sessions dict (primary cache)
- Message votes dict (primary cache)
- Join tokens dict (primary cache)

**Cache Invalidation:**
- Write-through cache (write to DB and cache)
- Cache refresh on restart (load from DB)
- Periodic cache sync (every 5 minutes)
- Manual cache invalidation (admin command)

---

## Cleanup Strategy

**Periodic Cleanup:**
- Expired session tokens (every hour)
- Expired join tokens (every hour)
- Expired shadow mutes (every hour)
- Old spam tracker entries (every day)
- Old upload counts (every hour)
- Old IP connections (every hour)
- Stale active sessions (every 5 minutes)
- Old analytics entries (every week)
- Old message votes (after message deletion)
- Old private history (based on MAX_PRIVATE_HISTORY)
- Old global history (based on MAX_GLOBAL_HISTORY)

**Cleanup Script:** `scripts/cleanup_database.py`

```python
import sqlite3
from datetime import datetime, timedelta

def cleanup_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clean expired session tokens
    cursor.execute("""
        DELETE FROM session_tokens WHERE expires_at < ?
    """, (datetime.now(),))
    
    # Clean expired join tokens
    cursor.execute("""
        DELETE FROM join_tokens WHERE expires_at < ?
    """, (datetime.now(),))
    
    # Clean expired shadow mutes
    cursor.execute("""
        DELETE FROM shadow_muted WHERE muted_until < ?
    """, (datetime.now(),))
    
    # Clean old spam tracker entries
    cursor.execute("""
        DELETE FROM spam_tracker WHERE updated_at < ?
    """, (datetime.now() - timedelta(days=7),))
    
    # Clean old upload counts
    cursor.execute("""
        DELETE FROM upload_counts WHERE window_start < ?
    """, (datetime.now() - timedelta(hours=1),))
    
    # Clean old IP connections
    cursor.execute("""
        DELETE FROM ip_connections WHERE window_start < ?
    """, (datetime.now() - timedelta(hours=1),))
    
    # Clean stale active sessions
    cursor.execute("""
        UPDATE active_sessions SET is_online = FALSE 
        WHERE last_seen < ?
    """, (datetime.now() - timedelta(minutes=5),))
    
    # Clean old analytics entries
    cursor.execute("""
        DELETE FROM analytics WHERE timestamp < ?
    """, (datetime.now() - timedelta(weeks=4),))
    
    conn.commit()
    conn.close()
```

---

# TESTING STRATEGY

## Unit Tests

**Test Cases:**
1. Schema creation test
2. Data migration test
3. Foreign key constraint test
4. Index performance test
5. Cache consistency test
6. Cleanup script test

**Test Script:** `tests/test_database_migration.py`

---

## Integration Tests

**Test Cases:**
1. User creation and retrieval
2. Room creation and retrieval
3. Message creation and retrieval
4. DM creation and retrieval
5. Public key storage and retrieval
6. Session token creation and validation
7. Shadow mute creation and expiration
8. Spam tracking and cleanup
9. Upload counting and window reset
10. IP connection limiting and window reset

**Test Script:** `tests/test_database_integration.py`

---

## Performance Tests

**Test Cases:**
1. 1000 users query performance
2. 1000 messages query performance
3. 100 rooms query performance
4. Concurrent write performance
5. Cache hit rate measurement
6. Index effectiveness measurement

**Test Script:** `tests/test_database_performance.py`

---

# ROLLBACK PLAN

## Rollback Triggers

1. Schema creation failure
2. Data migration failure
3. Validation failure
4. Performance degradation
5. Data corruption

## Rollback Procedure

1. Stop V2 server
2. Restore database from backup
3. Restart V2 server
4. Validate rollback success
5. Document rollback reason

## Rollback Script

`migrations/rollback_migration.py`

```python
import sqlite3
import shutil
from datetime import datetime

def rollback_migration(db_path, backup_path):
    # Stop server (manual)
    
    # Restore database from backup
    shutil.copy(backup_path, db_path)
    
    # Restart server (manual)
    
    # Validate rollback
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"Users after rollback: {user_count}")
    conn.close()
```

---

# SUMMARY

**Total Schema Changes:** 11 new tables, 15 new columns, 8 new indexes  
**Migration Phases:** 3 (Schema Creation, Data Migration, Validation)  
**Estimated Effort:** 3 days  
**Risk Level:** Medium  
**Rollback Plan:** Yes (database backup)  
**Testing Strategy:** Unit, Integration, Performance tests  

**Success Criteria:**
1. All V1 state structures represented in database
2. All V1 data migrated without loss
3. Foreign key constraints enforced
4. Indexes created for performance
5. Cache consistency maintained
6. Cleanup scripts working
7. Performance acceptable
8. Rollback plan tested
