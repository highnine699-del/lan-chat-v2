# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
routes/socket_messages.py
Message handling Socket.IO handlers.
"""

import json
import logging
import os
import secrets as _sec
import time

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

log = logging.getLogger('lan-chat')
sec_log = logging.getLogger('lan-chat.security')

import state_log as _sl

from config import (
    MAX_MESSAGE_LEN, MAX_SIGNAL_BYTES,
    HIDE_VOTE_THRESHOLD, SPAM_COOLDOWN_S, SPAM_MSG_LIMIT, SPAM_MSG_LIMIT_PUBLIC, SPAM_WINDOW_S_PUBLIC,
    PUBLIC_MODE,
    UPLOAD_FOLDER,
)
from core.state import (
    users, sid_map, message_history, private_history, rooms,
    message_votes, analytics, user_state,
    private_key, append_private, now_ms, reputation_label,
    check_smart_spam, cooldown_remaining, filter_expired,
    record_msg_id,
    set_presence,
    is_room_admin,
)
from .socket_rate_limit import _check_signal_rate


def register_message_handlers(sio):
    """Register message handling handlers."""

    def current_user(sid):
        return users.get(sid) if sid else None

    async def err(sid, message, code='ERROR', context=None):
        payload = {'message': message, 'code': code}
        if context:
            payload['context'] = context
        await sio.emit('error', payload, to=sid)

    async def relay_to_target(event, payload, target):
        if target and target in sid_map:
            await sio.emit(event, payload, to=sid_map[target])

    async def dispatch_message(msg, target, sid):
        msg['_ts'] = time.time()
        temp_id = msg.pop('_tempId', None)
        sender_sid = sid

        if target == 'global':
            message_history.append(msg)
            await sio.emit('new_message', msg)
        elif target in rooms:
            room = rooms[target]
            if room['is_frozen']:
                await err(sid, 'This room is frozen. No messages allowed.', 'ROOM_FROZEN', {'room_id': target})
                return
            room['seq'] = room.get('seq', 0) + 1
            msg['seq'] = room['seq']
            room['messages'].append(msg)
            await sio.emit('new_message', msg, to=target)
        else:
            key = private_key(msg['from'], target)
            append_private(key, msg)
            if target in sid_map:
                await sio.emit('new_message', msg, to=sid_map[target])
            if sender_sid:
                await sio.emit('new_message', msg, to=sender_sid)

        if temp_id and sender_sid:
            await sio.emit('message_ack', {
                'tempId': temp_id,
                'msg_id': msg['msg_id'],
            }, to=sender_sid)

    def _find_message(msg_id, target, uid=None, sid=None):
        if target == 'global':
            for m in message_history:
                if m.get('msg_id') == msg_id:
                    return m
        elif target in rooms:
            for m in rooms[target]['messages']:
                if m.get('msg_id') == msg_id:
                    return m
        else:
            if uid is None:
                user = current_user(sid)
                uid = user['display'] if user else None
            if uid:
                key = private_key(uid, target)
                hist = private_history.get(key, [])
                for m in hist:
                    if m.get('msg_id') == msg_id:
                        return m
        return None

    # ── send_message ───────────────────────────────────────────────────────────

    @sio.on('send_message')
    async def handle_message(sid, data):
        if not isinstance(data, dict):
            return

        user = current_user(sid)
        if not user:
            return

        text = str(data.get('text', '')).strip()
        if not text:
            return

        spam_result = check_smart_spam(
            sid, text,
            msg_limit=SPAM_MSG_LIMIT_PUBLIC if PUBLIC_MODE else SPAM_MSG_LIMIT,
            window_s=SPAM_WINDOW_S_PUBLIC if PUBLIC_MODE else None,
        )
        if spam_result == 'cooldown':
            remaining = cooldown_remaining(sid)
            _sl.spam_action(sid, user['display'], 'cooldown', user_state.get(sid, {}).get('spam_count', 0))
            await sio.emit('cooldown', {
                'seconds': int(remaining) or SPAM_COOLDOWN_S,
                'message': f'Slow down! Wait {int(remaining) or SPAM_COOLDOWN_S}s.',
            }, to=sid)
            return
        elif spam_result == 'shadow':
            _sl.spam_action(sid, user['display'], 'shadow', user_state.get(sid, {}).get('spam_count', 0))
            fake_msg_id = _sec.token_hex(8)
            await sio.emit('new_message', {
                'type': 'text', 'from': user['display'],
                'color': user['color'], 'text': text,
                'time': now_ms(), 'to': data.get('to', 'global'),
                'msg_id': fake_msg_id,
            }, to=sid)
            analytics['messages_sent'] += 1
            return

        if len(text) > MAX_MESSAGE_LEN:
            text = text[:MAX_MESSAGE_LEN]

        target = str(data.get('to', 'global'))

        if target == 'global':
            pass
        elif target in rooms:
            room = rooms[target]
            if sid not in room['members']:
                await err(sid, 'You are not a member of this room.', 'NOT_MEMBER', {'room_id': target})
                return
        elif target in sid_map:
            pass
        else:
            await err(sid, 'Target not found.', 'TARGET_NOT_FOUND', {'target': target})
            return

        user['msg_count'] = user.get('msg_count', 0) + 1
        analytics['messages_sent'] += 1

        msg_id = _sec.token_hex(8)
        client_msg_id = data.get('msg_id')
        if isinstance(client_msg_id, str) and client_msg_id:
            if not record_msg_id(client_msg_id[:32]):
                sec_log.warning('send_message: duplicate msg_id=%s from sid=%s', client_msg_id[:16], sid)
                return
            msg_id = client_msg_id[:32]
        else:
            record_msg_id(msg_id)

        msg = {
            'type': 'text',
            'from': user['display'],
            'color': user['color'],
            'tag': user['tag'],
            'reputation': reputation_label(user['msg_count']),
            'text': text,
            'time': now_ms(),
            'to': target,
            'msg_id': msg_id,
        }

        if 'encrypted' in data:
            enc = data['encrypted']
            if isinstance(enc, str) and enc:
                msg['encrypted'] = enc

        reply_to = data.get('reply_to')
        if isinstance(reply_to, dict) and isinstance(reply_to.get('msg_id'), str):
            original = _find_message(str(reply_to['msg_id'])[:32], target, sid=sid)
            if original:
                msg['reply_to'] = {
                    'msg_id': original['msg_id'],
                    'from': original['from'],
                    'text': str(original.get('text', ''))[:200],
                }

        client_temp_id = data.get('_tempId')
        if isinstance(client_temp_id, str) and client_temp_id:
            msg['_tempId'] = client_temp_id[:64]

        await dispatch_message(msg, target, sid)
        _sl.message_sent(sid, user['display'], target, msg_id, 'text')

    # ── send_file ─────────────────────────────────────────────────────────────

    @sio.on('send_file')
    async def handle_file(sid, data):
        if not isinstance(data, dict):
            return

        user = current_user(sid)
        if not user:
            return

        url = str(data.get('url', ''))
        if not url.startswith('/uploads/'):
            return

        filename = url[len('/uploads/'):]
        if not filename or not os.path.isfile(os.path.join(UPLOAD_FOLDER, filename)):
            return

        target = str(data.get('to', 'global'))
        if target == 'global':
            pass
        elif target in rooms:
            if sid not in rooms[target]['members']:
                await err(sid, 'You are not a member of this room.', 'NOT_MEMBER', {'room_id': target})
                return
        elif target in sid_map:
            pass
        else:
            return

        user['msg_count'] = user.get('msg_count', 0) + 1
        analytics['files_uploaded'] += 1
        msg_id = _sec.token_hex(8)
        record_msg_id(msg_id)

        import mimetypes as _mt
        server_mime, _ = _mt.guess_type(filename)
        if not server_mime:
            server_mime = 'application/octet-stream'

        display_name = str(data.get('name', filename))[:260]

        msg = {
            'type': 'file',
            'from': user['display'],
            'color': user['color'],
            'tag': user['tag'],
            'reputation': reputation_label(user.get('msg_count', 0)),
            'url': url,
            'name': display_name,
            'file_type': server_mime,
            'time': now_ms(),
            'to': target,
            'msg_id': msg_id,
        }
        await dispatch_message(msg, target, sid)
        _sl.message_sent(sid, user['display'], target, msg_id, 'file')

    # ── message:edit ──────────────────────────────────────────────────────────

    @sio.on('message:edit')
    async def handle_message_edit(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return

        msg_id = str(data.get('msg_id', ''))[:32]
        new_text = str(data.get('text', '')).strip()[:MAX_MESSAGE_LEN]
        target = str(data.get('to', ''))

        if not msg_id or not new_text or not target:
            return

        if target in rooms and sid not in rooms[target]['members']:
            await sio.emit('error', {'code': 'FORBIDDEN', 'message': 'Cannot edit this message.'}, to=sid)
            return

        is_admin = target in rooms and is_room_admin(sid, target)
        stored_msg = _find_message(msg_id, target, uid=user['display'], sid=sid)
        if not is_admin:
            if stored_msg is None or stored_msg.get('from') != user['display']:
                sec_log.warning('message:edit: unauthorised sid=%s msg_id=%s target=%s', sid, msg_id, target)
                await sio.emit('error', {'code': 'FORBIDDEN', 'message': 'Cannot edit this message.'}, to=sid)
                return

        if stored_msg is not None:
            stored_msg['text'] = new_text
            stored_msg['edited'] = True

        payload = {
            'msg_id': msg_id,
            'text': new_text,
            'edited': True,
            'to': target,
        }
        if 'encrypted' in data:
            enc = data['encrypted']
            if isinstance(enc, str) and enc:
                payload['encrypted'] = enc

        if target == 'global':
            await sio.emit('message:edited', payload)
        elif target in rooms:
            await sio.emit('message:edited', payload, to=target)
        elif target in sid_map:
            await sio.emit('message:edited', payload, to=sid_map[target])
            await sio.emit('message:edited', payload, to=sid)
        _sl.message_edited(sid, user['display'], msg_id, target, by_admin=is_admin)

    # ── message:delete ────────────────────────────────────────────────────────

    @sio.on('message:delete')
    async def handle_message_delete(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return

        msg_id = str(data.get('msg_id', ''))[:32]
        target = str(data.get('to', ''))

        if not msg_id or not target:
            return

        if target in rooms and sid not in rooms[target]['members']:
            await sio.emit('error', {'code': 'FORBIDDEN', 'message': 'Cannot delete this message.'}, to=sid)
            return

        is_admin = target in rooms and is_room_admin(sid, target)
        stored_msg = _find_message(msg_id, target, uid=user['display'], sid=sid)
        if not is_admin:
            if stored_msg is None or stored_msg.get('from') != user['display']:
                sec_log.warning('message:delete: unauthorised sid=%s msg_id=%s target=%s', sid, msg_id, target)
                await sio.emit('error', {'code': 'FORBIDDEN', 'message': 'Cannot delete this message.'}, to=sid)
                return

        if stored_msg is not None:
            stored_msg['deleted'] = True
            stored_msg['text'] = ''

        payload = {'msg_id': msg_id, 'to': target}

        if target == 'global':
            await sio.emit('message:deleted', payload)
        elif target in rooms:
            await sio.emit('message:deleted', payload, to=target)
        elif target in sid_map:
            await sio.emit('message:deleted', payload, to=sid_map[target])
            await sio.emit('message:deleted', payload, to=sid)
        _sl.message_deleted(sid, user['display'], msg_id, target, by_admin=is_admin)

    # ── message:seen ──────────────────────────────────────────────────────────

    @sio.on('message:seen')
    async def handle_message_seen(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user:
            return

        msg_ids = data.get('msg_ids', [])
        sender = str(data.get('sender', ''))

        if not isinstance(msg_ids, list) or not sender:
            return

        if sender in sid_map:
            await sio.emit('message:seen', {
                'msg_ids': [str(m)[:32] for m in msg_ids[:50]],
                'by': user['display'],
            }, to=sid_map[sender])

    # ── typing indicators ─────────────────────────────────────────────────────

    @sio.on('typing')
    async def handle_typing(sid, data):
        user = current_user(sid)
        if not user or not isinstance(data, dict):
            return
        set_presence(sid, 'typing')
        target = str(data.get('to', 'global'))
        payload = {'username': user['display'], 'to': target}
        if target == 'global':
            await sio.emit('typing', payload, skip_sid=sid)
        elif target in rooms:
            await sio.emit('typing', payload, to=target, skip_sid=sid)
        elif target in sid_map:
            await sio.emit('typing', payload, to=sid_map[target])

    @sio.on('stop_typing')
    async def handle_stop_typing(sid, data):
        user = current_user(sid)
        if not user or not isinstance(data, dict):
            return
        set_presence(sid, 'active')
        target = str(data.get('to', 'global'))
        payload = {'username': user['display'], 'to': target}
        if target == 'global':
            await sio.emit('stop_typing', payload, skip_sid=sid)
        elif target in rooms:
            await sio.emit('stop_typing', payload, to=target, skip_sid=sid)
        elif target in sid_map:
            await sio.emit('stop_typing', payload, to=sid_map[target])

    # ── vote_hide ─────────────────────────────────────────────────────────────

    @sio.on('vote_hide')
    async def handle_vote_hide(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return

        msg_id = str(data.get('msg_id', ''))[:32]
        if not msg_id:
            return

        voters = message_votes.setdefault(msg_id, set())
        voters.add(user['uid'])

        if len(voters) >= HIDE_VOTE_THRESHOLD:
            await sio.emit('hide_message', {'msg_id': msg_id})
            message_votes.pop(msg_id, None)
        else:
            await sio.emit('vote_count', {
                'msg_id': msg_id,
                'votes': len(voters),
                'needed': HIDE_VOTE_THRESHOLD,
            })
