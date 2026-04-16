"""
routes/sockets.py — All Socket.IO event handlers.

Prefixed event naming convention
---------------------------------
room:create       Create a new room
room:join         Join an existing room
room:leave        Leave current room
room:list         Get list of public rooms
user:presence     Update own presence state
user:switch_persona  Switch to a different persona
admin:kick        Kick a user from a room (room admin only)
admin:freeze      Freeze / unfreeze a room (room admin only)
admin:mod         Grant / revoke mod status (room admin only)
message:send      (legacy: send_message)
message:send_file (legacy: send_file)
"""
import json
import os
import time
import secrets as _sec

from flask import request
from flask_socketio import emit, join_room, leave_room

from config import (
    MAX_MESSAGE_LEN, MAX_SIGNAL_BYTES, UPLOAD_FOLDER,
    HIDE_VOTE_THRESHOLD, SPAM_COOLDOWN_S,
    MAX_ROOM_NAME_LEN, EPHEMERAL_TTLS, JOIN_TOKEN_TTL_S,
    SERVER_PASSWORD, MAX_CONNECTIONS_PER_IP,
)
from state import (
    # core state
    users, sid_map, public_keys,
    message_history, private_history,
    rooms, user_state, shadow_muted,
    message_votes, spam_tracker, analytics,
    join_tokens,
    uid_sessions, ip_connections, upload_counts,
    # helpers
    get_user_list, next_color, unique_username,
    private_key, append_private, now_ms, clean_username,
    generate_tag, reputation_label,
    init_user_state, set_presence,
    create_room, get_room, is_room_admin,
    room_member_list, schedule_room_delete, cancel_room_delete,
    check_smart_spam, cooldown_remaining,
    filter_expired, clean_room_name,
)


def register_socket_handlers(socketio):
    """Bind all Socket.IO event handlers to *socketio*."""

    # ── Module-level helpers ──────────────────────────────────────────────────

    def current_sid() -> str | None:
        return getattr(request, 'sid', None)

    def current_user() -> dict | None:
        sid = current_sid()
        return users.get(sid) if sid else None

    def system_msg(text: str) -> dict:
        return {'type': 'system', 'text': text, 'time': now_ms()}

    def err(message: str, code: str = 'ERROR', context: dict | None = None) -> None:
        """Emit a standardized error event."""
        payload = {'message': message, 'code': code}
        if context:
            payload['context'] = context
        emit('error', payload)

    def relay_to_target(event: str, payload: dict, target: str | None) -> None:
        """Emit to a named peer only if they are online."""
        if target and target in sid_map:
            emit(event, payload, to=sid_map[target])

    def dispatch_message(msg: dict, target: str) -> None:
        """
        Route a message to the correct destination:
          'global'       → global history + broadcast
          room_id        → room history + room broadcast
          display string → private history + both parties
        """
        # Stamp internal timestamp for TTL filtering
        msg['_ts'] = time.time()

        if target == 'global':
            message_history.append(msg)
            emit('new_message', msg, broadcast=True)

        elif target in rooms:
            room = rooms[target]
            if room['is_frozen']:
                emit('error', {
                    'code':    'ROOM_FROZEN',
                    'message': 'This room is frozen. No messages allowed.',
                    'context': {'room_id': target},
                })
                return
            # Assign per-room sequence number for ordering
            room['seq'] = room.get('seq', 0) + 1
            msg['seq'] = room['seq']
            room['messages'].append(msg)
            emit('new_message', msg, to=target)   # Socket.IO room broadcast

        else:
            # Private DM
            key = private_key(msg['from'], target)
            append_private(key, msg)
            if target in sid_map:
                emit('new_message', msg, to=sid_map[target])
            sid = current_sid()
            if sid:
                emit('new_message', msg, to=sid)

    # ── join ─────────────────────────────────────────────────────────────────

    @socketio.on('join')
    def handle_join(data):
        """Register a new user. Cleans up stale sessions on reconnect."""
        if not isinstance(data, dict):
            return

        sid = current_sid()
        if not sid:
            return

        # ── Server password check ─────────────────────────────────────────────
        if SERVER_PASSWORD:
            client_pw = str(data.get('server_password', ''))
            if client_pw != SERVER_PASSWORD:
                emit('error', {
                    'code':    'AUTH_FAILED',
                    'message': 'Wrong server password.',
                })
                return

        # ── IP connection limit ───────────────────────────────────────────────
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr or '').split(',')[0].strip()
        ip_set = ip_connections.setdefault(client_ip, set())
        # Remove stale sids from the IP set (disconnected clients)
        ip_set = {s for s in ip_set if s in users or s == sid}
        ip_connections[client_ip] = ip_set
        if len(ip_set) >= MAX_CONNECTIONS_PER_IP and sid not in ip_set:
            emit('error', {
                'code':    'TOO_MANY_CONNECTIONS',
                'message': f'Too many connections from your IP (max {MAX_CONNECTIONS_PER_IP}).',
            })
            return
        ip_set.add(sid)

        # ── Clean up stale session by SID ─────────────────────────────────────
        stale = users.pop(sid, None)
        if stale:
            sid_map.pop(stale['display'], None)
            public_keys.pop(stale['display'], None)
            user_state.pop(sid, None)
            emit('user_list', get_user_list(), broadcast=True)

        uid = str(data.get('uid', ''))[:64] or _sec.token_hex(16)
        tag = generate_tag(uid)

        # ── Ghost session cleanup: remove old session for same uid ────────────
        old_sid = uid_sessions.get(uid)
        if old_sid and old_sid != sid and old_sid in users:
            ghost = users.pop(old_sid, None)
            if ghost:
                sid_map.pop(ghost['display'], None)
                public_keys.pop(ghost['display'], None)
                spam_tracker.pop(old_sid, None)
                upload_counts.pop(old_sid, None)
                _leave_current_room_by_sid(old_sid, ghost['display'])
                user_state.pop(old_sid, None)
                # Remove from IP tracking
                for ip_s in ip_connections.values():
                    ip_s.discard(old_sid)
        uid_sessions[uid] = sid

        username = unique_username(clean_username(data.get('username', '')), sid)
        display  = f'{username}#{tag}'
        color    = next_color()

        users[sid] = {
            'username':  username,
            'tag':       tag,
            'display':   display,
            'uid':       uid,
            'color':     color,
            'joined_at': time.time(),
            'msg_count': 0,
            'room_id':   None,
            'presence':  'active',
            'persona':   None,
        }
        sid_map[display] = sid
        upload_counts[sid] = 0
        init_user_state(sid, username, tag, color)

        pub_key = data.get('publicKey')
        if isinstance(pub_key, dict):
            public_keys[display] = pub_key

        # Update peak users analytics
        if len(users) > analytics['peak_users']:
            analytics['peak_users'] = len(users)

        emit('joined', {
            'username':   username,
            'tag':        tag,
            'display':    display,
            'color':      color,
            'uid':        uid,
            'reputation': reputation_label(0),
        })

        other_keys = dict(public_keys)
        other_keys.pop(display, None)
        emit('all_keys', other_keys)
        emit('message_history', list(message_history)[-100:])

        if pub_key:
            emit('peer_key', {'username': display, 'publicKey': pub_key},
                 broadcast=True, include_self=False)

        emit('user_list', get_user_list(), broadcast=True)
        emit('system_message', system_msg(f'{display} joined'), broadcast=True)

    # ── send_message (legacy + room-aware) ───────────────────────────────────

    @socketio.on('send_message')
    def handle_message(data):
        if not isinstance(data, dict):
            return

        user = current_user()
        if not user:
            return

        sid = current_sid()

        # Smart spam detection
        text = str(data.get('text', '')).strip()
        if not text:
            return

        spam_result = check_smart_spam(sid, text)
        if spam_result == 'cooldown':
            remaining = cooldown_remaining(sid)
            emit('cooldown', {
                'seconds': int(remaining) or SPAM_COOLDOWN_S,
                'message': f'Slow down! Wait {int(remaining) or SPAM_COOLDOWN_S}s.',
            })
            return
        elif spam_result == 'shadow':
            # Shadow mute: pretend it worked, nobody else sees it
            fake_msg_id = _sec.token_hex(8)
            emit('new_message', {
                'type': 'text', 'from': user['display'],
                'color': user['color'], 'text': text,
                'time': now_ms(), 'to': data.get('to', 'global'),
                'msg_id': fake_msg_id,
            })
            analytics['messages_sent'] += 1
            return

        if len(text) > MAX_MESSAGE_LEN:
            text = text[:MAX_MESSAGE_LEN]

        target = str(data.get('to', 'global'))

        # ── Server-side validation ────────────────────────────────────────────
        if target == 'global':
            pass  # everyone can post to global
        elif target in rooms:
            # Must be a member of the room to post
            room = rooms[target]
            if sid not in room['members']:
                err('You are not a member of this room.',
                    'NOT_MEMBER', {'room_id': target})
                return
        elif target in sid_map:
            pass  # DM — target exists
        else:
            err('Target not found.', 'TARGET_NOT_FOUND', {'target': target})
            return

        user['msg_count'] = user.get('msg_count', 0) + 1
        analytics['messages_sent'] += 1

        msg_id = _sec.token_hex(8)
        msg = {
            'type':       'text',
            'from':       user['display'],
            'color':      user['color'],
            'tag':        user['tag'],
            'reputation': reputation_label(user['msg_count']),
            'text':       text,
            'time':       now_ms(),
            'to':         target,
            'msg_id':     msg_id,
        }

        if 'encrypted' in data:
            enc = data['encrypted']
            if isinstance(enc, str) and enc:
                msg['encrypted'] = enc

        dispatch_message(msg, target)

    # ── send_file ─────────────────────────────────────────────────────────────

    @socketio.on('send_file')
    def handle_file(data):
        if not isinstance(data, dict):
            return

        user = current_user()
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
                err('You are not a member of this room.',
                    'NOT_MEMBER', {'room_id': target})
                return
        elif target in sid_map:
            pass
        else:
            return

        user['msg_count'] = user.get('msg_count', 0) + 1
        analytics['files_uploaded'] += 1
        msg_id = _sec.token_hex(8)
        msg = {
            'type':       'file',
            'from':       user['display'],
            'color':      user['color'],
            'tag':        user['tag'],
            'reputation': reputation_label(user.get('msg_count', 0)),
            'url':        url,
            'name':       str(data.get('name', 'file'))[:260],
            'file_type':  str(data.get('file_type', 'file'))[:128],
            'time':       now_ms(),
            'to':         target,
            'msg_id':     msg_id,
        }
        dispatch_message(msg, target)

    # ── typing indicators ─────────────────────────────────────────────────────

    @socketio.on('typing')
    def handle_typing(data):
        user = current_user()
        if not user or not isinstance(data, dict):
            return
        sid = current_sid()
        set_presence(sid, 'typing')
        target  = str(data.get('to', 'global'))
        payload = {'username': user['display'], 'to': target}
        if target == 'global':
            emit('typing', payload, broadcast=True, include_self=False)
        elif target in rooms:
            emit('typing', payload, to=target, include_self=False)
        elif target in sid_map:
            emit('typing', payload, to=sid_map[target])

    @socketio.on('stop_typing')
    def handle_stop_typing(data):
        user = current_user()
        if not user or not isinstance(data, dict):
            return
        sid = current_sid()
        set_presence(sid, 'active')
        target  = str(data.get('to', 'global'))
        payload = {'username': user['display'], 'to': target}
        if target == 'global':
            emit('stop_typing', payload, broadcast=True, include_self=False)
        elif target in rooms:
            emit('stop_typing', payload, to=target, include_self=False)
        elif target in sid_map:
            emit('stop_typing', payload, to=sid_map[target])

    # ── user:presence ─────────────────────────────────────────────────────────

    @socketio.on('user:presence')
    def handle_presence(data):
        """Client updates its own presence state."""
        if not isinstance(data, dict):
            return
        sid = current_sid()
        user = current_user()
        if not user or not sid:
            return
        state_str = str(data.get('state', 'active'))
        set_presence(sid, state_str)
        # Broadcast updated presence to everyone
        emit('user:presence', {
            'display': user['display'],
            'state':   state_str,
        }, broadcast=True)

    # ── user:switch_persona ───────────────────────────────────────────────────

    @socketio.on('user:switch_persona')
    def handle_switch_persona(data):
        """
        Switch to a different persona (name + color).
        The SID stays the same. A system message announces the switch.
        """
        if not isinstance(data, dict):
            return
        user = current_user()
        sid  = current_sid()
        if not user or not sid:
            return

        new_name = clean_username(data.get('name', ''))
        new_color = str(data.get('color', user['color']))[:7]

        old_display = user['display']

        # Update sid_map
        sid_map.pop(old_display, None)
        user['username'] = new_name
        user['display']  = f"{new_name}#{user['tag']}"
        user['color']    = new_color
        user['persona']  = new_name
        sid_map[user['display']] = sid

        # Update user_state
        if sid in user_state:
            user_state[sid]['username'] = new_name
            user_state[sid]['color']    = new_color

        # Announce the switch
        announcement = system_msg(f'{old_display} is now {user["display"]}')
        emit('system_message', announcement, broadcast=True)
        emit('user_list', get_user_list(), broadcast=True)
        emit('persona_switched', {
            'old': old_display,
            'new': user['display'],
        }, broadcast=True)

    # ── room:create ───────────────────────────────────────────────────────────

    @socketio.on('room:create')
    def handle_room_create(data):
        """
        Create a new room.

        Client sends:
          {name, visibility, password?, ttl?}

        visibility: 'public' | 'private'
          - public  → no password, appears in room:list
          - private → optional password, NOT in room:list (join by room_id)

        ttl: '5min' | '1hour' | 'session'
        """
        if not isinstance(data, dict):
            return
        user = current_user()
        sid  = current_sid()
        if not user or not sid:
            return

        name = clean_room_name(data.get('name', ''))
        if not name:
            emit('error', {'message': 'Invalid room name. Use letters, numbers, spaces, - or .'})
            return

        visibility = str(data.get('visibility', 'public'))
        if visibility not in ('public', 'private'):
            visibility = 'public'

        # Password only meaningful for private rooms; create_room enforces this
        password = str(data.get('password', ''))[:64] or None
        ttl_key  = str(data.get('ttl', 'session'))
        ttl      = EPHEMERAL_TTLS.get(ttl_key)

        room = create_room(name, sid, visibility=visibility, password=password, ttl=ttl)
        if room is None:
            emit('error', {'message': 'Server is at room capacity. Try again later.'})
            return

        room_id = room['id']

        # Apply require_approval flag (private rooms only)
        if visibility == 'private' and data.get('require_approval'):
            room['require_approval'] = True

        # Creator joins immediately
        room['members'].add(sid)
        join_room(room_id)
        users[sid]['room_id'] = room_id
        if sid in user_state:
            user_state[sid]['room_id'] = room_id

        emit('room:created', {
            'room_id':    room_id,
            'name':       room['name'],
            'visibility': room['visibility'],
            'ttl':        ttl,
            'members':    room_member_list(room_id),
            'is_admin':   True,
        })

        # Only update the public list (private rooms don't appear there)
        emit('room:list', _public_room_list(), broadcast=True)

    # ── room:key ──────────────────────────────────────────────────────────────

    @socketio.on('room:key')
    def handle_room_key(data):
        """
        Room creator uploads the AES-GCM session key (as JWK) for the room.
        The server stores it and relays it to any members already in the room,
        and to future joiners via room:joined.

        The server never uses this key — it is opaque bytes to the relay.
        Only room members receive it.
        """
        if not isinstance(data, dict):
            return
        sid  = current_sid()
        user = current_user()
        if not sid or not user:
            return

        room_id = str(data.get('room_id', ''))
        key_jwk = data.get('key')   # dict (JWK)

        room = get_room(room_id)
        if not room:
            return

        # Only the room creator may set the session key
        if room['creator_sid'] != sid:
            return

        # Validate: must be a dict (JWK object), not a string or other type
        if not isinstance(key_jwk, dict):
            return

        room['session_key'] = key_jwk

        # Distribute to all current members except the creator
        for member_sid in room['members']:
            if member_sid != sid:
                emit('room:key', {
                    'room_id': room_id,
                    'key':     key_jwk,
                }, to=member_sid)

    # ── room:join ─────────────────────────────────────────────────────────────

    @socketio.on('room:join')
    def handle_room_join(data):
        """
        Join a public room by room_id.
        Public rooms have no password — if a password is somehow sent it is ignored.
        For private rooms use room:join_private.
        """
        if not isinstance(data, dict):
            return
        user = current_user()
        sid  = current_sid()
        if not user or not sid:
            return

        room_id = str(data.get('room_id', ''))
        room    = get_room(room_id)

        if not room:
            emit('error', {'message': 'Room not found.'})
            return

        if room['visibility'] == 'private':
            emit('error', {'message': 'This is a private room. Use "Join Private Room".'})
            return

        _do_join_room(sid, user, room)

    @socketio.on('room:join_private')
    def handle_room_join_private(data):
        """
        Join a private room by room_id + optional password.
        Private rooms are not listed publicly — the user must know the room_id.
        """
        if not isinstance(data, dict):
            return
        user = current_user()
        sid  = current_sid()
        if not user or not sid:
            return

        room_id  = str(data.get('room_id', ''))
        password = str(data.get('password', ''))
        room     = get_room(room_id)

        if not room:
            emit('error', {'message': 'Room not found.'})
            return

        if room['visibility'] != 'private':
            # Public rooms can be joined via room:join — redirect gracefully
            _do_join_room(sid, user, room)
            return

        if room['password'] and room['password'] != password:
            emit('error', {'message': 'Wrong password.'})
            return

        # If room requires approval, queue a knock instead of joining directly
        if room.get('require_approval'):
            room['pending_knocks'][sid] = user['display']
            # Notify all admins
            for admin_sid in room['admins']:
                emit('room:knock', {
                    'room_id':  room_id,
                    'sid':      sid,
                    'display':  user['display'],
                }, to=admin_sid)
            emit('room:knock_pending', {
                'room_id': room_id,
                'name':    room['name'],
            })
            return

        _do_join_room(sid, user, room)

    # ── room:leave ────────────────────────────────────────────────────────────

    @socketio.on('room:leave')
    def handle_room_leave(data):
        user = current_user()
        sid  = current_sid()
        if not user or not sid:
            return
        _leave_current_room(sid, user)
        emit('room:left', {})

    # ── room:set_approval ─────────────────────────────────────────────────────

    @socketio.on('room:set_approval')
    def handle_set_approval(data):
        """Toggle require_approval on a private room. Admin only."""
        if not isinstance(data, dict):
            return
        sid = current_sid()
        if not sid:
            return
        room_id  = str(data.get('room_id', ''))
        enabled  = bool(data.get('enabled', True))
        if not is_room_admin(sid, room_id):
            emit('error', {'message': 'Not authorised.'})
            return
        room = get_room(room_id)
        if not room:
            return
        room['require_approval'] = enabled

    # ── room:knock_approve / room:knock_deny ──────────────────────────────────

    @socketio.on('room:knock_approve')
    def handle_knock_approve(data):
        """Admin approves a pending knock — the knocker joins the room."""
        if not isinstance(data, dict):
            return
        sid  = current_sid()
        user = current_user()
        if not sid or not user:
            return
        room_id     = str(data.get('room_id', ''))
        knocker_sid = str(data.get('sid', ''))
        if not is_room_admin(sid, room_id):
            return
        room = get_room(room_id)
        if not room or knocker_sid not in room.get('pending_knocks', {}):
            return
        room['pending_knocks'].pop(knocker_sid, None)

        # Issue a time-limited join token instead of joining directly.
        # The knocker must present this token within JOIN_TOKEN_TTL_S seconds.
        token = _sec.token_hex(16)
        join_tokens[token] = {
            'room_id': room_id,
            'sid':     knocker_sid,
            'expires': time.time() + JOIN_TOKEN_TTL_S,
        }
        emit('room:join_approved', {
            'room_id': room_id,
            'token':   token,
            'ttl':     JOIN_TOKEN_TTL_S,
        }, to=knocker_sid)

    @socketio.on('room:knock_deny')
    def handle_knock_deny(data):
        """Admin denies a pending knock."""
        if not isinstance(data, dict):
            return
        sid = current_sid()
        if not sid:
            return
        room_id     = str(data.get('room_id', ''))
        knocker_sid = str(data.get('sid', ''))
        if not is_room_admin(sid, room_id):
            return
        room = get_room(room_id)
        if not room:
            return
        room['pending_knocks'].pop(knocker_sid, None)
        emit('room:knock_denied', {'room_id': room_id}, to=knocker_sid)

    # ── room:join_with_token ──────────────────────────────────────────────────

    @socketio.on('room:join_with_token')
    def handle_join_with_token(data):
        """
        Complete a knock-approved join using a time-limited token.
        The token was issued by room:knock_approve and sent to the knocker.
        """
        if not isinstance(data, dict):
            return
        sid  = current_sid()
        user = current_user()
        if not sid or not user:
            return

        token = str(data.get('token', ''))
        entry = join_tokens.pop(token, None)

        if not entry:
            err('Invalid or expired join token.', 'INVALID_TOKEN')
            return

        if time.time() > entry['expires']:
            err('Join token has expired. Request approval again.',
                'TOKEN_EXPIRED', {'room_id': entry['room_id']})
            return

        if entry['sid'] != sid:
            err('This token was not issued for your session.', 'TOKEN_MISMATCH')
            return

        room = get_room(entry['room_id'])
        if not room:
            err('Room no longer exists.', 'ROOM_NOT_FOUND',
                {'room_id': entry['room_id']})
            return

        _do_join_room(sid, user, room)

    @socketio.on('room:call')
    def handle_room_call(data):
        """
        Broadcast a call invitation to all members of a room.
        The caller's client then initiates individual WebRTC connections
        to each member who accepts.
        """
        if not isinstance(data, dict):
            return
        user = current_user()
        sid  = current_sid()
        if not user or not sid:
            return
        room_id   = str(data.get('room_id', ''))
        call_type = str(data.get('call_type', 'voice'))
        if call_type not in ('voice', 'video'):
            call_type = 'voice'
        room = get_room(room_id)
        if not room or sid not in room['members']:
            return
        # Notify every other member
        for member_sid in room['members']:
            if member_sid != sid:
                emit('room:incoming_call', {
                    'room_id':   room_id,
                    'room_name': room['name'],
                    'from':      user['display'],
                    'call_type': call_type,
                }, to=member_sid)

    # ── room:list ─────────────────────────────────────────────────────────────

    @socketio.on('room:list')
    def handle_room_list(data):
        emit('room:list', _public_room_list())

    # ── admin:kick ────────────────────────────────────────────────────────────

    @socketio.on('admin:kick')
    def handle_kick(data):
        """Kick a user from a room. Room admin only."""
        if not isinstance(data, dict):
            return
        sid  = current_sid()
        user = current_user()
        if not sid or not user:
            return

        room_id      = str(data.get('room_id', ''))
        target_disp  = str(data.get('target', ''))

        if not is_room_admin(sid, room_id):
            emit('error', {'message': 'Not authorised.'})
            return

        target_sid = sid_map.get(target_disp)
        if not target_sid:
            emit('error', {'message': 'User not found.'})
            return

        room = get_room(room_id)
        if not room or target_sid not in room['members']:
            emit('error', {'message': 'User is not in this room.'})
            return

        # Remove from room
        room['members'].discard(target_sid)
        leave_room(room_id, sid=target_sid)
        if target_sid in users:
            users[target_sid]['room_id'] = None
        if target_sid in user_state:
            user_state[target_sid]['room_id'] = None

        emit('admin:kicked', {'room_id': room_id}, to=target_sid)
        emit('system_message',
             system_msg(f'{target_disp} was removed by an admin.'),
             to=room_id)
        emit('room:members', room_member_list(room_id), to=room_id)

        if not room['members']:
            schedule_room_delete(room_id, socketio)

    # ── admin:freeze ──────────────────────────────────────────────────────────

    @socketio.on('admin:freeze')
    def handle_freeze(data):
        """Freeze or unfreeze a room. Room admin only."""
        if not isinstance(data, dict):
            return
        sid = current_sid()
        if not sid:
            return

        room_id = str(data.get('room_id', ''))
        freeze  = bool(data.get('freeze', True))

        if not is_room_admin(sid, room_id):
            emit('error', {'message': 'Not authorised.'})
            return

        room = get_room(room_id)
        if not room:
            return

        room['is_frozen'] = freeze
        status = 'frozen' if freeze else 'unfrozen'
        emit('room:frozen', {'room_id': room_id, 'is_frozen': freeze}, to=room_id)
        emit('system_message',
             system_msg(f'Room has been {status} by an admin.'),
             to=room_id)

    # ── admin:mod ─────────────────────────────────────────────────────────────

    @socketio.on('admin:mod')
    def handle_mod(data):
        """Grant or revoke mod (admin) status. Room creator only."""
        if not isinstance(data, dict):
            return
        sid  = current_sid()
        user = current_user()
        if not sid or not user:
            return

        room_id     = str(data.get('room_id', ''))
        target_disp = str(data.get('target', ''))
        grant       = bool(data.get('grant', True))

        room = get_room(room_id)
        if not room or room['creator_sid'] != sid:
            emit('error', {'message': 'Only the room creator can manage mods.'})
            return

        target_sid = sid_map.get(target_disp)
        if not target_sid:
            emit('error', {'message': 'User not found.'})
            return

        if grant:
            room['admins'].add(target_sid)
        else:
            room['admins'].discard(target_sid)

        action = 'granted mod' if grant else 'removed mod'
        emit('system_message',
             system_msg(f'{target_disp} was {action} by {user["display"]}.'),
             to=room_id)
        emit('room:members', room_member_list(room_id), to=room_id)

    # ── vote_hide ─────────────────────────────────────────────────────────────

    @socketio.on('vote_hide')
    def handle_vote_hide(data):
        if not isinstance(data, dict):
            return
        user = current_user()
        sid  = current_sid()
        if not user or not sid:
            return

        msg_id = str(data.get('msg_id', ''))[:32]
        if not msg_id:
            return

        # Use sid (not uid) as the voter identity — uid can be spoofed by the client
        voters = message_votes.setdefault(msg_id, set())
        voters.add(sid)

        if len(voters) >= HIDE_VOTE_THRESHOLD:
            emit('hide_message', {'msg_id': msg_id}, broadcast=True)
            message_votes.pop(msg_id, None)
        else:
            emit('vote_count', {
                'msg_id': msg_id,
                'votes':  len(voters),
                'needed': HIDE_VOTE_THRESHOLD,
            })

    # ── WebRTC signalling ─────────────────────────────────────────────────────

    @socketio.on('webrtc_signal')
    def handle_webrtc_signal(data):
        if not isinstance(data, dict):
            return
        try:
            if len(json.dumps(data).encode()) > MAX_SIGNAL_BYTES:
                return
        except (TypeError, ValueError):
            return

        user = current_user()
        if not user:
            return

        target = str(data.get('to', ''))
        if target in sid_map:
            data['from'] = user['display']
            emit('webrtc_signal', data, to=sid_map[target])
        else:
            emit('webrtc_signal', {
                'type':  'error',
                'error': f'User "{target}" is not connected',
            })

    # ── Legacy call events ────────────────────────────────────────────────────

    _CALL_EVENT_MAP = {
        'call-user':       'incoming-call',
        'video-call-user': 'incoming-call',
        'call-accepted':   'call-started',
        'call-rejected':   'call-ended',
        'end-call':        'call-ended',
    }

    def _make_call_handler(outgoing_event: str):
        def handler(data=None):
            target = data.get('to') if isinstance(data, dict) else None
            relay_to_target(outgoing_event, {}, target)
        return handler

    for _in, _out in _CALL_EVENT_MAP.items():
        socketio.on(_in)(_make_call_handler(_out))

    # ── disconnect ────────────────────────────────────────────────────────────

    @socketio.on('disconnect')
    def handle_disconnect():
        sid = current_sid()
        if not sid:
            return

        user = users.pop(sid, None)
        if not user:
            return

        display = user['display']
        uid     = user.get('uid', '')
        try:
            sid_map.pop(display, None)
            public_keys.pop(display, None)
            spam_tracker.pop(sid, None)
            upload_counts.pop(sid, None)

            # Clean up uid_sessions only if this sid is still the active one
            if uid and uid_sessions.get(uid) == sid:
                uid_sessions.pop(uid, None)

            # Clean up IP tracking
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr or '').split(',')[0].strip()
            if client_ip in ip_connections:
                ip_connections[client_ip].discard(sid)
                if not ip_connections[client_ip]:
                    del ip_connections[client_ip]

            # Capture room_id BEFORE popping user_state so _leave_current_room_by_sid
            # can still find it (user_state is the source of truth for room_id here)
            _leave_current_room_by_sid(sid, display)
        finally:
            user_state.pop(sid, None)
            emit('user_list', get_user_list(), broadcast=True)
            emit('system_message', system_msg(f'{display} left'), broadcast=True)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _do_join_room(sid: str, user: dict, room: dict) -> None:
        """Shared join logic used by both room:join and room:join_private."""
        room_id = room['id']

        # Leave current room first
        _leave_current_room(sid, user)

        room['members'].add(sid)
        cancel_room_delete(room_id)
        join_room(room_id)
        users[sid]['room_id'] = room_id
        if sid in user_state:
            user_state[sid]['room_id'] = room_id

        history = filter_expired(room['messages'], room['ttl'])
        emit('room:joined', {
            'room_id':    room_id,
            'name':       room['name'],
            'visibility': room['visibility'],
            'ttl':        room['ttl'],
            'history':    history,
            'members':    room_member_list(room_id),
            'is_admin':   sid in room['admins'],
            'is_frozen':  room['is_frozen'],
            'session_key': room.get('session_key'),   # None if creator hasn't sent it yet
        })

        emit('system_message',
             system_msg(f'{user["display"]} joined room {room["name"]}'),
             to=room_id)
        emit('room:members', room_member_list(room_id), to=room_id)

    def _leave_current_room(sid: str, user: dict) -> None:
        """Remove sid from their current room, schedule delete if empty."""
        room_id = user.get('room_id')
        if not room_id:
            return
        _leave_room_by_id(sid, room_id, user['display'])
        user['room_id'] = None
        if sid in user_state:
            user_state[sid]['room_id'] = None

    def _leave_current_room_by_sid(sid: str, display: str) -> None:
        """Used during disconnect when user record is already popped."""
        us = user_state.get(sid, {})
        room_id = us.get('room_id')
        if room_id:
            _leave_room_by_id(sid, room_id, display)

    def _leave_room_by_id(sid: str, room_id: str, display: str) -> None:
        room = get_room(room_id)
        if not room:
            return
        room['members'].discard(sid)
        leave_room(room_id)
        emit('system_message',
             system_msg(f'{display} left the room.'),
             to=room_id)
        emit('room:members', room_member_list(room_id), to=room_id)
        if not room['members']:
            schedule_room_delete(room_id, socketio)

    def _public_room_list() -> list:
        """
        Return only PUBLIC rooms.
        Private rooms are never listed — users must know the room_id to join.
        """
        return [
            {
                'room_id':   r['id'],
                'name':      r['name'],
                'members':   len(r['members']),
                'ttl':       r['ttl'],
                'is_frozen': r['is_frozen'],
                # 'locked' is always False for public rooms (no password)
                # but we include it for forward-compatibility
                'locked':    False,
            }
            for r in rooms.values()
            if r['visibility'] == 'public'
        ]
