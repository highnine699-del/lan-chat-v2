# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
routes/socket_rooms.py
Room management Socket.IO handlers.
"""

import logging
import secrets as _sec
import time
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

log = logging.getLogger('lan-chat')
sec_log = logging.getLogger('lan-chat.security')

import state_log as _sl

from config import MAX_ROOM_NAME_LEN, EPHEMERAL_TTLS, JOIN_TOKEN_TTL_S
from core.state import (
    users, rooms, join_tokens, analytics,
    create_room, get_room, update_room, is_room_admin,
    room_member_list, schedule_room_delete, cancel_room_delete,
    clean_room_name, set_user_room, join_call,
    filter_expired,
    _call_key_for_room,
)
from .socket_rate_limit import _require_member


def register_room_handlers(sio):
    """Register room management handlers."""

    def current_user(sid):
        return users.get(sid) if sid else None

    def system_msg(text):
        return {'type': 'system', 'text': text, 'time': int(time.time() * 1000)}

    async def err(sid, message, code='ERROR', context=None):
        payload = {'message': message, 'code': code}
        if context:
            payload['context'] = context
        await sio.emit('error', payload, to=sid)

    # ── room:create ───────────────────────────────────────────────────────────

    @sio.on('room:create')
    async def handle_room_create(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return

        name = clean_room_name(data.get('name', ''))
        if not name:
            await sio.emit('error', {'message': 'Invalid room name. Use letters, numbers, spaces, - or .'}, to=sid)
            return

        visibility = str(data.get('visibility', 'public'))
        if visibility not in ('public', 'private'):
            visibility = 'public'

        password = str(data.get('password', ''))[:64] or None
        ttl_key = str(data.get('ttl', 'session'))
        ttl = EPHEMERAL_TTLS.get(ttl_key)

        room = create_room(name, sid, visibility=visibility, password=password, ttl=ttl)
        if room is None:
            await sio.emit('error', {'message': 'Server is at room capacity. Try again later.'}, to=sid)
            return

        room_id = room['id']

        if visibility == 'private' and data.get('require_approval'):
            room['require_approval'] = True

        room['members'].add(sid)
        await sio.enter_room(sid, room_id)
        set_user_room(sid, room_id)

        await sio.emit('room:created', {
            'room_id': room_id,
            'name': room['name'],
            'visibility': room['visibility'],
            'ttl': ttl,
            'members': room_member_list(room_id),
            'is_admin': True,
        }, to=sid)
        _sl.room_created(sid, user['display'], room_id, room['name'], room['visibility'])

        await sio.emit('room:list', _public_room_list())

    # ── room:key ──────────────────────────────────────────────────────────────

    @sio.on('room:key')
    async def handle_room_key(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not sid or not user:
            return

        room_id = str(data.get('room_id', ''))
        key_jwk = data.get('key')

        room = get_room(room_id)
        if not room:
            return

        if room['creator_sid'] != sid:
            return

        if not isinstance(key_jwk, dict):
            return

        update_room(room_id, session_key=key_jwk)

        for member_sid in room['members']:
            if member_sid != sid:
                await sio.emit('room:key', {
                    'room_id': room_id,
                    'key': key_jwk,
                }, to=member_sid)

    # ── room:join ─────────────────────────────────────────────────────────────

    @sio.on('room:join')
    async def handle_room_join(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return

        room_id = str(data.get('room_id', ''))
        room = get_room(room_id)

        if not room:
            await sio.emit('error', {'message': 'Room not found.'}, to=sid)
            return

        if room['visibility'] == 'private':
            await sio.emit('error', {'message': 'This is a private room. Use "Join Private Room".'}, to=sid)
            return

        await _do_join_room(sid, user, room, sio)

    @sio.on('room:join_private')
    async def handle_room_join_private(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return

        room_id = str(data.get('room_id', ''))
        password = str(data.get('password', ''))
        room = get_room(room_id)

        if not room:
            await sio.emit('error', {'message': 'Room not found.'}, to=sid)
            return

        if room['visibility'] != 'private':
            await _do_join_room(sid, user, room, sio)
            return

        if room['password'] and room['password'] != password:
            sec_log.warning('room:join_private: wrong password for room=%s from sid=%s', room_id, sid)
            await sio.emit('error', {'message': 'Wrong password.'}, to=sid)
            return

        if room.get('require_approval'):
            room['pending_knocks'][sid] = user['display']
            for admin_sid in room['admins']:
                await sio.emit('room:knock', {
                    'room_id': room_id,
                    'sid': sid,
                    'display': user['display'],
                }, to=admin_sid)
            await sio.emit('room:knock_pending', {
                'room_id': room_id,
                'name': room['name'],
            }, to=sid)
            return

        await _do_join_room(sid, user, room, sio)

    # ── room:leave ────────────────────────────────────────────────────────────

    @sio.on('room:leave')
    async def handle_room_leave(sid, data):
        user = current_user(sid)
        if not user or not sid:
            return
        await _leave_current_room(sid, user, sio)
        await sio.emit('room:left', {}, to=sid)

    # ── room:set_approval ─────────────────────────────────────────────────────

    @sio.on('room:set_approval')
    async def handle_set_approval(sid, data):
        if not isinstance(data, dict):
            return
        if not sid:
            return
        room_id = str(data.get('room_id', ''))
        enabled = bool(data.get('enabled', True))
        if not is_room_admin(sid, room_id):
            await sio.emit('error', {'message': 'Not authorised.'}, to=sid)
            return
        room = get_room(room_id)
        if not room:
            return
        update_room(room_id, require_approval=enabled)

    # ── room:knock_approve / room:knock_deny ──────────────────────────────────

    @sio.on('room:knock_approve')
    async def handle_knock_approve(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not sid or not user:
            return
        room_id = str(data.get('room_id', ''))
        knocker_sid = str(data.get('sid', ''))
        if not is_room_admin(sid, room_id):
            return
        room = get_room(room_id)
        if not room or knocker_sid not in room.get('pending_knocks', {}):
            return
        room['pending_knocks'].pop(knocker_sid, None)

        token = _sec.token_hex(16)
        join_tokens[token] = {
            'room_id': room_id,
            'sid': knocker_sid,
            'expires': time.time() + JOIN_TOKEN_TTL_S,
        }
        await sio.emit('room:join_approved', {
            'room_id': room_id,
            'token': token,
            'ttl': JOIN_TOKEN_TTL_S,
        }, to=knocker_sid)

    @sio.on('room:knock_deny')
    async def handle_knock_deny(sid, data):
        if not isinstance(data, dict):
            return
        if not sid:
            return
        room_id = str(data.get('room_id', ''))
        knocker_sid = str(data.get('sid', ''))
        if not is_room_admin(sid, room_id):
            return
        room = get_room(room_id)
        if not room:
            return
        room['pending_knocks'].pop(knocker_sid, None)
        await sio.emit('room:knock_denied', {'room_id': room_id}, to=knocker_sid)

    # ── room:join_with_token ──────────────────────────────────────────────────

    @sio.on('room:join_with_token')
    async def handle_join_with_token(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not sid or not user:
            return

        token = str(data.get('token', ''))
        entry = join_tokens.pop(token, None)

        if not entry:
            await err(sid, 'Invalid or expired join token.', 'INVALID_TOKEN')
            return

        if time.time() > entry['expires']:
            await err(sid, 'Join token has expired. Request approval again.',
                'TOKEN_EXPIRED', {'room_id': entry['room_id']})
            return

        if entry['sid'] != sid:
            await err(sid, 'This token was not issued for your session.', 'TOKEN_MISMATCH')
            return

        room = get_room(entry['room_id'])
        if not room:
            await err(sid, 'Room no longer exists.', 'ROOM_NOT_FOUND',
                {'room_id': entry['room_id']})
            return

        await _do_join_room(sid, user, room, sio)

    # ── room:call ─────────────────────────────────────────────────────────────

    @sio.on('room:call')
    async def handle_room_call(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return
        room_id = str(data.get('room_id', ''))
        call_type = str(data.get('call_type', 'voice'))
        if call_type not in ('voice', 'video'):
            call_type = 'voice'
        room = get_room(room_id)
        if not room or sid not in room['members']:
            return
        call_id = _call_key_for_room(room_id)
        join_call(call_id, sid)
        for member_sid in room['members']:
            if member_sid != sid:
                await sio.emit('room:incoming_call', {
                    'room_id': room_id,
                    'room_name': room['name'],
                    'from': user['display'],
                    'call_type': call_type,
                }, to=member_sid)

    # ── room:list ─────────────────────────────────────────────────────────────

    @sio.on('room:list')
    async def handle_room_list(sid, data):
        await sio.emit('room:list', _public_room_list(), to=sid)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _do_join_room(sid, user, room, sio):
        room_id = room['id']
        prev_room = user.get('room_id')

        await _leave_current_room(sid, user, sio)

        cancel_room_delete(room_id)
        room['members'].add(sid)
        await sio.enter_room(sid, room_id)
        set_user_room(sid, room_id)

        history = filter_expired(room['messages'], room['ttl'])
        await sio.emit('room:joined', {
            'room_id': room_id,
            'name': room['name'],
            'visibility': room['visibility'],
            'ttl': room['ttl'],
            'history': history,
            'members': room_member_list(room_id),
            'is_admin': sid in room['admins'],
            'is_frozen': room['is_frozen'],
            'session_key': room.get('session_key'),
        }, to=sid)

        await sio.emit('system_message',
             system_msg(f'{user["display"]} joined room {room["name"]}'),
             room=room_id)
        await sio.emit('room:members', room_member_list(room_id), room=room_id)
        _sl.room_joined(sid, user['display'], room_id, room['name'], prev_room)

    async def _leave_current_room(sid, user, sio):
        room_id = user.get('room_id')
        if not room_id:
            return
        await _leave_room_by_id(sid, room_id, user['display'], sio)
        set_user_room(sid, None)

    async def _leave_room_by_id(sid, room_id, display, sio):
        room = get_room(room_id)
        if not room:
            return
        room['members'].discard(sid)
        await sio.leave_room(sid, room_id)
        await sio.emit('system_message',
             system_msg(f'{display} left the room.'),
             room=room_id)
        await sio.emit('room:members', room_member_list(room_id), room=room_id)
        if not room['members']:
            schedule_room_delete(room_id, sio)
        _sl.room_left(sid, display, room_id, room['name'])

    def _public_room_list():
        return [
            {
                'room_id': r['id'],
                'name': r['name'],
                'members': len(r['members']),
                'ttl': r['ttl'],
                'is_frozen': r['is_frozen'],
                'locked': False,
            }
            for r in rooms.values()
            if r['visibility'] == 'public'
        ]
