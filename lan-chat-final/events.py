"""
events.py — Central event schema contract for LAN Chat.

Every Socket.IO event the server emits or handles is declared here with:
  - name:        the event string
  - direction:   'in' (client→server), 'out' (server→client), or 'both'
  - auth:        whether a joined session is required
  - scope:       'global' | 'room' | 'dm' | 'self' | 'broadcast'
  - payload:     dict of field → type-hint string (documentation only)

This module is import-only — it does NOT register handlers.
Use it as the authoritative reference when adding or auditing events.
"""

from typing import Any

# ── Schema entry ──────────────────────────────────────────────────────────────

class EventSchema:
    __slots__ = ('name', 'direction', 'auth', 'scope', 'payload', 'notes')

    def __init__(
        self,
        name: str,
        direction: str,
        auth: bool,
        scope: str,
        payload: dict[str, str],
        notes: str = '',
    ):
        self.name      = name
        self.direction = direction
        self.auth      = auth
        self.scope     = scope
        self.payload   = payload
        self.notes     = notes

    def __repr__(self) -> str:
        return f'<EventSchema {self.name!r} {self.direction} auth={self.auth}>'


# ── Registry ──────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, EventSchema] = {}


def _reg(schema: EventSchema) -> EventSchema:
    _REGISTRY[schema.name] = schema
    return schema


def get(name: str) -> EventSchema | None:
    """Look up a schema by event name."""
    return _REGISTRY.get(name)


def all_events() -> list[EventSchema]:
    """Return all registered schemas sorted by name."""
    return sorted(_REGISTRY.values(), key=lambda s: s.name)


def validate_payload(name: str, data: Any) -> list[str]:
    """
    Lightweight structural validation.
    Returns a list of error strings (empty = valid).
    Only checks that required keys are present; does not type-check values.
    """
    schema = _REGISTRY.get(name)
    if schema is None:
        return [f'Unknown event: {name!r}']
    if not isinstance(data, dict):
        return [f'{name}: payload must be a dict, got {type(data).__name__}']
    errors = []
    for field, hint in schema.payload.items():
        if hint.startswith('?'):
            continue   # optional field
        if field not in data:
            errors.append(f'{name}: missing required field {field!r}')
    return errors


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='join',
    direction='in',
    auth=False,
    scope='self',
    payload={
        'username':       'str',
        'uid':            '?str',
        'publicKey':      '?dict',
        'server_password':'?str',
    },
    notes='First event a client sends. Registers the session.',
))

_reg(EventSchema(
    name='joined',
    direction='out',
    auth=False,
    scope='self',
    payload={
        'username':        'str',
        'tag':             'str',
        'display':         'str',
        'color':           'str',
        'uid':             'str',
        'reputation':      'str',
        'is_server_admin': 'bool',
    },
))

_reg(EventSchema(
    name='disconnect',
    direction='in',
    auth=True,
    scope='broadcast',
    payload={},
    notes='Fired by Socket.IO engine on connection close.',
))

_reg(EventSchema(
    name='reconnect_sync',
    direction='in',
    auth=True,
    scope='self',
    payload={
        'last_seq':    '?int',
        'room_id':     '?str',
        'known_ids':   '?list[str]',
    },
    notes='Client sends after reconnect to request missed messages.',
))

_reg(EventSchema(
    name='sync_reply',
    direction='out',
    auth=True,
    scope='self',
    payload={
        'missed':      'list[dict]',
        'current_seq': 'int',
        'room_id':     '?str',
    },
    notes='Server replies with messages the client missed.',
))

# ─────────────────────────────────────────────────────────────────────────────
# MESSAGING
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='send_message',
    direction='in',
    auth=True,
    scope='global|room|dm',
    payload={
        'text':      'str',
        'to':        'str',
        'encrypted': '?str',
        'reply_to':  '?dict',
    },
))

_reg(EventSchema(
    name='new_message',
    direction='out',
    auth=True,
    scope='global|room|dm',
    payload={
        'type':       'str',
        'from':       'str',
        'color':      'str',
        'tag':        'str',
        'reputation': 'str',
        'text':       'str',
        'time':       'int',
        'to':         'str',
        'msg_id':     'str',
        'seq':        '?int',
        'encrypted':  '?str',
        'reply_to':   '?dict',
    },
))

_reg(EventSchema(
    name='send_file',
    direction='in',
    auth=True,
    scope='global|room|dm',
    payload={
        'url':       'str',
        'name':      'str',
        'file_type': 'str',
        'to':        'str',
    },
))

_reg(EventSchema(
    name='message:edit',
    direction='in',
    auth=True,
    scope='global|room|dm',
    payload={
        'msg_id': 'str',
        'text':   'str',
        'to':     'str',
        'from':   '?str',
    },
))

_reg(EventSchema(
    name='message:edited',
    direction='out',
    auth=True,
    scope='global|room|dm',
    payload={
        'msg_id':    'str',
        'text':      'str',
        'edited':    'bool',
        'to':        'str',
        'encrypted': '?str',
    },
))

_reg(EventSchema(
    name='message:delete',
    direction='in',
    auth=True,
    scope='global|room|dm',
    payload={
        'msg_id': 'str',
        'to':     'str',
        'from':   '?str',
    },
))

_reg(EventSchema(
    name='message:deleted',
    direction='out',
    auth=True,
    scope='global|room|dm',
    payload={
        'msg_id': 'str',
        'to':     'str',
    },
))

_reg(EventSchema(
    name='message:seen',
    direction='both',
    auth=True,
    scope='dm',
    payload={
        'msg_ids': 'list[str]',
        'sender':  '?str',
        'by':      '?str',
    },
    notes='Client sends {msg_ids, sender}; server relays {msg_ids, by} to sender.',
))

_reg(EventSchema(
    name='message_history',
    direction='out',
    auth=False,
    scope='self',
    payload={},
    notes='Array of message dicts sent on join.',
))

# ─────────────────────────────────────────────────────────────────────────────
# PRESENCE & TYPING
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='typing',
    direction='both',
    auth=True,
    scope='global|room|dm',
    payload={'to': 'str'},
))

_reg(EventSchema(
    name='stop_typing',
    direction='both',
    auth=True,
    scope='global|room|dm',
    payload={'to': 'str'},
))

_reg(EventSchema(
    name='user:presence',
    direction='both',
    auth=True,
    scope='broadcast',
    payload={
        'state':   '?str',
        'display': '?str',
    },
    notes='Client sends {state}; server broadcasts {display, state}.',
))

_reg(EventSchema(
    name='user:switch_persona',
    direction='in',
    auth=True,
    scope='broadcast',
    payload={
        'name':  'str',
        'color': '?str',
    },
))

_reg(EventSchema(
    name='persona_switched',
    direction='out',
    auth=True,
    scope='broadcast',
    payload={
        'old': 'str',
        'new': 'str',
    },
))

# ─────────────────────────────────────────────────────────────────────────────
# USER LIST & KEYS
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='user_list',
    direction='out',
    auth=False,
    scope='broadcast',
    payload={},
    notes='Array of user dicts.',
))

_reg(EventSchema(
    name='all_keys',
    direction='out',
    auth=False,
    scope='self',
    payload={},
    notes='Dict of display→JWK for all connected users.',
))

_reg(EventSchema(
    name='peer_key',
    direction='out',
    auth=False,
    scope='broadcast',
    payload={
        'username':  'str',
        'publicKey': 'dict',
    },
))

_reg(EventSchema(
    name='system_message',
    direction='out',
    auth=False,
    scope='broadcast',
    payload={
        'type': 'str',
        'text': 'str',
        'time': 'int',
    },
))

# ─────────────────────────────────────────────────────────────────────────────
# ROOMS
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='room:create',
    direction='in',
    auth=True,
    scope='self',
    payload={
        'name':             'str',
        'visibility':       '?str',
        'password':         '?str',
        'ttl':              '?str',
        'require_approval': '?bool',
    },
))

_reg(EventSchema(
    name='room:created',
    direction='out',
    auth=True,
    scope='self',
    payload={
        'room_id':    'str',
        'name':       'str',
        'visibility': 'str',
        'ttl':        '?int',
        'members':    'list',
        'is_admin':   'bool',
    },
))

_reg(EventSchema(
    name='room:join',
    direction='in',
    auth=True,
    scope='self',
    payload={'room_id': 'str'},
))

_reg(EventSchema(
    name='room:join_private',
    direction='in',
    auth=True,
    scope='self',
    payload={
        'room_id':  'str',
        'password': '?str',
    },
))

_reg(EventSchema(
    name='room:join_with_token',
    direction='in',
    auth=True,
    scope='self',
    payload={'token': 'str'},
))

_reg(EventSchema(
    name='room:joined',
    direction='out',
    auth=True,
    scope='self',
    payload={
        'room_id':     'str',
        'name':        'str',
        'visibility':  'str',
        'ttl':         '?int',
        'history':     'list',
        'members':     'list',
        'is_admin':    'bool',
        'is_frozen':   'bool',
        'session_key': '?dict',
    },
))

_reg(EventSchema(
    name='room:leave',
    direction='in',
    auth=True,
    scope='self',
    payload={},
))

_reg(EventSchema(
    name='room:left',
    direction='out',
    auth=True,
    scope='self',
    payload={},
))

_reg(EventSchema(
    name='room:list',
    direction='both',
    auth=True,
    scope='self|broadcast',
    payload={},
    notes='Client sends {} to request; server sends array of room summaries.',
))

_reg(EventSchema(
    name='room:members',
    direction='out',
    auth=True,
    scope='room',
    payload={},
    notes='Array of member dicts.',
))

_reg(EventSchema(
    name='room:deleted',
    direction='out',
    auth=False,
    scope='broadcast',
    payload={'room_id': 'str'},
))

_reg(EventSchema(
    name='room:key',
    direction='both',
    auth=True,
    scope='room',
    payload={
        'room_id': 'str',
        'key':     '?dict',
    },
    notes='Creator sends key; server relays to members.',
))

_reg(EventSchema(
    name='room:set_approval',
    direction='in',
    auth=True,
    scope='self',
    payload={
        'room_id': 'str',
        'enabled': 'bool',
    },
))

_reg(EventSchema(
    name='room:knock',
    direction='out',
    auth=True,
    scope='self',
    payload={
        'room_id': 'str',
        'sid':     'str',
        'display': 'str',
    },
    notes='Sent to room admins when someone knocks.',
))

_reg(EventSchema(
    name='room:knock_pending',
    direction='out',
    auth=True,
    scope='self',
    payload={
        'room_id': 'str',
        'name':    'str',
    },
    notes='Sent to the knocker to confirm their knock is pending.',
))

_reg(EventSchema(
    name='room:knock_approve',
    direction='in',
    auth=True,
    scope='self',
    payload={
        'room_id': 'str',
        'sid':     'str',
    },
))

_reg(EventSchema(
    name='room:knock_deny',
    direction='in',
    auth=True,
    scope='self',
    payload={
        'room_id': 'str',
        'sid':     'str',
    },
))

_reg(EventSchema(
    name='room:join_approved',
    direction='out',
    auth=True,
    scope='self',
    payload={
        'room_id': 'str',
        'token':   'str',
        'ttl':     'int',
    },
))

_reg(EventSchema(
    name='room:knock_denied',
    direction='out',
    auth=True,
    scope='self',
    payload={'room_id': 'str'},
))

_reg(EventSchema(
    name='room:call',
    direction='in',
    auth=True,
    scope='room',
    payload={
        'room_id':   'str',
        'call_type': '?str',
    },
))

_reg(EventSchema(
    name='room:incoming_call',
    direction='out',
    auth=True,
    scope='room',
    payload={
        'room_id':   'str',
        'room_name': 'str',
        'from':      'str',
        'call_type': 'str',
    },
))

_reg(EventSchema(
    name='room:frozen',
    direction='out',
    auth=True,
    scope='room',
    payload={
        'room_id':   'str',
        'is_frozen': 'bool',
    },
))

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN / MODERATION
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='admin:kick',
    direction='in',
    auth=True,
    scope='room',
    payload={
        'room_id': 'str',
        'target':  'str',
    },
))

_reg(EventSchema(
    name='admin:kicked',
    direction='out',
    auth=True,
    scope='self',
    payload={'room_id': 'str'},
))

_reg(EventSchema(
    name='admin:freeze',
    direction='in',
    auth=True,
    scope='room',
    payload={
        'room_id': 'str',
        'freeze':  'bool',
    },
))

_reg(EventSchema(
    name='admin:mod',
    direction='in',
    auth=True,
    scope='room',
    payload={
        'room_id': 'str',
        'target':  'str',
        'grant':   'bool',
    },
))

_reg(EventSchema(
    name='vote_hide',
    direction='in',
    auth=True,
    scope='global',
    payload={'msg_id': 'str'},
))

_reg(EventSchema(
    name='hide_message',
    direction='out',
    auth=False,
    scope='broadcast',
    payload={'msg_id': 'str'},
))

_reg(EventSchema(
    name='vote_count',
    direction='out',
    auth=False,
    scope='self',
    payload={
        'msg_id': 'str',
        'votes':  'int',
        'needed': 'int',
    },
))

_reg(EventSchema(
    name='cooldown',
    direction='out',
    auth=True,
    scope='self',
    payload={
        'seconds': 'int',
        'message': 'str',
    },
))

# ─────────────────────────────────────────────────────────────────────────────
# WEBRTC
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='webrtc_signal',
    direction='both',
    auth=True,
    scope='dm',
    payload={
        'to':   '?str',
        'from': '?str',
        'type': 'str',
    },
    notes='Opaque relay. Server adds "from" field before forwarding.',
))

# ─────────────────────────────────────────────────────────────────────────────
# ERROR
# ─────────────────────────────────────────────────────────────────────────────

_reg(EventSchema(
    name='error',
    direction='out',
    auth=False,
    scope='self',
    payload={
        'message': 'str',
        'code':    'str',
        'context': '?dict',
    },
))
