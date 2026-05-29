"""
backend/db.py — Database initialization and management

SQLite database for persistent storage of:
- Users/sessions
- Messages
- Rooms
- Devices/fingerprints
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "chat.db")

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # Sessions table (temporary connections by SID)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            sid TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            device_fingerprint TEXT
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT REFERENCES users(id),
            room_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_edited BOOLEAN DEFAULT 0,
            edited_at TIMESTAMP,
            message_type TEXT DEFAULT 'text'
        )
    """)
    
    # Create index for fast message retrieval
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_room_created 
        ON messages(room_id, created_at DESC)
    """)
    
    # Rooms table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT REFERENCES users(id),
            description TEXT,
            is_private BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # Room memberships table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_members (
            room_id TEXT REFERENCES rooms(id),
            user_id TEXT REFERENCES users(id),
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_moderator BOOLEAN DEFAULT 0,
            PRIMARY KEY (room_id, user_id)
        )
    """)
    
    # Message read receipts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS read_receipts (
            message_id INTEGER REFERENCES messages(id),
            user_id TEXT REFERENCES users(id),
            read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (message_id, user_id)
        )
    """)
    
    # Device fingerprints table (for enhanced security)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            fingerprint TEXT NOT NULL,
            user_agent TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_trusted BOOLEAN DEFAULT 0
        )
    """)

    # Session tokens table (for reconnect identity)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_tokens (
            uid TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            ip_address TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("✓ Database initialized at", DB_PATH)

# Message operations
def save_message(sender_id: str, room_id: str, content: str, message_type: str = "text") -> int:
    """Save a message to database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO messages (sender_id, room_id, content, message_type)
        VALUES (?, ?, ?, ?)
    """, (sender_id, room_id, content, message_type))
    
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def get_recent_messages(room_id: str, limit: int = 50) -> List[dict]:
    """Get recent messages from a room"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT m.id, m.sender_id, m.content, m.created_at, m.message_type,
               COALESCE(u.username, m.sender_id) as sender_name
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.room_id = ?
        ORDER BY m.created_at DESC
        LIMIT ?
    """, (room_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in reversed(rows)]

def get_messages_since(room_id: str, since: datetime) -> List[dict]:
    """Get messages since a specific time"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT m.id, m.sender_id, m.content, m.created_at, m.message_type,
               COALESCE(u.username, m.sender_id) as sender_name
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.room_id = ? AND m.created_at >= ?
        ORDER BY m.created_at ASC
    """, (room_id, since.isoformat()))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# User operations
def get_or_create_temp_user(sid: str) -> str:
    """Create temporary user for anonymous session"""
    username = f"guest_{sid[:8]}"
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (id, username)
            VALUES (?, ?)
        """, (sid, username))
        conn.commit()
    except sqlite3.IntegrityError:
        # User already exists
        pass
    
    conn.close()
    return sid

def record_session(sid: str, user_id: str, ip_address: str = None):
    """Record a session"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO sessions (sid, user_id, ip_address)
        VALUES (?, ?, ?)
    """, (sid, user_id, ip_address))
    
    conn.commit()
    conn.close()

def get_session(sid: str) -> Optional[dict]:
    """Get session info"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE sid = ?", (sid,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def update_session_activity(sid: str):
    """Update session last activity timestamp"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE sessions 
        SET last_activity = CURRENT_TIMESTAMP
        WHERE sid = ?
    """, (sid,))
    
    conn.commit()
    conn.close()

def delete_session(sid: str):
    """Delete a session"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
    
    conn.commit()
    conn.close()

# Room operations
def create_room_db(room_id: str, name: str, creator_id: str = None, is_private: bool = False):
    """Create a room in database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO rooms (id, name, created_by, is_private)
            VALUES (?, ?, ?, ?)
        """, (room_id, name, creator_id, is_private))
        
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Room already exists
    
    conn.close()

def add_room_member(room_id: str, user_id: str):
    """Add user to room"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO room_members (room_id, user_id)
            VALUES (?, ?)
        """, (room_id, user_id))
        
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already a member
    
    conn.close()

def get_room_members(room_id: str) -> List[str]:
    """Get all members in a room"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id FROM room_members WHERE room_id = ?
    """, (room_id,))
    
    members = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return members

# Session token operations
import secrets
from datetime import timedelta

def issue_session_token(uid: str, ttl_seconds: int = 24*3600, ip_address: str = None) -> str:
    """Issue or replace a session token for a uid. Returns token."""
    token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO session_tokens (uid, token, issued_at, expires_at, ip_address)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
    """, (uid, token, expires_at, ip_address))
    conn.commit()
    conn.close()
    return token


def verify_session_token(uid: str, token: str, ip_address: str = None) -> bool:
    """Verify a session token is valid and not expired. If ip_address provided, validate match if present."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT token, expires_at, ip_address FROM session_tokens WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    db_token = row['token']
    expires_at = row['expires_at']
    db_ip = row['ip_address']
    if db_token != token:
        return False
    if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
        return False
    if ip_address and db_ip and db_ip != ip_address:
        return False
    return True


def revoke_session_token(uid: str):
    """Remove session token for uid"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM session_tokens WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()

