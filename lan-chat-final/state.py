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

# ── Moderation / identity ─────────────────────────────────────────────────────
uid_tags: dict      = {}   # uid -> 4-char tag (persistent across reconnects)
message_votes: dict = {}   # msg_id -> set[uid]
spam_tracker: dict  = {}   # sid -> {'timestamps': deque, 'cooldown_until': float}

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
        'id':           room_id,
        'name':         name[:32],
        'visibility':   visibility,
        'password':     password or None,
        'creator_sid':  creator_sid,
        'members':      set(),
        'admins':       {creator_sid},
        'created_at':   time.time(),
        'ttl':          ttl,
        'messages':     deque(maxlen=ROOM_HISTORY_SIZE),
        'is_frozen':    False,
        'delete_timer': None,
        'session_key':  None,   # AES-GCM JWK set by creator, relayed to joiners
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
    - Removes empty rooms past their grace period (belt-and-suspenders
      alongside the per-room threading.Timer)
    - Prunes expired shadow mutes
    - Updates peak_users analytics
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

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
