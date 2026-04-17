"""
tests/test_rooms.py — Integration tests for room management, message
edit/delete/seen, reconnect_sync, and the active_sessions registry.

Covers the events that were missing from the original test suite:
  room:create, room:join, room:leave, room:join_private
  admin:kick, admin:freeze, admin:mod
  message:edit, message:delete, message:seen
  reconnect_sync / sync_reply
  active_sessions registry consistency
  upload rate limiting (check_upload_rate)
"""
import pytest
from flask_socketio import SocketIO

import state
from server import app, socketio


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_state():
    """Wipe all shared state before every test."""
    state.users.clear()
    state.sid_map.clear()
    state.public_keys.clear()
    state.message_history.clear()
    state.private_history.clear()
    state.uid_tags.clear()
    state.uid_sessions.clear()
    state.ip_connections.clear()
    state.upload_counts.clear()
    state.upload_rate.clear()
    state.message_votes.clear()
    state.spam_tracker.clear()
    state.user_state.clear()
    state.shadow_muted.clear()
    state.rooms.clear()
    state.active_sessions.clear()
    state.join_tokens.clear()
    state._color_index[0] = 0
    yield


@pytest.fixture()
def alice():
    app.config['TESTING'] = True
    c = socketio.test_client(app)
    c.emit('join', {'username': 'Alice', 'uid': 'uid-alice'})
    c.get_received()
    yield c
    if c.is_connected():
        c.disconnect()


@pytest.fixture()
def bob():
    app.config['TESTING'] = True
    c = socketio.test_client(app)
    c.emit('join', {'username': 'Bob', 'uid': 'uid-bob'})
    c.get_received()
    yield c
    if c.is_connected():
        c.disconnect()


def _events(client) -> dict:
    """Return received events as {name: last_payload}."""
    received = client.get_received()
    result = {}
    for e in received:
        result[e['name']] = e['args'][0] if e['args'] else {}
    return result


# ── active_sessions registry ──────────────────────────────────────────────────

class TestActiveSessionsRegistry:
    def test_session_registered_on_join(self, alice):
        assert len(state.active_sessions) == 1
        sess = list(state.active_sessions.values())[0]
        assert sess['uid'] == 'uid-alice'
        assert sess['status'] == 'connected'

    def test_session_removed_on_disconnect(self, alice):
        alice.disconnect()
        assert len(state.active_sessions) == 0

    def test_session_room_id_is_none_before_joining_room(self, alice):
        sess = list(state.active_sessions.values())[0]
        assert sess['room_id'] is None

    def test_session_room_id_updated_on_room_join(self, alice):
        alice.emit('room:create', {'name': 'TestRoom', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        sess = list(state.active_sessions.values())[0]
        assert sess['room_id'] == room_id

    def test_session_room_id_cleared_on_room_leave(self, alice):
        alice.emit('room:create', {'name': 'TestRoom', 'visibility': 'public'})
        _events(alice)
        alice.emit('room:leave', {})
        _events(alice)

        sess = list(state.active_sessions.values())[0]
        assert sess['room_id'] is None

    def test_two_sessions_tracked_independently(self, alice, bob):
        assert len(state.active_sessions) == 2
        uids = {s['uid'] for s in state.active_sessions.values()}
        assert uids == {'uid-alice', 'uid-bob'}


# ── room:create ───────────────────────────────────────────────────────────────

class TestRoomCreate:
    def test_creates_public_room(self, alice):
        alice.emit('room:create', {'name': 'General', 'visibility': 'public'})
        events = _events(alice)
        assert 'room:created' in events
        assert events['room:created']['name'] == 'General'
        assert events['room:created']['visibility'] == 'public'
        assert events['room:created']['is_admin'] is True

    def test_room_appears_in_room_list(self, alice):
        alice.emit('room:create', {'name': 'Lobby', 'visibility': 'public'})
        _events(alice)
        alice.emit('room:list', {})
        events = _events(alice)
        names = [r['name'] for r in events['room:list']]
        assert 'Lobby' in names

    def test_private_room_not_in_public_list(self, alice):
        alice.emit('room:create', {'name': 'Secret', 'visibility': 'private'})
        _events(alice)
        alice.emit('room:list', {})
        events = _events(alice)
        names = [r['name'] for r in events['room:list']]
        assert 'Secret' not in names

    def test_invalid_room_name_returns_error(self, alice):
        alice.emit('room:create', {'name': '', 'visibility': 'public'})
        events = _events(alice)
        assert 'error' in events

    def test_room_stored_in_state(self, alice):
        alice.emit('room:create', {'name': 'MyRoom', 'visibility': 'public'})
        _events(alice)
        assert len(state.rooms) == 1

    def test_creator_is_member(self, alice):
        alice.emit('room:create', {'name': 'MyRoom', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']
        room = state.rooms[room_id]
        alice_sid = list(state.active_sessions.keys())[0]
        assert alice_sid in room['members']

    def test_public_room_has_no_password(self, alice):
        alice.emit('room:create', {
            'name': 'Open', 'visibility': 'public', 'password': 'secret'
        })
        events = _events(alice)
        room_id = events['room:created']['room_id']
        assert state.rooms[room_id]['password'] is None


# ── room:join ─────────────────────────────────────────────────────────────────

class TestRoomJoin:
    def test_join_public_room(self, alice, bob):
        alice.emit('room:create', {'name': 'Lobby', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join', {'room_id': room_id})
        events = _events(bob)
        assert 'room:joined' in events
        assert events['room:joined']['room_id'] == room_id

    def test_join_nonexistent_room_returns_error(self, alice):
        alice.emit('room:join', {'room_id': 'DEADBEEF'})
        events = _events(alice)
        assert 'error' in events

    def test_join_private_room_via_public_join_returns_error(self, alice, bob):
        alice.emit('room:create', {'name': 'Private', 'visibility': 'private'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join', {'room_id': room_id})
        events = _events(bob)
        assert 'error' in events

    def test_join_private_room_with_correct_password(self, alice, bob):
        alice.emit('room:create', {
            'name': 'VIP', 'visibility': 'private', 'password': 'pass123'
        })
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join_private', {'room_id': room_id, 'password': 'pass123'})
        events = _events(bob)
        assert 'room:joined' in events

    def test_join_private_room_with_wrong_password_returns_error(self, alice, bob):
        alice.emit('room:create', {
            'name': 'VIP', 'visibility': 'private', 'password': 'pass123'
        })
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join_private', {'room_id': room_id, 'password': 'wrong'})
        events = _events(bob)
        assert 'error' in events

    def test_room_history_sent_on_join(self, alice, bob):
        alice.emit('room:create', {'name': 'Chat', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        alice.emit('send_message', {'to': room_id, 'text': 'hello room'})
        _events(alice)

        bob.emit('room:join', {'room_id': room_id})
        events = _events(bob)
        history = events['room:joined']['history']
        assert any(m.get('text') == 'hello room' for m in history)


# ── room:leave ────────────────────────────────────────────────────────────────

class TestRoomLeave:
    def test_leave_room(self, alice):
        alice.emit('room:create', {'name': 'Temp', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        alice.emit('room:leave', {})
        events = _events(alice)
        assert 'room:left' in events

        alice_sid = list(state.active_sessions.keys())[0]
        assert alice_sid not in state.rooms.get(room_id, {}).get('members', set())

    def test_leave_clears_room_id_in_registry(self, alice):
        alice.emit('room:create', {'name': 'Temp', 'visibility': 'public'})
        _events(alice)
        alice.emit('room:leave', {})
        _events(alice)

        sess = list(state.active_sessions.values())[0]
        assert sess['room_id'] is None


# ── admin:kick ────────────────────────────────────────────────────────────────

class TestAdminKick:
    def test_admin_can_kick_member(self, alice, bob):
        alice.emit('room:create', {'name': 'Room', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join', {'room_id': room_id})
        _events(bob)

        bob_display = list(state.users.values())[1]['display']
        alice.emit('admin:kick', {'room_id': room_id, 'target': bob_display})
        _events(alice)

        bob_sid = state.sid_map.get(bob_display)
        if bob_sid:
            assert bob_sid not in state.rooms[room_id]['members']

    def test_non_admin_cannot_kick(self, alice, bob):
        alice.emit('room:create', {'name': 'Room', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join', {'room_id': room_id})
        _events(bob)

        alice_display = list(state.users.values())[0]['display']
        bob.emit('admin:kick', {'room_id': room_id, 'target': alice_display})
        events = _events(bob)
        assert 'error' in events


# ── admin:freeze ──────────────────────────────────────────────────────────────

class TestAdminFreeze:
    def test_admin_can_freeze_room(self, alice):
        alice.emit('room:create', {'name': 'Room', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        alice.emit('admin:freeze', {'room_id': room_id, 'freeze': True})
        _events(alice)

        assert state.rooms[room_id]['is_frozen'] is True

    def test_frozen_room_rejects_messages(self, alice):
        alice.emit('room:create', {'name': 'Room', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        alice.emit('admin:freeze', {'room_id': room_id, 'freeze': True})
        _events(alice)

        alice.emit('send_message', {'to': room_id, 'text': 'blocked'})
        events = _events(alice)
        assert 'error' in events
        assert 'new_message' not in events

    def test_admin_can_unfreeze_room(self, alice):
        alice.emit('room:create', {'name': 'Room', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        alice.emit('admin:freeze', {'room_id': room_id, 'freeze': True})
        _events(alice)
        alice.emit('admin:freeze', {'room_id': room_id, 'freeze': False})
        _events(alice)

        assert state.rooms[room_id]['is_frozen'] is False


# ── admin:mod ─────────────────────────────────────────────────────────────────

class TestAdminMod:
    def test_creator_can_grant_mod(self, alice, bob):
        alice.emit('room:create', {'name': 'Room', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join', {'room_id': room_id})
        _events(bob)

        bob_display = list(state.users.values())[1]['display']
        alice.emit('admin:mod', {
            'room_id': room_id, 'target': bob_display, 'grant': True
        })
        _events(alice)

        bob_sid = state.sid_map.get(bob_display)
        if bob_sid:
            assert bob_sid in state.rooms[room_id]['admins']

    def test_non_creator_cannot_grant_mod(self, alice, bob):
        alice.emit('room:create', {'name': 'Room', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        bob.emit('room:join', {'room_id': room_id})
        _events(bob)

        alice_display = list(state.users.values())[0]['display']
        bob.emit('admin:mod', {
            'room_id': room_id, 'target': alice_display, 'grant': True
        })
        events = _events(bob)
        assert 'error' in events


# ── message:edit ──────────────────────────────────────────────────────────────

class TestMessageEdit:
    def test_sender_can_edit_global_message(self, alice):
        alice.emit('send_message', {'to': 'global', 'text': 'original'})
        events = _events(alice)
        msg_id = events['new_message']['msg_id']
        alice_display = events['new_message']['from']

        alice.emit('message:edit', {
            'msg_id': msg_id,
            'text': 'edited',
            'to': 'global',
            'from': alice_display,
        })
        events = _events(alice)
        assert 'message:edited' in events
        assert events['message:edited']['text'] == 'edited'
        assert events['message:edited']['edited'] is True

    def test_non_sender_cannot_edit(self, alice, bob):
        alice.emit('send_message', {'to': 'global', 'text': 'original'})
        events = _events(alice)
        msg_id = events['new_message']['msg_id']
        alice_display = events['new_message']['from']

        # Bob tries to edit Alice's message
        bob.emit('message:edit', {
            'msg_id': msg_id,
            'text': 'hacked',
            'to': 'global',
            'from': alice_display,   # spoofed sender
        })
        events = _events(bob)
        assert 'error' in events

    def test_missing_fields_ignored(self, alice):
        alice.emit('message:edit', {'msg_id': '', 'text': '', 'to': ''})
        events = _events(alice)
        assert 'message:edited' not in events


# ── message:delete ────────────────────────────────────────────────────────────

class TestMessageDelete:
    def test_sender_can_delete_global_message(self, alice):
        alice.emit('send_message', {'to': 'global', 'text': 'bye'})
        events = _events(alice)
        msg_id = events['new_message']['msg_id']
        alice_display = events['new_message']['from']

        alice.emit('message:delete', {
            'msg_id': msg_id,
            'to': 'global',
            'from': alice_display,
        })
        events = _events(alice)
        assert 'message:deleted' in events
        assert events['message:deleted']['msg_id'] == msg_id

    def test_non_sender_cannot_delete(self, alice, bob):
        alice.emit('send_message', {'to': 'global', 'text': 'bye'})
        events = _events(alice)
        msg_id = events['new_message']['msg_id']
        alice_display = events['new_message']['from']

        bob.emit('message:delete', {
            'msg_id': msg_id,
            'to': 'global',
            'from': alice_display,
        })
        events = _events(bob)
        assert 'error' in events

    def test_missing_fields_ignored(self, alice):
        alice.emit('message:delete', {'msg_id': '', 'to': ''})
        events = _events(alice)
        assert 'message:deleted' not in events


# ── message:seen ──────────────────────────────────────────────────────────────

class TestMessageSeen:
    def test_seen_relayed_to_sender(self, alice, bob):
        alice.emit('send_message', {'to': 'global', 'text': 'hi'})
        events = _events(alice)
        msg_id = events['new_message']['msg_id']
        alice_display = events['new_message']['from']

        bob.emit('message:seen', {
            'msg_ids': [msg_id],
            'sender': alice_display,
        })
        # Alice should receive the seen notification
        events = _events(alice)
        assert 'message:seen' in events
        assert msg_id in events['message:seen']['msg_ids']

    def test_seen_for_unknown_sender_ignored(self, alice):
        alice.emit('message:seen', {
            'msg_ids': ['abc123'],
            'sender': 'nobody#XXXX',
        })
        events = _events(alice)
        # No error, no crash — just silently dropped
        assert 'error' not in events

    def test_non_dict_data_ignored(self, alice):
        alice.emit('message:seen', 'bad')
        events = _events(alice)
        assert 'error' not in events


# ── reconnect_sync ────────────────────────────────────────────────────────────

class TestReconnectSync:
    def test_sync_reply_sent_on_reconnect_sync(self, alice):
        alice.emit('reconnect_sync', {})
        events = _events(alice)
        assert 'sync_reply' in events

    def test_sync_reply_contains_required_fields(self, alice):
        alice.emit('reconnect_sync', {})
        events = _events(alice)
        reply = events['sync_reply']
        assert 'missed' in reply
        assert 'current_seq' in reply
        assert 'room_id' in reply

    def test_sync_returns_missed_global_messages(self, alice, bob):
        # Alice sends a message
        alice.emit('send_message', {'to': 'global', 'text': 'msg1'})
        events = _events(alice)
        msg_id = events['new_message']['msg_id']

        # Bob reconnects and doesn't know about msg1
        bob.emit('reconnect_sync', {
            'known_ids': [],
        })
        events = _events(bob)
        missed_ids = [m.get('msg_id') for m in events['sync_reply']['missed']]
        assert msg_id in missed_ids

    def test_sync_skips_already_known_messages(self, alice, bob):
        alice.emit('send_message', {'to': 'global', 'text': 'known'})
        events = _events(alice)
        msg_id = events['new_message']['msg_id']

        # Bob already knows about this message
        bob.emit('reconnect_sync', {'known_ids': [msg_id]})
        events = _events(bob)
        missed_ids = [m.get('msg_id') for m in events['sync_reply']['missed']]
        assert msg_id not in missed_ids

    def test_room_sync_returns_missed_by_seq(self, alice, bob):
        alice.emit('room:create', {'name': 'SyncRoom', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        alice.emit('send_message', {'to': room_id, 'text': 'seq1'})
        _events(alice)
        alice.emit('send_message', {'to': room_id, 'text': 'seq2'})
        _events(alice)

        # Bob syncs with last_seq=0 (missed both messages)
        bob.emit('reconnect_sync', {'room_id': room_id, 'last_seq': 0})
        events = _events(bob)
        reply = events['sync_reply']
        assert reply['room_id'] == room_id
        assert len(reply['missed']) == 2

    def test_room_sync_with_current_seq_returns_empty(self, alice):
        alice.emit('room:create', {'name': 'SyncRoom', 'visibility': 'public'})
        events = _events(alice)
        room_id = events['room:created']['room_id']

        alice.emit('send_message', {'to': room_id, 'text': 'msg'})
        _events(alice)

        current_seq = state.rooms[room_id]['seq']
        alice.emit('reconnect_sync', {'room_id': room_id, 'last_seq': current_seq})
        events = _events(alice)
        assert events['sync_reply']['missed'] == []

    def test_non_dict_data_ignored(self, alice):
        alice.emit('reconnect_sync', 'bad')
        events = _events(alice)
        assert 'sync_reply' not in events


# ── upload rate limiting ──────────────────────────────────────────────────────

class TestUploadRateLimiting:
    def test_ok_on_first_upload(self):
        result = state.check_upload_rate('192.168.1.1')
        assert result == 'ok'

    def test_burst_limit_triggers(self):
        ip = '10.0.0.1'
        for _ in range(state.UPLOAD_BURST_LIMIT):
            state.check_upload_rate(ip)
        result = state.check_upload_rate(ip)
        assert result == 'burst'

    def test_daily_limit_triggers(self):
        ip = '10.0.0.2'
        entry = state.upload_rate.setdefault(ip, {
            'timestamps':  __import__('collections').deque(),
            'daily_count': state.UPLOAD_DAILY_LIMIT,
            'day':         int(__import__('time').time() // 86400),
        })
        result = state.check_upload_rate(ip)
        assert result == 'daily'

    def test_daily_counter_resets_on_new_day(self):
        ip = '10.0.0.3'
        import collections, time as _time
        yesterday = int(_time.time() // 86400) - 1
        state.upload_rate[ip] = {
            'timestamps':  collections.deque(),
            'daily_count': state.UPLOAD_DAILY_LIMIT,
            'day':         yesterday,
        }
        result = state.check_upload_rate(ip)
        assert result == 'ok'

    def test_different_ips_tracked_independently(self):
        ip_a = '172.16.0.1'
        ip_b = '172.16.0.2'
        for _ in range(state.UPLOAD_BURST_LIMIT):
            state.check_upload_rate(ip_a)
        # ip_a is burst-limited, ip_b should still be ok
        assert state.check_upload_rate(ip_b) == 'ok'


# ── room:join_with_token ──────────────────────────────────────────────────────

class TestJoinWithToken:
    def test_invalid_token_returns_error(self, alice):
        alice.emit('room:join_with_token', {'token': 'badtoken'})
        events = _events(alice)
        assert 'error' in events

    def test_expired_token_returns_error(self, alice):
        import time
        state.join_tokens['expiredtok'] = {
            'room_id': 'ROOM1',
            'sid':     list(state.active_sessions.keys())[0],
            'expires': time.time() - 1,  # already expired
        }
        alice.emit('room:join_with_token', {'token': 'expiredtok'})
        events = _events(alice)
        assert 'error' in events

    def test_token_for_different_sid_returns_error(self, alice):
        import time
        alice_sid = list(state.active_sessions.keys())[0]
        state.join_tokens['wrongsidtok'] = {
            'room_id': 'ROOM1',
            'sid':     'some-other-sid',
            'expires': time.time() + 300,
        }
        alice.emit('room:join_with_token', {'token': 'wrongsidtok'})
        events = _events(alice)
        assert 'error' in events


# ── event schema contract ─────────────────────────────────────────────────────

class TestEventSchema:
    def test_all_known_events_registered(self):
        import events as ev
        known = {s.name for s in ev.all_events()}
        # Spot-check a representative set
        required = {
            'join', 'joined', 'disconnect',
            'send_message', 'new_message',
            'message:edit', 'message:edited',
            'message:delete', 'message:deleted',
            'message:seen',
            'room:create', 'room:created',
            'room:join', 'room:joined', 'room:leave', 'room:left',
            'room:join_with_token',
            'admin:kick', 'admin:freeze', 'admin:mod',
            'reconnect_sync', 'sync_reply',
            'error',
        }
        missing = required - known
        assert not missing, f'Missing from event registry: {missing}'

    def test_validate_payload_catches_missing_field(self):
        import events as ev
        errors = ev.validate_payload('join', {})
        assert any('username' in e for e in errors)

    def test_validate_payload_accepts_valid_payload(self):
        import events as ev
        errors = ev.validate_payload('join', {'username': 'Alice'})
        assert errors == []

    def test_validate_payload_unknown_event(self):
        import events as ev
        errors = ev.validate_payload('nonexistent:event', {})
        assert errors

    def test_validate_payload_non_dict_returns_error(self):
        import events as ev
        errors = ev.validate_payload('join', 'not-a-dict')
        assert errors
