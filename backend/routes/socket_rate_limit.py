# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
routes/socket_rate_limit.py
Rate limiting and security helpers for Socket.IO handlers.
"""

import logging
import time
from collections import deque

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.state import rooms, users
import state_log as _sl

log = logging.getLogger('lan-chat')
sec_log = logging.getLogger('lan-chat.security')

# ── Module-level rate-limit state ─────────────────────────────────────────────
# These live outside register_socket_handlers so they persist across all calls.

# Per-IP join rate limiting: max 10 join attempts per 60s window
_join_rate: dict = {}          # ip -> deque of timestamps
_JOIN_RATE_LIMIT  = 10
_JOIN_RATE_WINDOW = 60         # seconds

# Per-SID WebRTC signal rate limiting: max 20 signals per 10s window
_signal_tracker: dict = {}     # sid -> deque of timestamps
_SIGNAL_RATE_LIMIT  = 20
_SIGNAL_RATE_WINDOW = 10       # seconds

# Per-UID ghost-eviction cooldown: prevents targeted DoS via uid replay
_uid_last_kick: dict = {}      # uid -> float (epoch of last eviction)
_UID_KICK_COOLDOWN = 30        # seconds

# Export these for test compatibility
__all__ = [
    'reset_rate_limiters',
    '_prune_module_state',
    '_check_join_rate',
    '_check_signal_rate',
    '_get_client_ip',
    '_require_member',
    '_join_rate',
    '_signal_tracker',
    '_uid_last_kick',
    '_JOIN_RATE_LIMIT',
    '_JOIN_RATE_WINDOW',
    '_SIGNAL_RATE_LIMIT',
    '_SIGNAL_RATE_WINDOW',
    '_UID_KICK_COOLDOWN',
]

# Hard caps for module-level dicts — prevents unbounded growth when IPs/SIDs
# accumulate faster than the background cleanup thread runs.
_JOIN_RATE_MAX    = 5_000   # max distinct IPs tracked
_SIGNAL_RATE_MAX  = 5_000   # max distinct SIDs tracked
_UID_KICK_MAX     = 10_000  # max distinct UIDs tracked


def reset_rate_limiters() -> None:
    """
    Clear all module-level rate-limit state.
    Intended for use in tests only — never call this in production code.
    """
    _join_rate.clear()
    _signal_tracker.clear()
    _uid_last_kick.clear()


def _prune_module_state() -> None:
    """
    Prune stale entries from module-level rate-limit dicts.
    Called by the background cleanup worker every 30 seconds.
    """
    now = time.time()
    # _join_rate: remove IPs whose window has fully expired
    stale_ips = [ip for ip, q in list(_join_rate.items()) if not q or now - q[-1] > _JOIN_RATE_WINDOW]
    for ip in stale_ips:
        _join_rate.pop(ip, None)
    # Hard cap
    if len(_join_rate) > _JOIN_RATE_MAX:
        for k in list(_join_rate.keys())[:len(_join_rate) - _JOIN_RATE_MAX]:
            _join_rate.pop(k, None)

    # _signal_tracker: remove SIDs no longer in active users
    from core.state import users as _users
    stale_sids = [sid for sid in list(_signal_tracker.keys()) if sid not in _users]
    for sid in stale_sids:
        _signal_tracker.pop(sid, None)
    if len(_signal_tracker) > _SIGNAL_RATE_MAX:
        for k in list(_signal_tracker.keys())[:len(_signal_tracker) - _SIGNAL_RATE_MAX]:
            _signal_tracker.pop(k, None)

    # _uid_last_kick: remove entries older than 2x the cooldown window
    cutoff = now - (_UID_KICK_COOLDOWN * 2)
    stale_uids = [uid for uid, t in list(_uid_last_kick.items()) if t < cutoff]
    for uid in stale_uids:
        _uid_last_kick.pop(uid, None)
    if len(_uid_last_kick) > _UID_KICK_MAX:
        for k in list(_uid_last_kick.keys())[:len(_uid_last_kick) - _UID_KICK_MAX]:
            _uid_last_kick.pop(k, None)


def _check_join_rate(ip: str) -> bool:
    """Return True if this IP is allowed to attempt a join, False if rate-limited."""
    now = time.time()
    q = _join_rate.setdefault(ip, deque())
    while q and now - q[0] > _JOIN_RATE_WINDOW:
        q.popleft()
    if len(q) >= _JOIN_RATE_LIMIT:
        return False
    q.append(now)
    return True


def _check_signal_rate(sid: str) -> bool:
    """Return True if this SID is allowed to send a WebRTC signal, False if rate-limited."""
    now = time.time()
    q = _signal_tracker.setdefault(sid, deque())
    while q and now - q[0] > _SIGNAL_RATE_WINDOW:
        q.popleft()
    if len(q) >= _SIGNAL_RATE_LIMIT:
        return False
    q.append(now)
    return True


def _get_client_ip(request) -> str:
    """
    Return the real client IP.
    Only trusts X-Forwarded-For if TRUSTED_PROXY is set in config,
    otherwise always uses the direct socket address to prevent spoofing.
    """
    from config import TRUSTED_PROXY
    if TRUSTED_PROXY:
        xff = request.headers.get('x-forwarded-for', '')
        if xff:
            # Rightmost entry is the last trusted proxy's view of the client
            return xff.split(',')[-1].strip()
    return request.client.host if request.client else '127.0.0.1'


def _require_member(sid: str, room_id: str, action: str) -> bool:
    """
    INVARIANT 2 enforcer.

    Returns True if sid is a current member of room_id.
    Logs and returns False otherwise — caller must return immediately.

    Usage:
        if not _require_member(sid, room_id, 'send_message'):
            emit('error', {'code': 'FORBIDDEN', ...})
            return
    """
    room = rooms.get(room_id)
    if room is None or sid not in room['members']:
        sec_log.warning('invariant2: %s by non-member sid=%s room=%s', action, sid, room_id)
        actor = users.get(sid, {}).get('display', sid[:8])
        _sl.invariant_violation(sid, actor, action, 2,
                                'non_member_action',
                                {'room_id': room_id})
        return False
    return True
