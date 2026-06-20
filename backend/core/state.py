# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
state.py — Shared in-memory state and pure helper functions.

All mutable state lives here so every other module imports from one place.
Nothing in this module imports from Flask or Socket.IO, keeping it testable
in isolation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTITY AUTHORITY HIERARCHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

There is ONE source of truth per concern.  All other structures are derived
caches that must be kept in sync through the accessor functions below.

  users[sid]            ← PRIMARY record for all per-session mutable state.
                          This is the single source of truth for:
                            - identity  (username, tag, display, uid, color)
                            - room      (room_id)
                            - presence  (presence, last_message, spam_count …)
                            - flags     (is_server_admin, msg_count …)
                          WRITE via: users[sid][key] = value  (direct, it's the primary)
                          READ  via: users.get(sid)

  user_state[sid]       ← ALIAS pointing at the same dict as users[sid].
                          Exists only for backward-compat with code that reads
                          user_state[sid]['presence'] etc.
                          DO NOT write to user_state directly — write to users.
                          WRITE via: set_presence(), set_user_room() etc.
                          READ  via: user_state.get(sid)  (same object as users[sid])

  sid_map[display]      ← DERIVED reverse index: display → sid.
                          WRITE via: register_identity() / unregister_identity()
                          READ  via: sid_map.get(display)

  uid_sessions[uid]     ← DERIVED reverse index: uid → sid.
                          WRITE via: register_identity() / unregister_identity()
                          READ  via: uid_sessions.get(uid)

  active_sessions[sid]  ← DISCONNECT-SAFE thin view used only during teardown
                          when the users dict entry may already be popped.
                          Contains: uid, display, room_id, status, ip.
                          WRITE via: register_session() / update_session_room()
                          READ  via: get_session(sid)

  session_tokens[uid]   ← INDEPENDENT concern (reconnect auth). Not an alias.

Rule: if you need to write room_id for a session, call set_user_room(sid, x).
Rule: if you need to write sid_map or uid_sessions, call register_identity().
Rule: never write user_state[sid] directly — it's an alias for users[sid].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Schema reference
----------------
users[sid] = {
    # identity
    'username': str, 'tag': str, 'display': str, 'uid': str,
    'color': str, 'joined_at': float, 'msg_count': int,
    'is_server_admin': bool, 'persona': str | None,
    # room (single source of truth — also mirrored in active_sessions)
    'room_id': str | None,
    # presence & spam (previously in user_state — now merged here)
    'presence': str,
    'last_message': str, 'last_message_time': float, 'spam_count': int,
}

rooms[room_id] = {
    'id':           str,
    'name':         str,
    'visibility':   'public' | 'private',
    'password':     str | None,
    'creator_sid':  str,
    'members':      set[sid],
    'admins':       set[sid],
    'created_at':   float,
    'ttl':          int | None,
    'messages':     deque[msg],
    'is_frozen':    bool,
    'delete_timer': Timer | None,
}

active_sessions[sid] = {
    'uid':      str,
    'display':  str,
    'room_id':  str | None,
    'status':   'connected' | 'disconnected',
    'ip':       str,
}

shadow_muted[sid] = {'until': float}
"""
import os
import re
import time
import string
import threading
import asyncio
import secrets
from collections import deque

# Import from V2 config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    USER_COLORS, MAX_USERNAME_LEN, MAX_PRIVATE_HISTORY, MAX_GLOBAL_HISTORY,
    SPAM_MSG_LIMIT, SPAM_WINDOW_S, SPAM_WINDOW_S_PUBLIC, SPAM_COOLDOWN_S, SPAM_REPEAT_LIMIT,
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

# ── Per-user extended state ───────────────────────────────────────────────────
# user_state is a PROXY that returns the same dict object as users[sid].
# This means user_state[sid] IS users[sid] — they share the same reference.
# Code that reads user_state[sid]['presence'] continues to work unchanged.
# Code that writes should use set_presence() / set_user_room() instead of
# writing to user_state directly.
#
# The proxy is implemented as a simple class that delegates to users.

class _UserStateProxy:
    """
    Transparent proxy over users dict.
    user_state[sid] returns users[sid] — the same dict object.
    Supports: __getitem__, __setitem__, __delitem__, get, pop, __contains__,
              __iter__, items, keys, values, clear, setdefault.
    """
    def __getitem__(self, sid):
        return users[sid]

    def __setitem__(self, sid, value):
        # Called by init_user_state — merge fields into users[sid] instead of
        # creating a separate dict.  If users[sid] already exists, update it;
        # otherwise store as-is (test fixtures may call this before users[sid]).
        if sid in users:
            users[sid].update(value)
        else:
            users[sid] = value

    def __delitem__(self, sid):
        # user_state.pop(sid) / del user_state[sid] — no-op if users already
        # removed the entry (disconnect path pops users first).
        users.pop(sid, None)

    def get(self, sid, default=None):
        return users.get(sid, default)

    def pop(self, sid, *args):
        # Disconnect path calls user_state.pop(sid, None).
        # user_state IS users — pop from users directly.
        return users.pop(sid, *args)

    def __contains__(self, sid):
        return sid in users

    def __iter__(self):
        return iter(users)

    def items(self):
        return users.items()

    def keys(self):
        return users.keys()

    def values(self):
        return users.values()

    def clear(self):
        # Called by reset_runtime_state — users.clear() handles the actual wipe.
        pass   # no-op: users.clear() is called separately in reset_runtime_state

    def setdefault(self, sid, default=None):
        if sid not in users:
            users[sid] = default
        return users[sid]

    def __len__(self):
        return len(users)


user_state: _UserStateProxy = _UserStateProxy()

# ── Shadow mute (auto-expiring) ───────────────────────────────────────────────
shadow_muted: dict = {}   # sid -> {'until': float}

# ── Join tokens (approval flow for private rooms) ─────────────────────────────
join_tokens: dict = {}    # token -> {'room_id': str, 'sid': str, 'expires': float}

# ── Session tokens (Fix B) ────────────────────────────────────────────────────
# Maps uid -> {'token': str, 'issued_at': float, 'expires_at': float, 'ip': str}
# Issued on first join; must be presented on reconnect to reclaim the same uid.
# Bound to the issuing IP — token stolen from another device is rejected.
# Without a valid token, a reconnecting client gets a fresh uid (new identity).
session_tokens: dict = {}   # uid -> token record

SESSION_TOKEN_TTL_S = int(os.environ.get('SESSION_TOKEN_TTL_S', str(24 * 3600)))  # 24h default

# ── Active calls (Fix A) ──────────────────────────────────────────────────────
# Maps call_id -> set of sids currently in that call.
# A call_id is the room_id for room calls, or a sorted "sidA|sidB" key for DM calls.
active_calls: dict = {}   # call_id -> set[sid]

# ── Call session immutability (Fix 5) ─────────────────────────────────────────
# call_sessions: maps call_id -> session_uuid (str).
#   A session_uuid is minted when the first offer is accepted.
#   Every subsequent signal (answer, ice, end) must carry a matching session_id
#   field.  Signals with a missing or wrong session_id are dropped — this
#   prevents late/stale signals from a previous negotiation round from mutating
#   live call state.
#
# open_call: maps sid -> call_id.
#   Tracks which call_id a SID currently holds an open offer for.
#   A SID may only be the offerer of ONE call at a time.  A second offer from
#   the same SID while open_call[sid] is set is rejected (offer lock / glare
#   guard).  The entry is cleared when the call ends or the SID disconnects.
call_sessions: dict = {}   # call_id -> session_uuid
open_call:     dict = {}   # sid     -> call_id  (offer lock)

# ── Negotiation phase FSM (Fix 6) ─────────────────────────────────────────────
# call_phase: maps call_id -> one of the _CallPhase string constants below.
#
# Valid transitions (enforced server-side):
#
#   (none)      --[offer]-->   OFFERED
#   OFFERED     --[answer]--> ANSWERED
#   ANSWERED    --[ice]-->    CONNECTING
#   CONNECTING  --[ice]-->    CONNECTING   (self-loop, ICE trickle)
#   ACTIVE      --[ice]-->    ACTIVE       (ICE restart)
#   ANSWERED    --[end/reject]--> CLOSED
#   CONNECTING  --[end/reject]--> CLOSED
#   ACTIVE      --[end/reject]--> CLOSED
#   OFFERED     --[end/reject]--> CLOSED   (caller hung up before answer)
#
# Signals that arrive out of order are silently dropped with a sec_log warning.
# The CLOSED state is transient — it is removed from the dict immediately after
# teardown so the call_id can be reused for a fresh negotiation.
call_phase: dict = {}   # call_id -> str (phase constant)

# Phase constants — kept as plain strings so they serialise cleanly in logs.
_CP_OFFERED    = 'OFFERED'
_CP_ANSWERED   = 'ANSWERED'
_CP_CONNECTING = 'CONNECTING'
_CP_ACTIVE     = 'ACTIVE'
_CP_CLOSED     = 'CLOSED'

# ── Call tombstones (Fix 7 — reconnect identity bridge) ───────────────────────
# When a call tears down due to peer disconnect (NOT a clean end/reject), a
# tombstone is written so that if both peers reconnect within TOMBSTONE_TTL_S
# seconds, the new negotiation can inherit the old session_uuid.
#
# The client receives resume=True in the forwarded offer and knows to do an
# ICE restart rather than a full renegotiation — no "call reset" flash.
#
# Schema:
#   call_tombstones[tombstone_key] = {
#       'session_uuid': str,          # the uuid from the torn-down call
#       'uids':         frozenset,    # the two UIDs that were in the call
#       'phase':        str,          # phase at time of disconnect
#       'torn_at':      float,        # epoch timestamp
#   }
#
# tombstone_key = '|'.join(sorted(uids))  — UID-based, survives SID change
TOMBSTONE_TTL_S: int = 30   # seconds — covers typical reconnect window
call_tombstones: dict = {}   # tombstone_key -> tombstone record

# ── Duplicate message dedup (Phase 1) ────────────────────────────────────────
# Server-generated msg_ids are already unique, but clients may replay offline
# queue messages on reconnect causing duplicates.  We track recently-seen
# msg_ids and reject re-submissions within a rolling window.
# Schema: msg_id -> float (epoch when it was first accepted)
seen_msg_ids: dict = {}
SEEN_MSG_ID_TTL_S  = 300   # 5 minutes — enough to cover any reconnect window
SEEN_MSG_ID_MAX    = 10_000  # hard cap — prune oldest when exceeded

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


# ── Runtime state reset ───────────────────────────────────────────────────────

def reset_runtime_state() -> None:
    """
    Clear ALL volatile in-memory state in one call.

    Use cases:
      - Test fixtures (call before every test)
      - Admin endpoint (optional server soft-reset without restart)
      - Future: hot-reload without losing the process

    Does NOT touch:
      - analytics['started_at']  (uptime clock)
      - config constants          (immutable at import time)
      - background thread         (daemon, harmless)
    """
    # ── Identity & session ────────────────────────────────────────────────────
    users.clear()
    sid_map.clear()
    public_keys.clear()
    uid_tags.clear()
    uid_sessions.clear()
    session_tokens.clear()
    active_sessions.clear()
    ip_connections.clear()

    # ── Messages ──────────────────────────────────────────────────────────────
    message_history.clear()
    private_history.clear()
    seen_msg_ids.clear()
    # ── Rooms ─────────────────────────────────────────────────────────────────
    # Cancel any pending delete timers before wiping rooms
    for room in rooms.values():
        t = room.get('delete_timer')
        if t:
            t.cancel()
    rooms.clear()

    # ── Per-user state ────────────────────────────────────────────────────────
    # user_state is a proxy for users — clearing users is sufficient.
    # spam_tracker, shadow_muted, upload_counts are separate.
    spam_tracker.clear()
    shadow_muted.clear()
    upload_counts.clear()
    upload_rate.clear()

    # ── Tokens & votes ────────────────────────────────────────────────────────
    join_tokens.clear()
    message_votes.clear()

    # ── Calls ─────────────────────────────────────────────────────────────────
    active_calls.clear()

    # ── Admin lease ───────────────────────────────────────────────────────────
    t = admin_state.get('lease_timer')
    if t:
        t.cancel()
    admin_state['sid']           = None
    admin_state['lease_expires'] = 0.0
    admin_state['lease_timer']   = None

    # ── Color index ───────────────────────────────────────────────────────────
    _color_index[0] = 0

    # ── Analytics (preserve uptime, reset counters) ───────────────────────────
    analytics['messages_sent']  = 0
    analytics['files_uploaded'] = 0
    analytics['peak_users']     = 0
    analytics['rooms_created']  = 0
    analytics['errors']         = 0


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
    """
    Merge presence/spam fields into users[sid].

    Previously these lived in a separate user_state dict.  Now they are part
    of the primary users record — user_state is a proxy that returns users[sid].
    This function is called immediately after users[sid] is created in handle_join.
    """
    if sid in users:
        users[sid].setdefault('presence',          'active')
        users[sid].setdefault('last_message',      '')
        users[sid].setdefault('last_message_time', 0.0)
        users[sid].setdefault('spam_count',        0)


def set_presence(sid: str, state_str: str) -> None:
    """Update presence for a sid. Silently ignores unknown sids."""
    valid = {'active', 'idle', 'typing', 'in-call', 'recording', 'uploading'}
    if sid in users and state_str in valid:
        users[sid]['presence'] = state_str


# ── Consolidated identity write functions ─────────────────────────────────────
# These are the ONLY functions that may write to sid_map and uid_sessions.
# Direct writes to those dicts outside these functions are a bug.

def register_identity(sid: str, display: str, uid: str) -> None:
    """
    Write-through: update both reverse-index caches atomically.

    Call this whenever a session's display name or uid is established or
    changes (join, persona switch).  Never write sid_map or uid_sessions
    directly.
    """
    sid_map[display]   = sid
    uid_sessions[uid]  = sid


def unregister_identity(sid: str, display: str, uid: str) -> None:
    """
    Write-through: remove from both reverse-index caches atomically.

    Call this on disconnect or ghost eviction.  Only removes the entry if
    it still points to this sid (prevents clobbering a newer session's entry).
    """
    if sid_map.get(display) == sid:
        sid_map.pop(display, None)
    if uid_sessions.get(uid) == sid:
        uid_sessions.pop(uid, None)


def set_user_room(sid: str, room_id: str | None) -> None:
    """
    Single write point for a session's current room.

    Updates users[sid]['room_id'] AND active_sessions[sid]['room_id'] in one
    call.  Replaces the previous pattern of writing to three separate dicts.

    Call this instead of:
        users[sid]['room_id'] = x
        user_state[sid]['room_id'] = x   ← now a no-op alias
        update_session_room(sid, x)
    """
    if sid in users:
        users[sid]['room_id'] = room_id
    if sid in active_sessions:
        active_sessions[sid]['room_id'] = room_id


# ── Room helpers ──────────────────────────────────────────────────────────────

def _make_room_id() -> str:
    """Generate a short unique room ID."""
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
        'key_mode':        'relay',  # future: 'e2e' for end-to-end encrypted rooms
        'seq':             0,      # per-room message sequence counter
    }
    rooms[room_id] = room
    analytics['rooms_created'] += 1
    return room


def get_room(room_id: str) -> dict | None:
    return rooms.get(room_id)


def update_room(room_id: str, **kwargs) -> bool:
    """
    Central helper for mutating room state.
    Prevents scattered direct dict mutations across modules.
    Returns True if the room exists and was updated, False otherwise.

    Usage:
        update_room(room_id, session_key=jwk_dict)
        update_room(room_id, is_frozen=True)
    """
    room = rooms.get(room_id)
    if not room:
        return False
    for key, value in kwargs.items():
        room[key] = value
    return True


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
    Schedule an async grace-period task. If the room is still empty when it
    fires, delete it and notify all clients.

    Uses asyncio.ensure_future so the emit is properly awaited within the
    running event loop (uvicorn / python-socketio async mode).
    Falls back to threading.Timer in test environments with no running loop.
    """
    room = rooms.get(room_id)
    if not room:
        return

    # Cancel any existing timer/task before creating a new one
    existing = room.get('delete_timer')
    if existing is not None:
        try:
            existing.cancel()
        except Exception:
            pass
        room['delete_timer'] = None

    async def _async_delete():
        try:
            await asyncio.sleep(ROOM_IDLE_GRACE_S)
        except asyncio.CancelledError:
            return
        r = rooms.get(room_id)
        if r and not r['members']:
            r['delete_timer'] = None
            if not r['members']:   # double-check after clearing ref
                del rooms[room_id]
                await socketio_ref.emit('room:deleted', {'room_id': room_id})

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.ensure_future(_async_delete())
            room['delete_timer'] = task
            return
    except RuntimeError:
        pass

    # Fallback for test environments: threading.Timer (no actual emit)
    timer = threading.Timer(ROOM_IDLE_GRACE_S, lambda: None)
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

def check_smart_spam(sid: str, text: str, msg_limit: int = SPAM_MSG_LIMIT,
                     window_s: float | None = None) -> str:
    """
    Returns 'ok', 'cooldown', or 'shadow'.

    Detection rules (per your spec):
    1. Rate limit: > msg_limit messages in window_s seconds → cooldown
    2. Repeat flood: same message SPAM_REPEAT_LIMIT times in a row → shadow mute
    3. Fast typing: < 0.3s between messages → increment spam_count
    4. Large paste: message > 500 chars → increment spam_count
    5. spam_count > 5 → shadow mute

    msg_limit defaults to SPAM_MSG_LIMIT (LAN). Pass SPAM_MSG_LIMIT_PUBLIC
    and SPAM_WINDOW_S_PUBLIC from the caller when PUBLIC_MODE is active.
    """
    effective_window = window_s if window_s is not None else SPAM_WINDOW_S
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
    while ts and now - ts[0] > effective_window:
        ts.popleft()

    if len(ts) >= msg_limit:
        tracker['cooldown_until'] = now + SPAM_COOLDOWN_S
        ts.clear()
        return 'cooldown'

    ts.append(now)

    # ── Behaviour-based spam score ────────────────────────────────────────────
    # Decay: if the user has been quiet for 60+ seconds, reduce the score.
    # This prevents legitimate slow typists from accumulating a permanent ban.
    if us['last_message_time'] and (now - us['last_message_time']) > 60:
        us['spam_count'] = max(0, us['spam_count'] - 2)

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
    """
    Update the room_id for a session.
    Delegates to set_user_room() — kept for backward compatibility.
    Prefer calling set_user_room() directly in new code.
    """
    set_user_room(sid, room_id)


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


# ── Session token helpers (Fix B) ───────────────────────────────────────────────

import logging as _logging_mod
_sec_log = _logging_mod.getLogger('lan-chat.security')

def issue_session_token(uid: str, ip: str = '') -> str:
    """
    Issue a new session token for a uid, bound to the client IP.
    Overwrites any existing token (rotated on every successful join).
    Returns the raw token string to send to the client.
    """
    token = secrets.token_hex(24)
    now   = time.time()
    session_tokens[uid] = {
        'token':      token,
        'issued_at': now,
        'expires_at': now + SESSION_TOKEN_TTL_S,
        'ip':         ip,
    }
    return token


def verify_session_token(uid: str, token: str, ip: str = '') -> bool:
    """
    Return True if the token is valid for this uid, not expired, and
    (when ip is provided) matches the issuing IP.

    IP check is best-effort: if the stored ip is empty (legacy record or
    server restart) we skip the IP check rather than locking everyone out.
    """
    entry = session_tokens.get(uid)
    if not entry:
        _sec_log.warning('session_token: no token on record for uid=%.8s', uid)
        return False
    if time.time() > entry['expires_at']:
        session_tokens.pop(uid, None)
        _sec_log.warning('session_token: expired for uid=%.8s', uid)
        return False
    if entry['token'] != token:
        _sec_log.warning('session_token: wrong token for uid=%.8s ip=%s', uid, ip)
        return False
    # IP binding — only enforce when both sides have an IP recorded
    stored_ip = entry.get('ip', '')
    if ip and stored_ip and ip != stored_ip:
        _sec_log.warning(
            'session_token: IP mismatch for uid=%.8s stored=%s presented=%s',
            uid, stored_ip, ip,
        )
        return False
    return True


def revoke_session_token(uid: str) -> None:
    """Remove the session token for a uid (called on clean disconnect)."""
    session_tokens.pop(uid, None)


# ── Active call helpers (Fix A) ───────────────────────────────────────────────

def _call_key_for_room(room_id: str) -> str:
    return f'room:{room_id}'


def _call_key_for_dm(sid_a: str, sid_b: str) -> str:
    return '|'.join(sorted([sid_a, sid_b]))


def join_call(call_id: str, sid: str) -> None:
    """Add sid to a call."""
    active_calls.setdefault(call_id, set()).add(sid)


def leave_call(sid: str) -> str | None:
    """
    Remove sid from any call it is in.
    Returns the call_id that was affected (or None), so the caller can
    notify remaining participants of the teardown.
    Also clears the offer lock and call session for this sid/call.
    """
    for call_id in list(active_calls.keys()):
        if sid in active_calls[call_id]:
            active_calls[call_id].discard(sid)
            if not active_calls[call_id]:
                del active_calls[call_id]
                # Last participant gone — invalidate the session and phase too
                call_sessions.pop(call_id, None)
                call_phase.pop(call_id, None)
            # Always clear the offer lock for this sid
            open_call.pop(sid, None)
            return call_id
    # sid wasn't in any call — still clear any stale offer lock
    open_call.pop(sid, None)
    return None


def teardown_call(call_id: str) -> set:
    """
    Forcibly end a call and return the set of sids that were in it.
    Used when a participant disconnects unexpectedly — the caller is
    responsible for notifying the returned sids.
    Also invalidates the call session, phase, and offer locks for all participants.
    """
    participants = active_calls.pop(call_id, set())
    call_sessions.pop(call_id, None)
    call_phase.pop(call_id, None)
    for sid in participants:
        open_call.pop(sid, None)
    return participants


def in_same_call(sid_a: str, sid_b: str) -> bool:
    """Return True if both sids are in the same active call."""
    for participants in active_calls.values():
        if sid_a in participants and sid_b in participants:
            return True
    return False


def get_call_for_sid(sid: str) -> str | None:
    """Return the call_id the sid is currently in, or None."""
    for call_id, participants in active_calls.items():
        if sid in participants:
            return call_id
    return None


# ── Call session immutability helpers (Fix 5) ────────────────────────────────

def create_call_session(call_id: str) -> str:
    """
    Mint a new session_uuid for call_id and store it.
    Returns the uuid.  Overwrites any existing entry — only called when a
    fresh offer is accepted (after the offer-lock check passes).
    """
    session_uuid = secrets.token_hex(16)
    call_sessions[call_id] = session_uuid
    return session_uuid


def get_call_session_id(call_id: str) -> str | None:
    """Return the current session_uuid for call_id, or None if not found."""
    return call_sessions.get(call_id)


def invalidate_call_session(call_id: str) -> None:
    """Remove the session_uuid for call_id (called on end/reject/teardown)."""
    call_sessions.pop(call_id, None)


def is_offer_locked(sid: str) -> bool:
    """
    Return True if sid already has an open outgoing offer.
    A SID may only hold one active offer at a time (glare guard).
    """
    return sid in open_call


def set_offer_lock(sid: str, call_id: str) -> None:
    """Record that sid is the offerer for call_id."""
    open_call[sid] = call_id


def clear_offer_lock(sid: str) -> None:
    """Remove the offer lock for sid (called on end/reject/teardown/disconnect)."""
    open_call.pop(sid, None)


# ── Negotiation phase FSM helpers (Fix 6) ────────────────────────────────────

def get_call_phase(call_id: str) -> str | None:
    """Return the current negotiation phase for call_id, or None if unknown."""
    return call_phase.get(call_id)


def advance_call_phase(call_id: str, signal_type: str) -> tuple[bool, str]:
    """
    Attempt to advance the FSM for call_id based on signal_type.

    Returns (allowed: bool, reason: str).
      allowed=True  → signal is permitted; phase has been updated.
      allowed=False → signal is out of order; caller must drop it.

    Transition table
    ----------------
    signal_type  current phase(s) allowed   → new phase
    -----------  ----------------------     -----------
    offer        None / CLOSED              → OFFERED
    answer       OFFERED                    → ANSWERED
    ice          ANSWERED                   → CONNECTING
                 CONNECTING                 → CONNECTING  (trickle)
                 ACTIVE                     → ACTIVE      (ICE restart)
    end/reject   any                        → CLOSED (then removed)
    """
    current = call_phase.get(call_id)

    if signal_type == 'offer':
        if current not in (None, _CP_CLOSED):
            return False, f'offer rejected: phase is {current!r} (expected None or CLOSED)'
        call_phase[call_id] = _CP_OFFERED
        return True, 'OFFERED'

    if signal_type == 'answer':
        if current != _CP_OFFERED:
            if current in (_CP_ANSWERED, _CP_CONNECTING, _CP_ACTIVE):
                # Duplicate answer — silently ignore, not an error
                return False, f'answer ignored: already in phase {current!r}'
            return False, f'answer rejected: phase is {current!r} (expected OFFERED)'
        call_phase[call_id] = _CP_ANSWERED
        return True, 'ANSWERED'

    if signal_type in ('ice', 'candidate'):
        if current == _CP_ANSWERED:
            call_phase[call_id] = _CP_CONNECTING
            return True, 'CONNECTING'
        if current in (_CP_CONNECTING, _CP_ACTIVE):
            return True, current   # self-loop, no phase change
        return False, f'ice rejected: phase is {current!r} (expected ANSWERED/CONNECTING/ACTIVE)'

    if signal_type in ('end', 'reject'):
        # Valid from any phase — always allowed
        call_phase.pop(call_id, None)
        return True, 'CLOSED'

    # Unknown signal type — pass through without phase enforcement
    return True, current or 'UNKNOWN'


def mark_call_active(call_id: str) -> None:
    """
    Promote a call from CONNECTING → ACTIVE.
    Called when the client signals that ICE has completed (e.g. 'connected'
    event forwarded as a status signal).  Optional — the FSM works correctly
    without this; it just stays in CONNECTING until end/reject.
    """
    if call_phase.get(call_id) == _CP_CONNECTING:
        call_phase[call_id] = _CP_ACTIVE


def reset_call_phase(call_id: str) -> None:
    """Remove the phase entry for call_id (called on teardown/disconnect)."""
    call_phase.pop(call_id, None)


# ── Call tombstone helpers (Fix 7 — reconnect identity bridge) ───────────────

def _tombstone_key(uid_a: str, uid_b: str) -> str:
    return '|'.join(sorted([uid_a, uid_b]))


def write_call_tombstone(uid_a: str, uid_b: str, session_uuid: str, phase: str) -> None:
    """
    Write a tombstone for a call that ended due to peer disconnect.
    Only called from the disconnect handler — NOT from clean end/reject.

    The tombstone lets the reconnecting peer inherit the old session_uuid
    so the client can do ICE restart instead of full renegotiation.
    """
    key = _tombstone_key(uid_a, uid_b)
    call_tombstones[key] = {
        'session_uuid': session_uuid,
        'uids':         frozenset([uid_a, uid_b]),
        'phase':        phase,
        'torn_at':      time.time(),
    }


def find_call_tombstone(uid_a: str, uid_b: str) -> dict | None:
    """
    Return a live tombstone for this UID pair, or None if expired/absent.
    Does NOT consume the tombstone — call consume_call_tombstone() after use.
    """
    key = _tombstone_key(uid_a, uid_b)
    entry = call_tombstones.get(key)
    if entry is None:
        return None
    if time.time() - entry['torn_at'] > TOMBSTONE_TTL_S:
        call_tombstones.pop(key, None)
        return None
    return entry


def consume_call_tombstone(uid_a: str, uid_b: str) -> dict | None:
    """
    Return and remove a live tombstone for this UID pair.
    Returns None if expired or absent.
    """
    key = _tombstone_key(uid_a, uid_b)
    entry = call_tombstones.pop(key, None)
    if entry is None:
        return None
    if time.time() - entry['torn_at'] > TOMBSTONE_TTL_S:
        return None
    return entry


def prune_call_tombstones() -> None:
    """Remove expired tombstones. Called by background cleanup worker."""
    cutoff = time.time() - TOMBSTONE_TTL_S
    stale = [k for k, v in list(call_tombstones.items()) if v['torn_at'] < cutoff]
    for k in stale:
        call_tombstones.pop(k, None)


# ── Duplicate message dedup helpers ──────────────────────────────────────────

def record_msg_id(msg_id: str) -> bool:
    """
    Record a msg_id as seen.  Returns True if this is a new id (allow),
    False if it was already seen (duplicate — reject).

    Also enforces the hard cap: if seen_msg_ids exceeds SEEN_MSG_ID_MAX,
    prune the oldest half before inserting.
    """
    now = time.time()
    if msg_id in seen_msg_ids:
        return False   # duplicate

    # Hard cap: prune oldest entries when we hit the limit
    if len(seen_msg_ids) >= SEEN_MSG_ID_MAX:
        cutoff = now - SEEN_MSG_ID_TTL_S
        to_prune = [k for k, v in seen_msg_ids.items() if v < cutoff]
        for k in to_prune:
            del seen_msg_ids[k]
        # If still over cap (all recent), drop oldest half by insertion order
        if len(seen_msg_ids) >= SEEN_MSG_ID_MAX:
            prune_count = len(seen_msg_ids) // 2
            for k in list(seen_msg_ids.keys())[:prune_count]:
                del seen_msg_ids[k]

    seen_msg_ids[msg_id] = now
    return True


# ── Background cleanup worker ──────────────────────────────────────────────────

async def _cleanup_loop() -> None:
    """Periodic pruning of expired in-memory state. Runs as an asyncio task."""
    while True:
        await asyncio.sleep(30)
        now = time.time()
        # Prune expired shadow mutes
        stale_sm = [sid for sid, v in list(shadow_muted.items()) if now > v.get('until', 0)]
        for sid in stale_sm:
            shadow_muted.pop(sid, None)
        # Prune expired session tokens
        stale_st = [uid for uid, v in list(session_tokens.items()) if now > v.get('expires_at', 0)]
        for uid in stale_st:
            session_tokens.pop(uid, None)
        # Prune expired join tokens
        stale_jt = [tok for tok, v in list(join_tokens.items()) if now > v.get('expires', 0)]
        for tok in stale_jt:
            join_tokens.pop(tok, None)
        # Prune call tombstones
        prune_call_tombstones()
        # Prune stale uid_sessions entries for disconnected users
        stale_us = [uid for uid, sid in list(uid_sessions.items()) if sid not in users]
        for uid in stale_us:
            if uid_sessions.get(uid) not in users:
                uid_sessions.pop(uid, None)


def start_cleanup_worker() -> None:
    """Schedule the cleanup coroutine on the running asyncio event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_cleanup_loop())
    except RuntimeError:
        pass
