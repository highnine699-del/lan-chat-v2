# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
routes/socket_admin.py
Admin function Socket.IO handlers.
"""

import logging
import time
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

log = logging.getLogger('lan-chat')
sec_log = logging.getLogger('lan-chat.security')

import state_log as _sl

from core.state import (
    users, sid_map, rooms, shadow_muted,
    get_room, update_room, is_room_admin,
    room_member_list, schedule_room_delete,
    set_user_room,
)
from config import SPAM_COOLDOWN_S
from .socket_rate_limit import _require_member


def register_admin_handlers(sio):
    """Register admin function handlers."""

    def current_user(sid):
        return users.get(sid) if sid else None

    def system_msg(text):
        return {'type': 'system', 'text': text, 'time': int(time.time() * 1000)}

    async def err(sid, message, code='ERROR', context=None):
        payload = {'message': message, 'code': code}
        if context:
            payload['context'] = context
        await sio.emit('error', payload, to=sid)

    # ── admin:kick (room-level kick by a room admin) ───────────────────────────
    # Frontend sends: { target: display, room_id: roomId }
    # Legacy compat: also accept 'username' field as alias for 'target'

    @sio.on('admin:kick')
    async def handle_kick(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not sid or not user:
            return

        room_id = str(data.get('room_id', ''))
        # Accept both 'target' (correct) and 'username' (frontend legacy alias)
        target_disp = str(data.get('target', '') or data.get('username', ''))

        if not is_room_admin(sid, room_id):
            sec_log.warning('admin:kick: unauthorised attempt by sid=%s target=%s', sid, target_disp)
            await err(sid, 'Not authorised.')
            return

        target_sid = sid_map.get(target_disp)
        if not target_sid:
            await err(sid, 'User not found.')
            return

        room = get_room(room_id)
        if not room or target_sid not in room['members']:
            await err(sid, 'User is not in this room.')
            return

        room['members'].discard(target_sid)
        room['admins'].discard(target_sid)
        await sio.leave_room(target_sid, room_id)     # FIX: was missing await
        set_user_room(target_sid, None)

        await sio.emit('admin:kicked', {'room_id': room_id}, to=target_sid)
        await sio.emit('system_message',
             system_msg(f'{target_disp} was removed by an admin.'),
             room=room_id)
        await sio.emit('room:members', room_member_list(room_id), room=room_id)

        if not room['members']:
            schedule_room_delete(room_id, sio)

    # ── admin:freeze / admin:freeze_room / admin:unfreeze_room ────────────────
    # Backend canonical: admin:freeze  { room_id, freeze: bool }
    # Frontend also sends: admin:freeze_room and admin:unfreeze_room

    async def _do_freeze(sid, room_id, freeze):
        if not is_room_admin(sid, room_id):
            await sio.emit('error', {'message': 'Not authorised.'}, to=sid)
            return
        room = get_room(room_id)
        if not room:
            return
        update_room(room_id, is_frozen=freeze)
        status = 'frozen' if freeze else 'unfrozen'
        await sio.emit('room:frozen', {'room_id': room_id, 'is_frozen': freeze}, room=room_id)
        await sio.emit('system_message',
             system_msg(f'Room has been {status} by an admin.'),
             room=room_id)
        _sl.room_frozen(sid, users.get(sid, {}).get('display', sid[:8]), room_id, freeze)

    @sio.on('admin:freeze')
    async def handle_freeze(sid, data):
        if not isinstance(data, dict) or not sid:
            return
        room_id = str(data.get('room_id', ''))
        freeze = bool(data.get('freeze', True))
        await _do_freeze(sid, room_id, freeze)

    @sio.on('admin:freeze_room')
    async def handle_freeze_room(sid, data):
        if not isinstance(data, dict) or not sid:
            return
        room_id = str(data.get('room_id', ''))
        await _do_freeze(sid, room_id, True)

    @sio.on('admin:unfreeze_room')
    async def handle_unfreeze_room(sid, data):
        if not isinstance(data, dict) or not sid:
            return
        room_id = str(data.get('room_id', ''))
        await _do_freeze(sid, room_id, False)

    # ── admin:mod ─────────────────────────────────────────────────────────────

    @sio.on('admin:mod')
    async def handle_mod(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not sid or not user:
            return

        room_id = str(data.get('room_id', ''))
        target_disp = str(data.get('target', '') or data.get('username', ''))
        grant = bool(data.get('grant', True))

        room = get_room(room_id)
        if not room or room['creator_sid'] != sid:
            await sio.emit('error', {'message': 'Only the room creator can manage mods.'}, to=sid)
            return

        target_sid = sid_map.get(target_disp)
        if not target_sid:
            await sio.emit('error', {'message': 'User not found.'}, to=sid)
            return

        if grant:
            room['admins'].add(target_sid)
        else:
            room['admins'].discard(target_sid)

        action = 'granted mod' if grant else 'removed mod'
        await sio.emit('system_message',
             system_msg(f'{target_disp} was {action} by {user["display"]}.'),
             room=room_id)
        await sio.emit('room:members', room_member_list(room_id), room=room_id)

    # ── admin:server_kick (server-admin only) ─────────────────────────────────
    # Also aliased as admin:ban (frontend legacy name)

    async def _do_server_kick(sid, data):
        user = current_user(sid)
        if not sid or not user:
            return
        if not users.get(sid, {}).get('is_server_admin'):
            sec_log.warning('admin:server_kick: unauthorised attempt by sid=%s', sid)
            await sio.emit('error', {'code': 'FORBIDDEN', 'message': 'Not authorised.'}, to=sid)
            return
        target_disp = str(data.get('target', '') or data.get('username', ''))
        reason = str(data.get('reason', 'Removed by server admin.'))[:200]
        target_sid = sid_map.get(target_disp)
        if not target_sid or target_sid not in users:
            await sio.emit('error', {'message': 'User not found.'}, to=sid)
            return
        if users[target_sid].get('is_server_admin'):
            await sio.emit('error', {'message': 'Cannot kick another server admin.'}, to=sid)
            return
        sec_log.info('admin:server_kick: %s kicked %s reason=%r', user['display'], target_disp, reason)
        await sio.emit('admin:kicked', {'reason': reason}, to=target_sid)
        await sio.emit('system_message',
             system_msg(f'{target_disp} was removed by the server admin.'))

    @sio.on('admin:server_kick')
    async def handle_server_kick(sid, data):
        if not isinstance(data, dict):
            return
        await _do_server_kick(sid, data)

    @sio.on('admin:ban')
    async def handle_ban(sid, data):
        """Frontend alias for admin:server_kick."""
        if not isinstance(data, dict):
            return
        await _do_server_kick(sid, data)

    # ── admin:server_shadow_mute (server-admin only) ──────────────────────────
    # Also aliased as admin:mute (frontend name)

    async def _do_shadow_mute(sid, data, duration_default=300):
        user = current_user(sid)
        if not sid or not user:
            return
        if not users.get(sid, {}).get('is_server_admin'):
            sec_log.warning('admin:server_shadow_mute: unauthorised attempt by sid=%s', sid)
            await sio.emit('error', {'code': 'FORBIDDEN', 'message': 'Not authorised.'}, to=sid)
            return
        target_disp = str(data.get('target', '') or data.get('username', ''))
        duration_s = min(int(data.get('duration', duration_default)), 86400)
        target_sid = sid_map.get(target_disp)
        if not target_sid or target_sid not in users:
            await sio.emit('error', {'message': 'User not found.'}, to=sid)
            return
        shadow_muted[target_sid] = {'until': time.time() + duration_s}
        sec_log.info(
            'admin:server_shadow_mute: %s muted %s for %ds',
            user['display'], target_disp, duration_s,
        )
        await sio.emit('system_message', system_msg('Moderation action applied.'), to=sid)

    @sio.on('admin:server_shadow_mute')
    async def handle_server_shadow_mute(sid, data):
        if not isinstance(data, dict):
            return
        await _do_shadow_mute(sid, data)

    @sio.on('admin:mute')
    async def handle_mute(sid, data):
        """Frontend alias for admin:server_shadow_mute."""
        if not isinstance(data, dict):
            return
        await _do_shadow_mute(sid, data)

    # ── admin:unmute ─────────────────────────────────────────────────────────
    # No real 'unmute' in V1 — just clear the shadow_muted entry.

    @sio.on('admin:unmute')
    async def handle_unmute(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not sid or not user:
            return
        if not users.get(sid, {}).get('is_server_admin'):
            await sio.emit('error', {'code': 'FORBIDDEN', 'message': 'Not authorised.'}, to=sid)
            return
        target_disp = str(data.get('target', '') or data.get('username', ''))
        target_sid = sid_map.get(target_disp)
        if not target_sid:
            await sio.emit('error', {'message': 'User not found.'}, to=sid)
            return
        shadow_muted.pop(target_sid, None)
        sec_log.info('admin:unmute: %s unmuted %s', user['display'], target_disp)
        await sio.emit('system_message', system_msg('Moderation action applied.'), to=sid)

    # ── admin:delete_room ────────────────────────────────────────────────────
    # Server-admin or room admin can force-delete a room.

    @sio.on('admin:delete_room')
    async def handle_delete_room(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not sid or not user:
            return

        room_id = str(data.get('room_id', ''))
        room = get_room(room_id)
        if not room:
            await err(sid, 'Room not found.')
            return

        is_server_admin = users.get(sid, {}).get('is_server_admin', False)
        if not is_server_admin and not is_room_admin(sid, room_id):
            await err(sid, 'Not authorised.')
            return

        # Kick all members out
        members_copy = set(room['members'])
        for member_sid in members_copy:
            room['members'].discard(member_sid)
            await sio.leave_room(member_sid, room_id)
            set_user_room(member_sid, None)
            await sio.emit('room:left', {'room_id': room_id, 'reason': 'deleted'}, to=member_sid)

        # Cancel any pending delete timer
        t = room.get('delete_timer')
        if t is not None:
            try:
                t.cancel()
            except Exception:
                pass
            room['delete_timer'] = None

        from core.state import rooms as _rooms
        _rooms.pop(room_id, None)

        await sio.emit('room:deleted', {'room_id': room_id})
        await sio.emit('room:list', _public_room_list())
        sec_log.info('admin:delete_room: %s deleted room=%s', user['display'], room_id)

    # ── Helper ────────────────────────────────────────────────────────────────

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
