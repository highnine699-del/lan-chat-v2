# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
state_log.py — State diff logger for LAN Chat.

Logs every meaningful state transition in a structured, human-readable format:

    [TRANSITION] actor=Alice#A1B2 handler=join
        OLD: identity=None room=None presence=None
        NEW: identity=Alice#A1B2 room=None presence=active
        REASON: new session
        INVARIANT: PASS

Activation
----------
Set the STATE_LOG environment variable before starting the server:

    STATE_LOG=1 python server.py          # log to stderr (default)
    STATE_LOG=file python server.py       # log to state_transitions.log
    STATE_LOG=0 python server.py          # disabled (default)

The logger uses Python's standard logging infrastructure, so it can be
redirected to any handler (file, syslog, cloud log aggregator) by
configuring the 'lan-chat.state' logger in your logging setup.

Design constraints
------------------
- Zero imports from Flask or Socket.IO — fully testable in isolation.
- No mutable state of its own — the logger never grows unboundedly.
- All log calls are no-ops when STATE_LOG is not set (checked once at import).
- Structured fields use key=value pairs so log parsers (grep, jq, etc.) work.
- Sensitive data (passwords, tokens, message text) is never logged.
"""
import os
import logging
import time

# ── Activation ────────────────────────────────────────────────────────────────
_STATE_LOG_MODE = os.environ.get('STATE_LOG', '0').strip().lower()
_ENABLED = _STATE_LOG_MODE not in ('0', '', 'false', 'off', 'no')

_log = logging.getLogger('lan-chat.state')

if _ENABLED:
    if _STATE_LOG_MODE == 'file':
        _fh = logging.FileHandler(
            os.path.join(os.path.dirname(__file__), 'state_transitions.log'),
            encoding='utf-8',
        )
        _fh.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
        _log.addHandler(_fh)
        _log.setLevel(logging.DEBUG)
        _log.propagate = False   # don't double-log to root handler
    else:
        # Default: let the root logger handle it (goes to stderr / wherever
        # the operator has configured logging).
        _log.setLevel(logging.DEBUG)


# ── Transition categories ─────────────────────────────────────────────────────
# Each category maps to a set of transitions we care about.
# The caller picks the right emit_* function — no magic introspection.

class InvariantResult:
    PASS = 'PASS'
    FAIL = 'FAIL'
    NA   = 'N/A'   # transition doesn't touch an invariant


# ── Core emit ─────────────────────────────────────────────────────────────────

def _emit(
    category: str,
    actor: str,
    handler: str,
    old: dict,
    new: dict,
    reason: str,
    invariant: str = InvariantResult.NA,
    extra: dict | None = None,
) -> None:
    """
    Internal: format and emit one transition log line.

    Never raises — logging must never crash the server.
    """
    if not _ENABLED:
        return
    try:
        old_str = ' '.join(f'{k}={v!r}' for k, v in old.items())
        new_str = ' '.join(f'{k}={v!r}' for k, v in new.items())
        extra_str = (' ' + ' '.join(f'{k}={v!r}' for k, v in extra.items())) if extra else ''
        _log.debug(
            '[%s] actor=%s handler=%s\n'
            '    OLD: %s\n'
            '    NEW: %s\n'
            '    REASON: %s  INVARIANT: %s%s',
            category, actor, handler,
            old_str or '(none)',
            new_str or '(none)',
            reason, invariant,
            extra_str,
        )
    except Exception:
        pass   # never let logging crash the server


# ── Public API ────────────────────────────────────────────────────────────────
# One function per transition type.  Each function is a no-op when disabled.

def session_joined(
    sid: str,
    display: str,
    ip: str,
    uid_reclaimed: bool,
    is_admin: bool,
) -> None:
    """
    A new session was fully registered after a successful 'join'.

    INVARIANT 1: identity is now established for this SID.
    """
    _emit(
        category='SESSION',
        actor=display,
        handler='join',
        old={'identity': None, 'room': None, 'presence': None},
        new={'identity': display, 'room': None, 'presence': 'active', 'admin': is_admin},
        reason='uid_reclaimed' if uid_reclaimed else 'new_session',
        invariant=InvariantResult.PASS,
        extra={'ip': ip, 'sid': sid[:8]},
    )


def session_rejected(
    sid: str,
    ip: str,
    reason: str,
    code: str,
) -> None:
    """
    A join attempt was rejected before any state was written.

    INVARIANT 1: identity was NOT established — correct behaviour.
    """
    _emit(
        category='SESSION',
        actor='(unauthenticated)',
        handler='join',
        old={'identity': None},
        new={'identity': None},
        reason=reason,
        invariant=InvariantResult.FAIL,   # attempted invariant violation
        extra={'ip': ip, 'code': code, 'sid': sid[:8]},
    )


def session_disconnected(
    sid: str,
    display: str,
    room_id: str | None,
) -> None:
    """A session was cleanly removed on disconnect."""
    _emit(
        category='SESSION',
        actor=display,
        handler='disconnect',
        old={'identity': display, 'room': room_id, 'status': 'connected'},
        new={'identity': None, 'room': None, 'status': 'disconnected'},
        reason='socket_closed',
        invariant=InvariantResult.NA,
        extra={'sid': sid[:8]},
    )


def ghost_evicted(
    old_sid: str,
    new_sid: str,
    display: str,
    uid: str,
) -> None:
    """
    A stale session for the same uid was evicted to make room for a reconnect.

    INVARIANT 5: display name uniqueness is maintained by removing the ghost.
    """
    _emit(
        category='SESSION',
        actor=display,
        handler='join',
        old={'sid': old_sid[:8], 'status': 'connected'},
        new={'sid': new_sid[:8], 'status': 'connected'},
        reason='ghost_eviction_on_reconnect',
        invariant=InvariantResult.PASS,
        extra={'uid': uid[:8]},
    )


def room_joined(
    sid: str,
    display: str,
    room_id: str,
    room_name: str,
    prev_room: str | None,
) -> None:
    """
    A user joined a room.  INVARIANT 2: they are now a member.
    """
    _emit(
        category='ROOM',
        actor=display,
        handler='room:join',
        old={'room': prev_room},
        new={'room': room_id},
        reason=f'joined {room_name!r}',
        invariant=InvariantResult.PASS,
        extra={'sid': sid[:8]},
    )


def room_left(
    sid: str,
    display: str,
    room_id: str,
    room_name: str,
    reason: str = 'explicit_leave',
) -> None:
    """A user left a room (explicit leave, kick, or disconnect)."""
    _emit(
        category='ROOM',
        actor=display,
        handler='room:leave',
        old={'room': room_id},
        new={'room': None},
        reason=reason,
        invariant=InvariantResult.NA,
        extra={'sid': sid[:8], 'room_name': room_name},
    )


def room_created(
    sid: str,
    display: str,
    room_id: str,
    room_name: str,
    visibility: str,
) -> None:
    """A new room was created."""
    _emit(
        category='ROOM',
        actor=display,
        handler='room:create',
        old={'rooms_count': None},
        new={'room_id': room_id, 'visibility': visibility},
        reason=f'created {room_name!r}',
        invariant=InvariantResult.NA,
        extra={'sid': sid[:8]},
    )


def room_frozen(
    sid: str,
    display: str,
    room_id: str,
    frozen: bool,
) -> None:
    """A room was frozen or unfrozen by an admin."""
    _emit(
        category='ROOM',
        actor=display,
        handler='admin:freeze',
        old={'is_frozen': not frozen},
        new={'is_frozen': frozen},
        reason='admin_action',
        invariant=InvariantResult.NA,
        extra={'sid': sid[:8], 'room_id': room_id},
    )


def presence_changed(
    sid: str,
    display: str,
    old_presence: str,
    new_presence: str,
    handler: str = 'user:presence',
) -> None:
    """A user's presence state changed."""
    if old_presence == new_presence:
        return   # no-op — don't spam the log
    _emit(
        category='PRESENCE',
        actor=display,
        handler=handler,
        old={'presence': old_presence},
        new={'presence': new_presence},
        reason='client_update',
        invariant=InvariantResult.NA,
        extra={'sid': sid[:8]},
    )


def persona_switched(
    sid: str,
    old_display: str,
    new_display: str,
    color_changed: bool,
) -> None:
    """
    A user switched persona (name and/or color).

    INVARIANT 5: new display name must be unique — checked before this is called.
    """
    _emit(
        category='IDENTITY',
        actor=old_display,
        handler='user:switch_persona',
        old={'display': old_display},
        new={'display': new_display, 'color_changed': color_changed},
        reason='persona_switch',
        invariant=InvariantResult.PASS,
        extra={'sid': sid[:8]},
    )


def message_sent(
    sid: str,
    display: str,
    target: str,
    msg_id: str,
    msg_type: str = 'text',
) -> None:
    """A message was accepted and dispatched."""
    _emit(
        category='MESSAGE',
        actor=display,
        handler='send_message',
        old={'msg_count': None},
        new={'target': target, 'msg_id': msg_id[:8], 'type': msg_type},
        reason='message_accepted',
        invariant=InvariantResult.PASS,
        extra={'sid': sid[:8]},
    )


def message_rejected(
    sid: str,
    display: str,
    handler: str,
    msg_id: str,
    reason: str,
    invariant_id: int | None = None,
) -> None:
    """
    A message action (send/edit/delete) was rejected.

    invariant_id: which invariant was violated (2=membership, 3=ownership, 4=dedup).
    """
    inv = f'FAIL (INV-{invariant_id})' if invariant_id else InvariantResult.FAIL
    _emit(
        category='MESSAGE',
        actor=display,
        handler=handler,
        old={'msg_id': msg_id[:8] if msg_id else '?'},
        new={'msg_id': msg_id[:8] if msg_id else '?'},
        reason=reason,
        invariant=inv,
        extra={'sid': sid[:8]},
    )


def message_edited(
    sid: str,
    display: str,
    msg_id: str,
    target: str,
    by_admin: bool,
) -> None:
    """A message was successfully edited and persisted."""
    _emit(
        category='MESSAGE',
        actor=display,
        handler='message:edit',
        old={'text': '(original)'},
        new={'text': '(edited)', 'persisted': True},
        reason='admin_edit' if by_admin else 'owner_edit',
        invariant=InvariantResult.PASS,
        extra={'msg_id': msg_id[:8], 'target': target, 'sid': sid[:8]},
    )


def message_deleted(
    sid: str,
    display: str,
    msg_id: str,
    target: str,
    by_admin: bool,
) -> None:
    """A message was soft-deleted and persisted."""
    _emit(
        category='MESSAGE',
        actor=display,
        handler='message:delete',
        old={'deleted': False},
        new={'deleted': True, 'persisted': True},
        reason='admin_delete' if by_admin else 'owner_delete',
        invariant=InvariantResult.PASS,
        extra={'msg_id': msg_id[:8], 'target': target, 'sid': sid[:8]},
    )


def spam_action(
    sid: str,
    display: str,
    result: str,
    spam_count: int,
) -> None:
    """
    Spam detection fired a non-ok result (cooldown or shadow mute).
    """
    _emit(
        category='SPAM',
        actor=display,
        handler='send_message',
        old={'spam_result': 'ok'},
        new={'spam_result': result, 'spam_count': spam_count},
        reason=f'spam_detected:{result}',
        invariant=InvariantResult.NA,
        extra={'sid': sid[:8]},
    )


def shadow_muted_applied(
    sid: str,
    display: str,
    until: float,
    source: str = 'spam',
) -> None:
    """A shadow mute was applied to a session."""
    _emit(
        category='MODERATION',
        actor=display,
        handler=source,
        old={'shadow_muted': False},
        new={'shadow_muted': True, 'until': int(until - time.time()).__str__() + 's'},
        reason=f'shadow_mute_applied_by:{source}',
        invariant=InvariantResult.NA,
        extra={'sid': sid[:8]},
    )


def admin_action(
    sid: str,
    display: str,
    handler: str,
    target_display: str,
    action: str,
    room_id: str | None = None,
) -> None:
    """A server-admin or room-admin action was executed."""
    _emit(
        category='ADMIN',
        actor=display,
        handler=handler,
        old={'target_state': 'before'},
        new={'target_state': action},
        reason=f'admin:{action}',
        invariant=InvariantResult.NA,
        extra={
            'target': target_display,
            'room': room_id or 'global',
            'sid': sid[:8],
        },
    )


def invariant_violation(
    sid: str,
    actor: str,
    handler: str,
    invariant_id: int,
    description: str,
    extra: dict | None = None,
) -> None:
    """
    An invariant check failed — the action was blocked.

    This is the most important log entry: it means someone tried to do
    something they shouldn't be able to do.
    """
    _emit(
        category='INVARIANT_VIOLATION',
        actor=actor or '(unknown)',
        handler=handler,
        old={},
        new={},
        reason=description,
        invariant=f'FAIL (INV-{invariant_id})',
        extra={'sid': sid[:8], **(extra or {})},
    )


def webrtc_signal(
    sid: str,
    display: str,
    target: str,
    signal_type: str,
    blocked: bool,
    reason: str = '',
) -> None:
    """A WebRTC signal was relayed or blocked."""
    if not blocked:
        return   # only log blocked signals to avoid noise
    _emit(
        category='WEBRTC',
        actor=display,
        handler='webrtc_signal',
        old={'signal': signal_type, 'blocked': False},
        new={'signal': signal_type, 'blocked': True},
        reason=reason or 'not_in_same_call',
        invariant=InvariantResult.FAIL,
        extra={'sid': sid[:8], 'target': target},
    )


def rate_limited(
    ip: str,
    handler: str,
    limit_type: str,
) -> None:
    """A rate limit was hit."""
    _emit(
        category='RATE_LIMIT',
        actor=f'ip:{ip}',
        handler=handler,
        old={'allowed': True},
        new={'allowed': False},
        reason=f'rate_limit:{limit_type}',
        invariant=InvariantResult.NA,
    )
