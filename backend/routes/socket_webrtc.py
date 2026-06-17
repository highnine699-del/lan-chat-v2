# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
routes/socket_webrtc.py
WebRTC signaling Socket.IO handlers.
"""

import json
import logging
import time
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

log = logging.getLogger('lan-chat')
sec_log = logging.getLogger('lan-chat.security')

import state_log as _sl

from config import MAX_SIGNAL_BYTES
from core.state import (
    users, sid_map, analytics,
    join_call, leave_call, in_same_call, get_call_for_sid, teardown_call,
    create_call_session, get_call_session_id, invalidate_call_session,
    is_offer_locked, set_offer_lock, clear_offer_lock,
    advance_call_phase, get_call_phase, reset_call_phase, mark_call_active,
    write_call_tombstone, find_call_tombstone, consume_call_tombstone,
    call_sessions,
)
from .socket_rate_limit import _check_signal_rate


def register_webrtc_handlers(sio):
    """Register WebRTC signaling handlers."""

    def current_user(sid):
        return users.get(sid) if sid else None

    async def err(sid, message, code='ERROR', context=None):
        payload = {'message': message, 'code': code}
        if context:
            payload['context'] = context
        await sio.emit('error', payload, to=sid)

    # ── call_signal ─────────────────────────────────────────────────────────────

    _call_signal_last = {}
    _CALL_SIGNAL_MIN_GAP = 0.1

    @sio.on('call_signal')
    async def handle_call_signal(sid, data):
        if not isinstance(data, dict):
            return
        try:
            if len(json.dumps(data).encode()) > MAX_SIGNAL_BYTES:
                return
        except (TypeError, ValueError):
            return

        user = current_user(sid)
        if not user:
            return

        now = time.time()
        last = _call_signal_last.get(sid, 0.0)
        if now - last < _CALL_SIGNAL_MIN_GAP:
            return
        _call_signal_last[sid] = now

        target = str(data.get('to', ''))

        if target not in sid_map:
            await sio.emit('call_signal', {'type': 'error', 'error': f'User "{target}" is not connected'}, to=sid)
            return

        target_sid = sid_map[target]
        if target_sid not in users:
            sid_map.pop(target, None)
            await sio.emit('call_signal', {'type': 'error', 'error': f'User "{target}" has disconnected'}, to=sid)
            return

        signal_type = str(data.get('type', ''))
        call_id = '|'.join(sorted([sid, target_sid]))

        if signal_type == 'offer':
            if is_offer_locked(sid):
                await sio.emit('call_signal', {
                    'type': 'error',
                    'error': 'OFFER_LOCKED',
                    'detail': 'You already have an active outgoing offer. End the current call first.',
                }, to=sid)
                return

            allowed, reason = advance_call_phase(call_id, 'offer')
            if not allowed:
                sec_log.warning('call_signal: FSM rejected offer sid=%s reason=%s', sid, reason)
                return

            join_call(call_id, sid)
            join_call(call_id, target_sid)

            offerer_uid = user.get('uid', '')
            target_uid = users.get(target_sid, {}).get('uid', '')
            tombstone = consume_call_tombstone(offerer_uid, target_uid) if (offerer_uid and target_uid) else None

            if tombstone:
                session_uuid = tombstone['session_uuid']
                call_sessions[call_id] = session_uuid
                data['resume'] = True
                sec_log.info(
                    'call_signal: tombstone consumed uid=%.8s peer=%.8s session=%.8s',
                    offerer_uid, target_uid, session_uuid,
                )
            else:
                session_uuid = create_call_session(call_id)

            set_offer_lock(sid, call_id)
            data['session_id'] = session_uuid

        elif signal_type in ('answer', 'ice', 'end', 'reject'):
            if not in_same_call(sid, target_sid):
                return

            stored_uuid = get_call_session_id(call_id)
            client_uuid = str(data.get('session_id', ''))
            if stored_uuid and client_uuid != stored_uuid:
                sec_log.warning(
                    'call_signal: session_id mismatch type=%s sid=%s '
                    'stored=%.8s presented=%.8s — dropped',
                    signal_type, sid,
                    stored_uuid[:8] if stored_uuid else 'none',
                    client_uuid[:8] if client_uuid else 'none',
                )
                return

            allowed, reason = advance_call_phase(call_id, signal_type)
            if not allowed:
                sec_log.warning(
                    'call_signal: FSM rejected %s sid=%s reason=%s',
                    signal_type, sid, reason,
                )
                return

        data['from'] = user['display']
        await sio.emit('call_signal', data, to=target_sid)

        if signal_type in ('end', 'reject'):
            invalidate_call_session(call_id)
            reset_call_phase(call_id)
            clear_offer_lock(sid)
            clear_offer_lock(target_sid)
            leave_call(sid)
            leave_call(target_sid)

    # ── webrtc_signal (legacy fallback) ───────────────────────────────────────

    @sio.on('webrtc_signal')
    async def handle_webrtc_signal(sid, data):
        if not isinstance(data, dict):
            return
        try:
            if len(json.dumps(data).encode()) > MAX_SIGNAL_BYTES:
                return
        except (TypeError, ValueError):
            return

        user = current_user(sid)
        if not user:
            return

        if not _check_signal_rate(sid):
            return

        target = str(data.get('to', ''))
        if target not in sid_map:
            await sio.emit('webrtc_signal', {
                'type': 'error',
                'error': f'User "{target}" is not connected',
            }, to=sid)
            return

        target_sid = sid_map[target]
        if target_sid not in users:
            sid_map.pop(target, None)
            await sio.emit('webrtc_signal', {
                'type': 'error',
                'error': f'User "{target}" has disconnected',
            }, to=sid)
            return

        signal_type = str(data.get('type', ''))
        call_id = '|'.join(sorted([sid, target_sid]))

        if signal_type == 'offer':
            if is_offer_locked(sid):
                await sio.emit('webrtc_signal', {
                    'type': 'error',
                    'error': 'OFFER_LOCKED',
                    'detail': 'You already have an active outgoing offer.',
                }, to=sid)
                return

            allowed, reason = advance_call_phase(call_id, 'offer')
            if not allowed:
                sec_log.warning('webrtc_signal: FSM rejected offer sid=%s reason=%s', sid, reason)
                return

            join_call(call_id, sid)
            join_call(call_id, target_sid)
            session_uuid = create_call_session(call_id)
            set_offer_lock(sid, call_id)
            data['session_id'] = session_uuid
            await sio.emit('webrtc_signal', {'type': 'session_ack', 'session_id': session_uuid}, to=sid)

        elif signal_type in ('answer', 'candidate'):
            if not in_same_call(sid, target_sid):
                sec_log.warning(
                    'webrtc_signal: blocked %s from sid=%s to %s — not in same call',
                    signal_type, sid, target,
                )
                _sl.webrtc_signal(sid, user['display'], target, signal_type,
                                  blocked=True, reason='not_in_same_call')
                return

            stored_uuid = get_call_session_id(call_id)
            client_uuid = str(data.get('session_id', ''))
            if stored_uuid and client_uuid != stored_uuid:
                sec_log.warning(
                    'webrtc_signal: session_id mismatch type=%s sid=%s — dropped',
                    signal_type, sid,
                )
                return

            allowed, reason = advance_call_phase(call_id, signal_type)
            if not allowed:
                sec_log.warning(
                    'webrtc_signal: FSM rejected %s sid=%s reason=%s',
                    signal_type, sid, reason,
                )
                return

        data['from'] = user['display']
        await sio.emit('webrtc_signal', data, to=target_sid)

        if signal_type in ('end', 'reject'):
            invalidate_call_session(call_id)
            reset_call_phase(call_id)
            clear_offer_lock(sid)
            clear_offer_lock(target_sid)
            leave_call(sid)
            leave_call(target_sid)

    # ── call:query_phase ──────────────────────────────────────────────────────

    @sio.on('call:query_phase')
    async def handle_call_query_phase(sid, data):
        if not isinstance(data, dict):
            return

        user = current_user(sid)
        if not user:
            return

        target = str(data.get('to', ''))

        if target not in sid_map:
            await sio.emit('call:phase_reply', {
                'phase': None,
                'session_id': None,
                'call_id': None,
                'answer_allowed': False,
                'ice_allowed': False,
            }, to=sid)
            return

        target_sid = sid_map[target]
        call_id = '|'.join(sorted([sid, target_sid]))
        phase = get_call_phase(call_id)
        session_id = get_call_session_id(call_id)

        answer_allowed = (phase == 'OFFERED')
        ice_allowed = (phase in ('ANSWERED', 'CONNECTING', 'ACTIVE'))

        await sio.emit('call:phase_reply', {
            'call_id': call_id if phase else None,
            'phase': phase,
            'session_id': session_id,
            'answer_allowed': answer_allowed,
            'ice_allowed': ice_allowed,
        }, to=sid)

    # ── Legacy call events ───────────────────────────────────────────────────────

    _CALL_EVENT_MAP = {
        'call-user': 'incoming-call',
        'video-call-user': 'incoming-call',
        'call-accepted': 'call-started',
        'call-rejected': 'call-ended',
        'end-call': 'call-ended',
    }

    def _make_call_handler(outgoing_event):
        async def handler(sid, data=None):
            target = data.get('to') if isinstance(data, dict) else None
            if target and target in sid_map:
                await sio.emit(outgoing_event, {}, to=sid_map[target])

            if not sid or not target:
                return
            target_sid = sid_map.get(target)
            if not target_sid:
                return

            if outgoing_event == 'call-started':
                call_id = '|'.join(sorted([sid, target_sid]))
                join_call(call_id, sid)
                join_call(call_id, target_sid)
            elif outgoing_event == 'call-ended':
                leave_call(sid)
                leave_call(target_sid)
        return handler

    for _in, _out in _CALL_EVENT_MAP.items():
        sio.on(_in)(_make_call_handler(_out))
