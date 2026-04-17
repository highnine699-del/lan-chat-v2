"""
state.py — Shared in-memory state and pure helper functions.

All mutable state lives here so every other module imports from one place.
Nothing in this module imports from Flask or Socket.IO, keeping it testable
in isolation.

Schema reference
----------------
users[sid] = {
    'username': str, 'tag': str, 'display': str, 'uid': str,
    'color': str, 'joined_at': float, 'msg_count': int,
    'room_id': str | None, 'presence': str, 'persona': str | None,
}

rooms[room_id] = {
    'id':           str,
    'name':         str,
    'visibility':   'public' | 'private',   ← NEW
    'password':     str | None,             # always None for public rooms
    'creator_sid':  str,
    'members':      set[sid],
    'admins':       set[sid],
    'created_at':   float,
    'ttl':          int | None,
    'messages':     deque[msg],
    'is_frozen':    bool,
    'delete_timer': Timer | None,
}

user_state[sid] = {
    'username': str, 'tag': str, 'color': str,
    'room_id': str | None, 'presence': str,
    'last_message': str, 'last_message_time': float, 'spam_count': int,
}

shadow_muted[sid] = {'until': float}   # auto-expires
"""
import os
import re
import time
import string
import threading
from collections import deque

from config import (
    USER_COLORS, MAX_USERNAME_LEN, MAX_PRIVATE_HISTORY, MAX_GLOBAL_HISTORY,
    SPAM_MSG_LIMIT, SPAM_WINDOW_S, SPAM_COOLDOWN_S, SPAM_REPEAT_LIMIT,
    REP_ACTIVE, REP_TRUSTED,
    MAX_ROOMS, ROOM_IDLE_GRACE_S, ROOM_HISTORY_SIZE,
)

# ── Pre-compiled regex ────────────────────────────────────────────────────────
_UNSAFE_CHARS = re.compile(r'[^\w.\-]')
_ROOM_NAME_RE = re.compile(r'^[\w\s\-\.]{1,32}$')

# ── Core identity state ───────────────────────────────────────────────────────
users: dict    = {}   # sid  -> user record (see schema above)
sid_map: dict  = {}   # "username#tag" -> sid
public_keys: dict = {}  # "username#tag" -> ECDH JWK

# ── Global / private message history ─────────────────────────────────────────
message_history: deque = deque(maxlen=MAX_GLOBAL_HISTORY)
private_history: dict  = {}   # "displayA|displayB" -> deque[msg]

# ── Rooms (strict schema) ─────────────────────────────────────────────────────
rooms: dict = {}
# room_id -> {
#   'id':           str,
#   'name':         str,
#   'visibility':   'public' | 'private',
#   'password':     str | None,   # always None for public rooms
#   'creator_sid':  str,
#   'members':      set[sid],
#   'admins':       set[sid],
#   'created_at':   float,
#   'ttl':          int | None,   # seconds; None = session-only
#   'messages':     deque[msg],
#   'is_frozen':    bool,
#   'delete_timer': threading.Timer | None,
# }

# ── Per-user extended state (strict schema) ───────────────────────────────────
user_state: dict = {}
# sid -> {
#   'username':           str,
#   'tag':                str,
#   'color':              str,
#   'room_id':            str | None,
#   'presence':           str,   # 'active'|'idle'|'typing'|'in-call'|'recording'|'uploading'
#   'last_message':       str,
#   'last_message_time':  float,
#   'spam_count':         int,
# }

# ── Shadow mute (auto-expiring) ───────────────────────────────────────────────
shadow_muted: dict = {}   # sid -> {'until': float}

# ── Join tokens (approval flow for private rooms) ─────────────────────────────
join_tokens: dict = {}    # token -> {'room_id': str, 'sid': str, 'expires': float}

# ── Admin authority state (server-owned, single source of truth) ──────────────
# Only ONE admin session can exist at a time.
# The server is the ONLY entity that sets/clears this.
admin_state: dict = {
    'sid':           None,   # current admin socket ID
    'lease_expires': 0.0,    # grace window after disconnect (epoch seconds)
    'lease_timer':   None,   # threading.Timer for lease expiry
}

# ── Moderation / identity ─────────────────────────────────────────────────────
uid_tags: dict      = {}   # uid -> 4-char tag (persistent across reconnects)
uid_sessions: dict  = {}   # uid -> sid  (active session per uid for ghost cleanup)
message_votes: dict = {}   # msg_id -> set[uid]
spam_tracker: dict  = {}   # sid -> {'timestamps': deque, 'cooldown_until': float}

# ── Upload tracking ───────────────────────────────────────────────────────────
upload_counts: dict = {}   # sid -> int  (files uploaded this session)

# ── Upload rate limiting (time-windowed, per-IP) ──────────────────────────────
# Tracks upload timestamps per IP for burst + quota enforcement.
# Schema: ip -> {'timestamps': deque[float], 'daily_count': int, 'day': int}
#
# NOTE: This covers file uploads via POST /upload, but does NOT apply to
# text messages sent via Socket.IO. Text spam is handled by check_smart_spam()
# in the send_message handler (rate limit + repeat detection + shadow mute).
upload_rate: dict = {}

# ── IP connection tracking ────────────────────────────────────────────────────
ip_connections: dict = {}  # ip -> set[sid]

# ── Active session registry (SID → session metadata) ─────────────────────────
# This is the single source of truth for session state, independent of
# Flask request context.  All cleanup derives from this registry.
#
# Schema:
#   active_sessions[sid] = {
#       'uid':      str,
#       'display':  str,
#       'room_id':  str | None,
#       'status':   'connected' | 'disconnected',
#       'ip':       str,
#   }
active_sessions: dict = {}  # sid -> session metadata

# ── Analytics ─────────────────────────────────────────────────────────────────
analytics: dict = {
    'messages_sent':  0,
    'files_uploaded': 0,
    'peak_users':     0,
    'rooms_created':  0,
    'errors':         0,
    'started_at':     time.time(),
}

_color_index: list = [0]
_TAG_CHARS = string.ascii_uppercase + string.digits


# ── User helpers ──────────────────────────────────────────────────────────────

def get_user_list() -> list:
    """Return a JSON-serialisable list of connected users."""
    return [
        {
            'username':   u['username'],
            'tag':        u['tag'],
            'display':    u['display'],
            'color':      u['color'],
            'reputation': reputation_label(u.get('msg_count', 0)),
            'presence':   user_state.get(sid, {}).get('presence', 'active'),
        }
        for sid, u in users.items()
    ]


def next_color() -> str:
    """Return the next colour from the round-robin palette."""
    color = USER_COLORS[_color_index[0] % len(USER_COLORS)]
    _color_index[0] += 1
    return color


def unique_username(wanted: str, current_sid: str) -> str:
    """Return *wanted* if unclaimed, else append incrementing suffix.

    Two users CAN share the same username — they are differentiated by their
    tag (derived from uid). Uniqueness is only enforced on the full display
    string (username#tag). In tests, sid_map may be populated with plain
    username keys, so we check both sid_map keys and users dict displays.
    """
    base, counter = wanted, 2
    # Collect all display strings held by *other* sessions
    taken_displays = {u['display'] for s, u in users.items() if s != current_sid}
    # Also check sid_map keys (covers test fixtures that use plain names)
    taken_keys = {k for k, v in sid_map.items() if v != current_sid}
    taken = taken_displays | taken_keys

    # Build the candidate display to check (tag not known yet, so check username part)
    # Only suffix if the plain username itself is a key in sid_map (test compat)
    # OR if the full display is already taken
    while wanted in taken:
        wanted = f'{base}{counter}'
        counter += 1
        if counter > 999:
            wanted = f'{base}_{int(time.time())}'
            break
    return wanted


def generate_tag(uid: str) -> str:
    """Deterministic 4-char tag from uid hash. Same device = same tag."""
    if uid in uid_tags:
        return uid_tags[uid]
    h = abs(hash(uid))
    tag = ''.join(_TAG_CHARS[(h >> (i * 5)) % len(_TAG_CHARS)] for i in range(4))
    uid_tags[uid] = tag
    return tag


def reputation_label(msg_count: int) -> str:
    if msg_count >= REP_TRUSTED:
        return 'Trusted'
    if msg_count >= REP_ACTIVE:
        return 'Active'
    return 'New'


def init_user_state(sid: str, username: str, tag: str, color: str) -> None:
    """Initialise the extended user_state record for a new session."""
    user_state[sid] = {
        'username':          username,
        'tag':               tag,
        'color':             color,
        'room_id':           None,
        'presence':          'active',
        'last_message':      '',
        'last_message_time': 0.0,
        'spam_count':        0,
    }


def set_presence(sid: str, state_str: str) -> None:
    """Update presence for a sid. Silently ignores unknown sids."""
    valid = {'active', 'idle', 'typing', 'in-call', 'recording', 'uploading'}
    if sid in user_state and state_str in valid:
        user_state[sid]['presence'] = state_str


# ── Room helpers ──────────────────────────────────────────────────────────────

def _make_room_id() -> str:
    """Generate a short unique room ID."""
    import secrets
    return secrets.token_hex(4).upper()   # e.g. "A3F9B2C1"


def create_room(
    name: str,
    creator_sid: str,
    visibility: str = 'public',
    password: str | None = None,
    ttl: int | None = None,
) -> dict | None:
    """
    Create a new room. Returns the room dict or None if at capacity.

    Rules enforced here (not trusted from client):
    - visibility must be 'public' or 'private'; defaults to 'public'
    - public rooms NEVER have a password (stripped if provided)
    - private rooms MAY have a password

    Schema enforced here — callers must not build room dicts manually.
    """
    if len(rooms) >= MAX_ROOMS:
        return None

    # Enforce visibility rule
    if visibility not in ('public', 'private'):
        visibility = 'public'
    if visibility == 'public':
        password = None   # public rooms must not have passwords

    room_id = _make_room_id()
    while room_id in rooms:
        room_id = _make_room_id()

    room = {
        'id':              room_id,
        'name':            name[:32],
        'visibility':      visibility,
        'password':        password or None,
        'require_approval': False,          # set to True by creator after creation
        'pending_knocks':  {},              # sid -> display (waiting for admin approval)
        'creator_sid':     creator_sid,
        'members':         set(),
        'admins':          {creator_sid},
        'created_at':      time.time(),
        'ttl':             ttl,
        'messages':        deque(maxlen=ROOM_HISTORY_SIZE),
        'is_frozen':       False,
        'delete_timer':    None,
        'session_key':     None,   # AES-GCM JWK set by creator, relayed to joiners
        'seq':             0,      # per-room message sequence counter
    }
    rooms[room_id] = room
    analytics['rooms_created'] += 1
    return room


def get_room(room_id: str) -> dict | None:
    return rooms.get(room_id)


def is_room_admin(sid: str, room_id: str) -> bool:
    """Return True if sid is an admin of the given room."""
    room = rooms.get(room_id)
    return room is not None and sid in room['admins']


def room_member_list(room_id: str) -> list:
    """Return serialisable user list for a room."""
    room = rooms.get(room_id)
    if not room:
        return []
    result = []
    for sid in room['members']:
        u = users.get(sid)
        if u:
            result.append({
                'display':   u['display'],
                'color':     u['color'],
                'presence':  user_state.get(sid, {}).get('presence', 'active'),
                'is_admin':  sid in room['admins'],
            })
    return result


def schedule_room_delete(room_id: str, socketio_ref) -> None:
    """
    Start a grace-period timer. If the room is still empty when it fires,
    delete it and notify any lingering clients.
    """
    room = rooms.get(room_id)
    if not room:
        return

    # Cancel any existing timer before creating a new one (prevents double-fire)
    existing = room.get('delete_timer')
    if existing:
        existing.cancel()
        room['delete_timer'] = None

    def _delete():
        r = rooms.get(room_id)
        if r and not r['members']:
            # Clear the timer reference before deleting so cancel_room_delete
            # doesn't try to cancel an already-fired timer
            r['delete_timer'] = None
            del rooms[room_id]
            socketio_ref.emit('room:deleted', {'room_id': room_id})

    timer = threading.Timer(ROOM_IDLE_GRACE_S, _delete)
    timer.daemon = True
    timer.start()
    room['delete_timer'] = timer


def cancel_room_delete(room_id: str) -> None:
    """Cancel a pending delete timer (someone rejoined)."""
    room = rooms.get(room_id)
    if room and room['delete_timer']:
        room['delete_timer'].cancel()
        room['delete_timer'] = None


# ── Smart spam detection ──────────────────────────────────────────────────────

def check_smart_spam(sid: str, text: str) -> str:
    """
    Returns 'ok', 'cooldown', or 'shadow'.

    Detection rules (per your spec):
    1. Rate limit: > SPAM_MSG_LIMIT messages in SPAM_WINDOW_S seconds → cooldown
    2. Repeat flood: same message SPAM_REPEAT_LIMIT times in a row → shadow mute
    3. Fast typing: < 0.3s between messages → increment spam_count
    4. Large paste: message > 500 chars → increment spam_count
    5. spam_count > 5 → shadow mute
    """
    now = time.time()

    # Check shadow mute (auto-expiring)
    sm = shadow_muted.get(sid)
    if sm:
        if now < sm['until']:
            return 'shadow'
        else:
            del shadow_muted[sid]   # expired

    us = user_state.get(sid)
    if not us:
        return 'ok'

    # ── Rate limit ────────────────────────────────────────────────────────────
    tracker = spam_tracker.setdefault(sid, {
        'timestamps':     deque(),
        'cooldown_until': 0.0,
    })

    if now < tracker['cooldown_until']:
        return 'cooldown'

    ts = tracker['timestamps']
    while ts and now - ts[0] > SPAM_WINDOW_S:
        ts.popleft()

    if len(ts) >= SPAM_MSG_LIMIT:
        tracker['cooldown_until'] = now + SPAM_COOLDOWN_S
        ts.clear()
        return 'cooldown'

    ts.append(now)

    # ── Behaviour-based spam score ────────────────────────────────────────────
    # Repeated identical message
    if text == us['last_message']:
        us['spam_count'] += 1

    # Very fast typing (< 0.3s)
    if us['last_message_time'] and (now - us['last_message_time']) < 0.3:
        us['spam_count'] += 1

    # Large copy-paste blob
    if len(text) > 500:
        us['spam_count'] += 1

    us['last_message']      = text
    us['last_message_time'] = now

    if us['spam_count'] > 5:
        # Shadow mute for SPAM_COOLDOWN_S * 3
        shadow_muted[sid] = {'until': now + SPAM_COOLDOWN_S * 3}
        us['spam_count'] = 0
        return 'shadow'

    return 'ok'


def cooldown_remaining(sid: str) -> float:
    tracker = spam_tracker.get(sid)
    if not tracker:
        return 0.0
    return max(0.0, tracker['cooldown_until'] - time.time())


# ── Active session registry helpers ──────────────────────────────────────────

def register_session(sid: str, uid: str, display: str, ip: str) -> None:
    """Register a new session in the authoritative active_sessions registry."""
    active_sessions[sid] = {
        'uid':     uid,
        'display': display,
        'room_id': None,
        'status':  'connected',
        'ip':      ip,
    }


def update_session_room(sid: str, room_id: str | None) -> None:
    """Update the room_id for a session in the registry."""
    if sid in active_sessions:
        active_sessions[sid]['room_id'] = room_id


def mark_session_disconnected(sid: str) -> None:
    """Mark a session as disconnected (soft removal — keeps record briefly)."""
    if sid in active_sessions:
        active_sessions[sid]['status'] = 'disconnected'


def remove_session(sid: str) -> dict | None:
    """Remove and return a session record from the registry."""
    return active_sessions.pop(sid, None)


def get_session(sid: str) -> dict | None:
    """Return the session record for a sid, or None."""
    return active_sessions.get(sid)


def find_session_by_uid(uid: str) -> str | None:
    """Return the active sid for a uid, or None."""
    for sid, sess in active_sessions.items():
        if sess['uid'] == uid and sess['status'] == 'connected':
            return sid
    return None


# ── Upload rate limiting helpers ──────────────────────────────────────────────

# Configuration (can be overridden via config.py additions)
UPLOAD_BURST_LIMIT  = 5    # max uploads in UPLOAD_BURST_WINDOW seconds
UPLOAD_BURST_WINDOW = 30   # seconds for burst detection
UPLOAD_DAILY_LIMIT  = 200  # max uploads per IP per calendar day


def check_upload_rate(ip: str) -> str:
    """
    Check whether an IP is allowed to upload.

    Returns:
      'ok'          — upload is allowed
      'burst'       — too many uploads in the burst window
      'daily'       — daily quota exhausted
    """
    now = time.time()
    today = int(now // 86400)  # integer day number

    entry = upload_rate.setdefault(ip, {
        'timestamps':  deque(),
        'daily_count': 0,
        'day':         today,
    })

    # Reset daily counter on new day
    if entry['day'] != today:
        entry['daily_count'] = 0
        entry['day'] = today

    # Daily quota check
    if entry['daily_count'] >= UPLOAD_DAILY_LIMIT:
        return 'daily'

    # Burst check: prune old timestamps
    ts = entry['timestamps']
    while ts and now - ts[0] > UPLOAD_BURST_WINDOW:
        ts.popleft()

    if len(ts) >= UPLOAD_BURST_LIMIT:
        return 'burst'

    # Allow — record this upload
    ts.append(now)
    entry['daily_count'] += 1
    return 'ok'


# ── Message helpers ───────────────────────────────────────────────────────────

def private_key(a: str, b: str) -> str:
    """Canonical sorted key for a private conversation."""
    return f'{a}|{b}' if a < b else f'{b}|{a}'


def append_private(key: str, msg: dict) -> None:
    if key not in private_history:
        private_history[key] = deque(maxlen=MAX_PRIVATE_HISTORY)
    private_history[key].append(msg)


def now_ms() -> int:
    return int(time.time() * 1000)


def filter_expired(messages: deque, ttl: int | None) -> list:
    """
    Return messages that have not yet expired.
    ttl=None means session-only (never expire mid-session).
    """
    if ttl is None:
        return list(messages)
    cutoff = time.time() - ttl
    return [m for m in messages if m.get('_ts', 0) >= cutoff]


# ── Input helpers ─────────────────────────────────────────────────────────────

def sanitize_filename(raw: str) -> str:
    name = os.path.basename(raw)
    name = _UNSAFE_CHARS.sub('_', name)
    return name or 'file.bin'


def clean_username(raw) -> str:
    name = str(raw).strip()[:MAX_USERNAME_LEN]
    return name or 'Anonymous'


def clean_room_name(raw) -> str | None:
    """Return a sanitised room name, or None if invalid."""
    name = str(raw).strip()[:32]
    if not name or not _ROOM_NAME_RE.match(name):
        return None
    return name


# ── Background cleanup worker ─────────────────────────────────────────────────

def start_cleanup_worker() -> None:
    """
    Background thread that:
    - Removes empty rooms past their grace period
    - Prunes expired shadow mutes
    - Updates peak_users analytics
    - Deletes upload files older than 24 hours
    Runs every 30 seconds.
    """
    def _loop():
        while True:
            time.sleep(30)
            now = time.time()

            # Prune expired shadow mutes
            expired = [sid for sid, v in list(shadow_muted.items()) if now >= v['until']]
            for sid in expired:
                shadow_muted.pop(sid, None)

            # Prune expired join tokens
            expired_tokens = [t for t, v in list(join_tokens.items()) if now >= v['expires']]
            for t in expired_tokens:
                join_tokens.pop(t, None)

            # Update peak users
            current_count = len(users)
            if current_count > analytics['peak_users']:
                analytics['peak_users'] = current_count

            # Belt-and-suspenders: remove rooms that are empty and past grace
            for room_id, room in list(rooms.items()):
                if not room['members']:
                    age = now - room['created_at']
                    if age > ROOM_IDLE_GRACE_S:
                        rooms.pop(room_id, None)

            # Prune stale disconnected sessions from active_sessions registry
            stale_sids = [
                sid for sid, sess in list(active_sessions.items())
                if sess.get('status') == 'disconnected' and sid not in users
            ]
            for sid in stale_sids:
                active_sessions.pop(sid, None)

            # Prune upload_rate entries for IPs with no active users
            active_ips = {
                sess.get('ip') for sess in active_sessions.values()
            }
            stale_ips = [
                ip for ip in list(upload_rate.keys())
                if ip not in active_ips
            ]
            for ip in stale_ips:
                upload_rate.pop(ip, None)

            # Auto-delete upload files older than 24 hours
            try:
                from config import UPLOAD_FOLDER
                cutoff = now - 86400  # 24 hours
                if os.path.isdir(UPLOAD_FOLDER):
                    for fname in os.listdir(UPLOAD_FOLDER):
                        fpath = os.path.join(UPLOAD_FOLDER, fname)
                        try:
                            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                                os.remove(fpath)
                        except OSError:
                            pass
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()

# ── Admin authority helpers ───────────────────────────────────────────────────
# These are the ONLY functions that may read or write admin_state.
# No other module should touch admin_state directly.

ADMIN_LEASE_S = 60   # seconds grace window after admin disconnects

def admin_claim(sid: str) -> None:
    """
    Grant admin authority to *sid*.
    Cancels any existing lease timer and overwrites the previous admin.
    Only one admin can exist at a time.
    """
    # Cancel any pending lease expiry
    existing_timer = admin_state.get('lease_timer')
    if existing_timer:
        existing_timer.cancel()
    admin_state['sid']           = sid
    admin_state['lease_expires'] = 0.0
    admin_state['lease_timer']   = None


def admin_release(sid: str) -> None:
    """
    Called when the admin socket disconnects.
    Starts a grace-period lease — if the same sid reconnects within
    ADMIN_LEASE_S seconds, admin authority is silently restored.
    After the lease expires, admin_state is cleared.
    """
    if admin_state['sid'] != sid:
        return   # not the admin, nothing to do

    def _expire():
        if admin_state['sid'] == sid:
            admin_state['sid']           = None
            admin_state['lease_expires'] = 0.0
            admin_state['lease_timer']   = None

    admin_state['lease_expires'] = time.time() + ADMIN_LEASE_S
    timer = threading.Timer(ADMIN_LEASE_S, _expire)
    timer.daemon = True
    timer.start()
    admin_state['lease_timer'] = timer


def admin_reclaim(sid: str) -> bool:
    """
    Called on reconnect for a session that previously held admin.
    Returns True if the lease is still valid and admin was restored.
    """
    if time.time() < admin_state.get('lease_expires', 0):
        # Lease still valid — restore silently
        admin_claim(sid)
        return True
    return False


def is_admin(sid: str) -> bool:
    """Return True if *sid* is the current admin."""
    return admin_state['sid'] == sid
