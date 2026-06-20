# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
routes/socket_auth.py
Authentication and user management Socket.IO handlers.
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

from config import (
    MAX_CONNECTIONS_PER_IP,
    PUBLIC_MODE, SERVER_PASSWORD, ADMIN_PASSWORD,
    JOIN_TOKEN_TTL_S,
)
from core.state import (
    users, sid_map, public_keys,
    rooms, user_state,
    spam_tracker, upload_counts,
    uid_sessions, ip_connections,
    active_sessions, analytics,
    message_history,
    register_session, update_session_room,
    mark_session_disconnected, remove_session, get_session,
    find_session_by_uid,
    get_user_list, next_color, unique_username,
    private_key, clean_username,
    generate_tag, init_user_state, set_presence,
    register_identity, unregister_identity, set_user_room,
    issue_session_token, verify_session_token,
    join_call, leave_call, teardown_call,
    get_call_session_id, get_call_phase as _get_phase,
    write_call_tombstone, consume_call_tombstone,
    reputation_label,
    filter_expired,
)
from .socket_rate_limit import (
    _check_join_rate, _get_client_ip, _uid_last_kick, _UID_KICK_COOLDOWN,
)


# Storage for environ dict keyed by sid — needed because handle_join
# doesn't receive environ, only handle_connect does.
_client_environ: dict = {}


def register_auth_handlers(sio):
    """Register authentication and user management handlers."""

    def current_sid(sid):
        return sid

    def current_user(sid):
        return users.get(sid) if sid else None

    def system_msg(text):
        return {'type': 'system', 'text': text, 'time': int(time.time() * 1000)}

    async def err(sid, message, code='ERROR', context=None):
        payload = {'message': message, 'code': code}
        if context:
            payload['context'] = context
        await sio.emit('error', payload, to=sid)

    # ── connect ───────────────────────────────────────────────────────────────

    @sio.on('connect')
    async def handle_connect(sid, environ):
        _client_environ[sid] = environ  # store for handlers that don't receive it
        if PUBLIC_MODE and not SERVER_PASSWORD:
            log.warning('Connection rejected: PUBLIC_MODE=true but SERVER_PASSWORD is not set.')
            return False

    # ── join ─────────────────────────────────────────────────────────────────

    @sio.on('join')
    async def handle_join(sid, data):
        if not isinstance(data, dict):
            return

        # Retrieve environ stored during handle_connect
        environ = _client_environ.get(sid, {})
        # Get client IP from environ
        client_ip = environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[-1].strip() if environ.get('HTTP_X_FORWARDED_FOR') else environ.get('REMOTE_ADDR', '127.0.0.1')
        
        if not _check_join_rate(client_ip):
            sec_log.warning('join: rate-limited ip=%s', client_ip)
            _sl.rate_limited(client_ip, 'join', 'join_rate')
            _sl.session_rejected(sid, client_ip, 'join_rate_limit', 'RATE_LIMITED')
            await err(sid, 'Too many join attempts. Please wait before trying again.', 'RATE_LIMITED')
            return

        if PUBLIC_MODE:
            if not SERVER_PASSWORD:
                await err(sid, 'Server is in public mode but no password is configured.', 'SERVER_LOCKED')
                return
            client_server_pw = str(data.get('password', '') or data.get('server_password', ''))
            if client_server_pw != SERVER_PASSWORD:
                sec_log.warning('join: wrong server password from ip=%s', client_ip)
                _sl.session_rejected(sid, client_ip, 'wrong_server_password', 'WRONG_PASSWORD')
                await err(sid, 'Incorrect server password.', 'WRONG_PASSWORD')
                return

        client_admin_pw = str(data.get('admin_password', ''))
        is_server_admin = bool(ADMIN_PASSWORD and client_admin_pw == ADMIN_PASSWORD)

        ip_set = ip_connections.setdefault(client_ip, set())
        ip_set = {s for s in ip_set if s in users or s == sid}
        ip_connections[client_ip] = ip_set
        if len(ip_set) >= MAX_CONNECTIONS_PER_IP and sid not in ip_set:
            _sl.session_rejected(sid, client_ip, 'too_many_connections', 'TOO_MANY_CONNECTIONS')
            await err(sid, f'Too many connections from your IP (max {MAX_CONNECTIONS_PER_IP}).', 'TOO_MANY_CONNECTIONS')
            return
        ip_set.add(sid)

        stale = users.pop(sid, None)
        if stale:
            unregister_identity(sid, stale['display'], stale.get('uid', ''))
            public_keys.pop(stale['display'], None)
            await sio.emit('user_list', get_user_list())

        client_uid = str(data.get('uid', ''))[:64]
        client_token = str(data.get('session_token', ''))

        if client_uid and client_token and verify_session_token(client_uid, client_token, client_ip):
            uid = client_uid
        elif client_uid and not client_token:
            from core.state import session_tokens as _st
            if client_uid not in _st:
                uid = client_uid
            else:
                sec_log.warning('join: uid=%.8s presented without token from ip=%s — issuing new uid', client_uid, client_ip)
                uid = _sec.token_hex(16)
        else:
            if client_uid and client_token:
                sec_log.warning('join: bad/expired token for uid=%.8s from ip=%s', client_uid, client_ip)
            uid = _sec.token_hex(16)

        tag = generate_tag(uid)

        old_sid = uid_sessions.get(uid)
        if old_sid and old_sid != sid and old_sid in users:
            now = time.time()
            last_kick = _uid_last_kick.get(uid, 0.0)
            if now - last_kick < _UID_KICK_COOLDOWN:
                await err(sid, 'Session takeover rejected. Please wait before reconnecting.', 'UID_COOLDOWN')
                return
            _uid_last_kick[uid] = now
            ghost = users.pop(old_sid, None)
            if ghost:
                unregister_identity(old_sid, ghost['display'], uid)
                public_keys.pop(ghost['display'], None)
                spam_tracker.pop(old_sid, None)
                upload_counts.pop(old_sid, None)
                await _leave_current_room_by_sid(old_sid, ghost['display'], sio)
                for ip_s in ip_connections.values():
                    ip_s.discard(old_sid)
                remove_session(old_sid)
                _sl.ghost_evicted(old_sid, sid, ghost['display'], uid)
        uid_sessions[uid] = sid

        session_token = issue_session_token(uid, client_ip)

        username = unique_username(clean_username(data.get('username', '')), sid)
        display = f'{username}#{tag}'
        color = next_color()

        users[sid] = {
            'username': username,
            'tag': tag,
            'display': display,
            'uid': uid,
            'color': color,
            'joined_at': time.time(),
            'msg_count': 0,
            'room_id': None,
            'presence': 'active',
            'persona': None,
            'is_server_admin': is_server_admin,
        }
        register_identity(sid, display, uid)
        upload_counts[sid] = 0
        init_user_state(sid, username, tag, color)
        register_session(sid, uid, display, client_ip)

        pub_key = data.get('publicKey')
        if isinstance(pub_key, dict):
            public_keys[display] = pub_key

        if len(users) > analytics['peak_users']:
            analytics['peak_users'] = len(users)

        if display in sid_map and sid_map[display] != sid:
            _sl.session_rejected(sid, client_ip, 'display_name_taken', 'NAME_TAKEN')
            await err(sid, 'That display name is already in use. Try a different username.', 'NAME_TAKEN')
            users.pop(sid, None)
            unregister_identity(sid, display, uid)
            upload_counts.pop(sid, None)
            remove_session(sid)
            ip_set.discard(sid)
            return

        await sio.emit('joined', {
            'username': username,
            'tag': tag,
            'display': display,
            'color': color,
            'uid': uid,
            'session_token': session_token,
            'reputation': reputation_label(0),
            'is_server_admin': is_server_admin,
        }, to=sid)

        other_keys = dict(public_keys)
        other_keys.pop(display, None)
        await sio.emit('all_keys', other_keys, to=sid)
        await sio.emit('message_history', list(message_history)[-100:], to=sid)

        if pub_key:
            await sio.emit('peer_key', {'username': display, 'publicKey': pub_key}, skip_sid=sid)

        await sio.emit('user_list', get_user_list())
        await sio.emit('system_message', system_msg(f'{display} joined'))
        log.info('[SESSION] actor=%s handler=join', display)
        _sl.session_joined(sid, display, client_ip, uid_reclaimed=(uid == client_uid), is_admin=is_server_admin)

    # ── disconnect ────────────────────────────────────────────────────────────

    @sio.on('disconnect')
    async def handle_disconnect(sid):
        _client_environ.pop(sid, None)  # clean up stored environ
        mark_session_disconnected(sid)

        user = users.pop(sid, None)
        if not user:
            remove_session(sid)
            return

        display = user['display']
        uid = user.get('uid', '')
        room_id_for_log = user.get('room_id')
        try:
            unregister_identity(sid, display, uid)
            public_keys.pop(display, None)
            spam_tracker.pop(sid, None)
            upload_counts.pop(sid, None)

            affected_call = leave_call(sid)
            if affected_call:
                _ts_uuid = get_call_session_id(affected_call)
                _ts_phase = _get_phase(affected_call) or 'UNKNOWN'

                remaining = teardown_call(affected_call)
                for peer_sid in remaining:
                    await sio.emit('call-ended', {'reason': 'peer_disconnected'}, to=peer_sid)
                sec_log.info('call teardown: call_id=%s triggered by disconnect of sid=%s', affected_call, sid)

                if _ts_uuid and _ts_phase in ('ANSWERED', 'CONNECTING', 'ACTIVE'):
                    for peer_sid in remaining:
                        peer = users.get(peer_sid, {})
                        peer_uid = peer.get('uid', '')
                        if uid and peer_uid:
                            write_call_tombstone(uid, peer_uid, _ts_uuid, _ts_phase)
                            sec_log.info(
                                'call tombstone written: uid=%.8s peer_uid=%.8s phase=%s',
                                uid, peer_uid, _ts_phase,
                            )
                            break

            try:
                # Get client IP from session
                sess = get_session(sid)
                if sess:
                    client_ip = sess.get('ip', '')
                    if client_ip in ip_connections:
                        ip_connections[client_ip].discard(sid)
                        if not ip_connections[client_ip]:
                            del ip_connections[client_ip]
            except RuntimeError:
                pass

            sess = get_session(sid)
            room_id_from_registry = sess['room_id'] if sess else None

            if room_id_from_registry:
                await _leave_room_by_id(sid, room_id_from_registry, display, sio)
            else:
                await _leave_current_room_by_sid(sid, display, sio)
        finally:
            user_state.pop(sid, None)
            remove_session(sid)
            await sio.emit('user_list', get_user_list())
            await sio.emit('system_message', system_msg(f'{display} left'))
            log.info('[SESSION] actor=%s handler=disconnect', display)
            _sl.session_disconnected(sid, display, room_id_for_log)

    # ── user:presence ─────────────────────────────────────────────────────────

    @sio.on('user:presence')
    async def handle_presence(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return
        state_str = str(data.get('state', 'active'))
        old_presence = user_state.get(sid, {}).get('presence', 'active')
        set_presence(sid, state_str)
        _sl.presence_changed(sid, user['display'], old_presence, state_str)
        await sio.emit('user:presence', {
            'display': user['display'],
            'state': state_str,
        })

    # ── reconnect_sync ────────────────────────────────────────────────────────

    @sio.on('reconnect_sync')
    async def handle_reconnect_sync(sid, data):
        """
        Formal state reconciliation on reconnect.

        Client sends:
          {
            last_seq:   int | None   — last room message seq the client saw
            room_id:    str | None   — room the client thinks it's in
            known_ids:  list[str]    — msg_ids the client already has (global)
          }

        Server replies with sync_reply containing:
          {
            missed:      list[dict]  — messages the client is missing
            current_seq: int         — current room seq (0 if not in a room)
            room_id:     str | None  — confirmed room_id (None if not in room)
          }

        This enforces diff repair: the client can detect gaps and request
        replay without relying on event ordering.
        """
        if not isinstance(data, dict):
            return

        user = current_user(sid)
        if not user or not sid:
            return

        last_seq   = data.get('last_seq')
        # Fix C: ignore client-sent room_id entirely — use server-tracked room
        # The client cannot be trusted to report which room it's in.
        server_room_id = user.get('room_id') or user_state.get(sid, {}).get('room_id')
        room_id        = server_room_id
        known_ids  = set(str(m)[:32] for m in data.get('known_ids', [])[:200])

        missed      = []
        current_seq = 0

        # ── Room reconciliation ───────────────────────────────────────────────
        if room_id and room_id in rooms:
            room = rooms[room_id]

            # Security: only send history to current members of the room
            if sid not in room['members']:
                await sio.emit('sync_reply', {
                    'missed':      [],
                    'current_seq': 0,
                    'room_id':     None,
                }, to=sid)
                return

            current_seq = room.get('seq', 0)

            if last_seq is not None and isinstance(last_seq, int):
                # Send all messages with seq > last_seq (diff repair)
                missed = [
                    m for m in filter_expired(room['messages'], room['ttl'])
                    if m.get('seq', 0) > last_seq
                ]
            else:
                # No seq info — send full room history
                missed = filter_expired(room['messages'], room['ttl'])

        # ── Global reconciliation (known_ids diff) ────────────────────────────
        elif not room_id:
            if known_ids:
                # Send global messages the client doesn't have
                missed = [
                    m for m in list(message_history)[-100:]
                    if m.get('msg_id') and m['msg_id'] not in known_ids
                ]
            else:
                # Client has no known IDs — send full recent history
                missed = [
                    m for m in list(message_history)[-100:]
                    if m.get('msg_id')
                ]

        await sio.emit('sync_reply', {
            'missed':      missed,
            'current_seq': current_seq,
            'room_id':     room_id,
        }, to=sid)

    # ── user:switch_persona ───────────────────────────────────────────────────

    @sio.on('user:switch_persona')
    async def handle_switch_persona(sid, data):
        if not isinstance(data, dict):
            return
        user = current_user(sid)
        if not user or not sid:
            return

        new_name = clean_username(data.get('name', ''))
        raw_color = str(data.get('color', user['color'])).strip()
        import re as _re
        new_color = raw_color if _re.match(r'^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$', raw_color) else user['color']

        old_display = user['display']
        new_display = f"{new_name}#{user['tag']}"

        if new_display != old_display and new_display in sid_map:
            await err(sid, 'That name is already in use. Choose a different one.', 'NAME_TAKEN')
            return

        old_color = user.get('color')

        unregister_identity(sid, old_display, user['uid'])
        user['username'] = new_name
        user['display'] = new_display
        user['color'] = new_color
        user['persona'] = new_name
        register_identity(sid, new_display, user['uid'])

        color_changed = (old_color != new_color)

        announcement = system_msg(f'{old_display} is now {user["display"]}')
        await sio.emit('system_message', announcement)
        await sio.emit('user_list', get_user_list())
        await sio.emit('persona_switched', {
            'old': old_display,
            'new': user['display'],
        })
        _sl.persona_switched(sid, old_display, user['display'], color_changed=color_changed)


async def _leave_current_room_by_sid(sid, display, sio):
    sess = get_session(sid)
    room_id = sess['room_id'] if sess else None
    if room_id:
        await _leave_room_by_id(sid, room_id, display, sio)


async def _leave_room_by_id(sid, room_id, display, sio):
    from core.state import get_room, room_member_list, schedule_room_delete
    room = get_room(room_id)
    if not room:
        return
    room['members'].discard(sid)
    await sio.leave_room(sid, room_id)
    await sio.emit('system_message',
         {'type': 'system', 'text': f'{display} left the room.', 'time': int(time.time() * 1000)},
         room=room_id)
    await sio.emit('room:members', room_member_list(room_id), room=room_id)
    if not room['members']:
        schedule_room_delete(room_id, sio)
    _sl.room_left(sid, display, room_id, room['name'])
