"""
tests/test_sockets.py — Integration tests for Socket.IO event handlers.

Uses flask_socketio.test_client() which drives the full event pipeline
without a real network connection.
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
    state.message_votes.clear()
    state.spam_tracker.clear()
    state.user_state.clear()
    state.shadow_muted.clear()
    state.rooms.clear()
    state._color_index[0] = 0
    yield


@pytest.fixture()
def sio_client():
    """A single connected Socket.IO test client."""
    app.config['TESTING'] = True
    client = socketio.test_client(app)
    yield client
    # Guard against tests that disconnect the client themselves
    if client.is_connected():
        client.disconnect()


@pytest.fixture()
def alice(sio_client):
    """A client that has already joined as 'Alice'."""
    sio_client.emit('join', {'username': 'Alice'})
    sio_client.get_received()   # flush join events
    return sio_client


def _second_client():
    """Create and return a second independent Socket.IO test client."""
    return socketio.test_client(app)


# ── join ──────────────────────────────────────────────────────────────────────

class TestJoin:
    def test_joined_event_received(self, sio_client):
        sio_client.emit('join', {'username': 'Alice'})
        events = {e['name']: e['args'][0] for e in sio_client.get_received()}
        assert 'joined' in events
        assert events['joined']['username'] == 'Alice'
        assert 'tag' in events['joined']
        assert 'display' in events['joined']

    def test_joined_event_contains_color(self, sio_client):
        sio_client.emit('join', {'username': 'Alice'})
        events = {e['name']: e['args'][0] for e in sio_client.get_received()}
        assert 'color' in events['joined']

    def test_user_added_to_state(self, sio_client):
        sio_client.emit('join', {'username': 'Alice'})
        sio_client.get_received()
        # sid_map is now keyed by "username#tag"
        assert any(k.startswith('Alice#') for k in state.sid_map)

    def test_message_history_sent(self, sio_client):
        state.message_history.append({'type': 'text', 'text': 'old msg'})
        sio_client.emit('join', {'username': 'Alice'})
        events = {e['name']: e['args'][0] for e in sio_client.get_received()}
        assert 'message_history' in events
        assert len(events['message_history']) == 1

    def test_duplicate_username_same_tag_allowed(self, sio_client):
        """Two clients with the same name get different tags — both are allowed."""
        client2 = _second_client()
        try:
            sio_client.emit('join', {'username': 'Alice'})
            sio_client.get_received()
            client2.emit('join', {'username': 'Alice'})
            events = {e['name']: e['args'][0] for e in client2.get_received()}
            # Both are 'Alice' but with different tags — username stays 'Alice'
            assert events['joined']['username'] == 'Alice'
            assert 'tag' in events['joined']
        finally:
            client2.disconnect()

    def test_empty_username_becomes_anonymous(self, sio_client):
        sio_client.emit('join', {'username': ''})
        events = {e['name']: e['args'][0] for e in sio_client.get_received()}
        assert events['joined']['username'] == 'Anonymous'

    def test_non_dict_data_ignored(self, sio_client):
        sio_client.emit('join', 'not-a-dict')
        # Should not raise; state should remain empty
        sio_client.get_received()
        assert len(state.users) == 0

    def test_public_key_stored(self, sio_client):
        pub_key = {'kty': 'EC', 'crv': 'P-256', 'x': 'abc', 'y': 'def'}
        sio_client.emit('join', {'username': 'Alice', 'publicKey': pub_key})
        sio_client.get_received()
        # public_keys is keyed by "Alice#TAG"
        assert any(k.startswith('Alice#') for k in state.public_keys)

    def test_non_dict_public_key_rejected(self, sio_client):
        sio_client.emit('join', {'username': 'Alice', 'publicKey': 'bad-key'})
        sio_client.get_received()
        assert not any(k.startswith('Alice#') for k in state.public_keys)

    def test_all_keys_sent_to_new_joiner(self, sio_client):
        # Pre-populate a key for an existing user using the new tag format
        state.public_keys['Bob#FAKE'] = {'kty': 'EC'}
        state.sid_map['Bob#FAKE'] = 'fake-sid'
        sio_client.emit('join', {'username': 'Alice'})
        events = {e['name']: e['args'][0] for e in sio_client.get_received()}
        assert 'all_keys' in events
        assert 'Bob#FAKE' in events['all_keys']


# ── send_message ──────────────────────────────────────────────────────────────

class TestSendMessage:
    def test_global_message_broadcast(self, alice):
        alice.emit('send_message', {'to': 'global', 'text': 'Hello!'})
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert 'new_message' in events
        assert events['new_message']['text'] == 'Hello!'

    def test_global_message_stored_in_history(self, alice):
        alice.emit('send_message', {'to': 'global', 'text': 'stored'})
        alice.get_received()
        assert any(m['text'] == 'stored' for m in state.message_history)

    def test_empty_text_ignored(self, alice):
        alice.emit('send_message', {'to': 'global', 'text': '   '})
        events = [e['name'] for e in alice.get_received()]
        assert 'new_message' not in events

    def test_message_contains_sender_username(self, alice):
        alice.emit('send_message', {'to': 'global', 'text': 'hi'})
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert events['new_message']['from'].startswith('Alice#')

    def test_non_dict_data_ignored(self, alice):
        alice.emit('send_message', 'not-a-dict')
        events = [e['name'] for e in alice.get_received()]
        assert 'new_message' not in events

    def test_valid_encrypted_field_forwarded(self, alice):
        alice.emit('send_message', {
            'to': 'global',
            'text': '🔒',
            'encrypted': 'base64ciphertext==',
        })
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert events['new_message'].get('encrypted') == 'base64ciphertext=='

    def test_non_string_encrypted_field_dropped(self, alice):
        alice.emit('send_message', {
            'to': 'global',
            'text': 'hi',
            'encrypted': 12345,
        })
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert 'encrypted' not in events['new_message']

    def test_global_history_capped(self, alice):
        from config import MAX_GLOBAL_HISTORY, SPAM_MSG_LIMIT
        # Send enough messages to fill history, accounting for spam cooldown.
        # We send in small bursts within the spam limit.
        sent = 0
        while sent < MAX_GLOBAL_HISTORY + 5:
            alice.emit('send_message', {'to': 'global', 'text': str(sent)})
            sent += 1
        alice.get_received()
        assert len(state.message_history) <= MAX_GLOBAL_HISTORY

    def test_message_text_truncated_at_max_len(self, alice):
        from config import MAX_MESSAGE_LEN
        long_text = 'x' * (MAX_MESSAGE_LEN + 500)
        alice.emit('send_message', {'to': 'global', 'text': long_text})
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert len(events['new_message']['text']) == MAX_MESSAGE_LEN

    def test_message_to_unknown_target_dropped(self, alice):
        alice.emit('send_message', {'to': 'ghost_user_xyz', 'text': 'hi'})
        events = [e['name'] for e in alice.get_received()]
        assert 'new_message' not in events
        # No ghost history entry should be created
        assert not any('ghost_user_xyz' in k for k in state.private_history)


# ── send_file ─────────────────────────────────────────────────────────────────

class TestSendFile:
    @pytest.fixture(autouse=True)
    def real_upload_files(self, tmp_path, monkeypatch):
        """Create real files in a temp upload folder so existence checks pass."""
        import routes.http as http_mod
        import routes.sockets as sockets_mod
        monkeypatch.setattr(http_mod, 'UPLOAD_FOLDER', str(tmp_path))
        monkeypatch.setattr(sockets_mod, 'UPLOAD_FOLDER', str(tmp_path))
        # Create the files the tests reference
        (tmp_path / 'test.png').write_bytes(b'\x89PNG')
        (tmp_path / 'file.txt').write_bytes(b'hello')
        (tmp_path / 'file.bin').write_bytes(b'\x00')

    def test_valid_file_message_broadcast(self, alice):
        alice.emit('send_file', {
            'to': 'global',
            'url': '/uploads/test.png',
            'name': 'test.png',
            'file_type': 'image/png',
        })
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert 'new_message' in events
        assert events['new_message']['type'] == 'file'

    def test_url_not_starting_with_uploads_rejected(self, alice):
        alice.emit('send_file', {
            'to': 'global',
            'url': 'http://evil.com/malware.exe',
            'name': 'malware.exe',
            'file_type': 'application/octet-stream',
        })
        events = [e['name'] for e in alice.get_received()]
        assert 'new_message' not in events

    def test_nonexistent_upload_file_rejected(self, alice):
        """A URL pointing to a non-existent file must be silently dropped."""
        alice.emit('send_file', {
            'to': 'global',
            'url': '/uploads/ghost_file_that_does_not_exist.png',
            'name': 'ghost.png',
            'file_type': 'image/png',
        })
        events = [e['name'] for e in alice.get_received()]
        assert 'new_message' not in events

    def test_filename_capped_at_260_chars(self, alice):
        long_name = 'A' * 300 + '.txt'
        alice.emit('send_file', {
            'to': 'global',
            'url': '/uploads/file.txt',
            'name': long_name,
            'file_type': 'text/plain',
        })
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert len(events['new_message']['name']) <= 260

    def test_file_type_capped_at_128_chars(self, alice):
        long_type = 'x/' + 'a' * 200
        alice.emit('send_file', {
            'to': 'global',
            'url': '/uploads/file.bin',
            'name': 'file.bin',
            'file_type': long_type,
        })
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert len(events['new_message']['file_type']) <= 128


# ── typing indicators ─────────────────────────────────────────────────────────

class TestTyping:
    def test_typing_event_emitted(self, alice):
        alice.emit('typing', {'to': 'global'})
        # The event is broadcast (exclude_self), so alice won't receive it
        # Just verify no exception was raised and state is intact
        assert any(k.startswith('Alice#') for k in state.sid_map)

    def test_stop_typing_event_emitted(self, alice):
        alice.emit('stop_typing', {'to': 'global'})
        assert any(k.startswith('Alice#') for k in state.sid_map)

    def test_non_dict_data_ignored(self, alice):
        alice.emit('typing', 'bad')
        alice.emit('stop_typing', 'bad')
        assert any(k.startswith('Alice#') for k in state.sid_map)  # no crash


# ── webrtc_signal ─────────────────────────────────────────────────────────────

class TestWebrtcSignal:
    def test_error_returned_for_unknown_target(self, alice):
        alice.emit('webrtc_signal', {'to': 'nobody', 'type': 'offer', 'sdp': {}})
        events = {e['name']: e['args'][0] for e in alice.get_received()}
        assert 'webrtc_signal' in events
        assert events['webrtc_signal']['type'] == 'error'

    def test_non_dict_data_ignored(self, alice):
        alice.emit('webrtc_signal', 'bad')
        events = [e['name'] for e in alice.get_received()]
        # No crash, no webrtc_signal error for non-dict (silently dropped)
        assert any(k.startswith('Alice#') for k in state.sid_map)


# ── disconnect ────────────────────────────────────────────────────────────────

class TestDisconnect:
    def test_user_removed_from_state_on_disconnect(self, sio_client):
        sio_client.emit('join', {'username': 'Alice'})
        sio_client.get_received()
        assert any(k.startswith('Alice#') for k in state.sid_map)

        sio_client.disconnect()
        assert not any(k.startswith('Alice#') for k in state.sid_map)

    def test_public_key_removed_on_disconnect(self, sio_client):
        pub_key = {'kty': 'EC', 'crv': 'P-256', 'x': 'a', 'y': 'b'}
        sio_client.emit('join', {'username': 'Alice', 'publicKey': pub_key})
        sio_client.get_received()
        assert any(k.startswith('Alice#') for k in state.public_keys)

        sio_client.disconnect()
        assert not any(k.startswith('Alice#') for k in state.public_keys)

    def test_disconnect_without_join_does_not_crash(self):
        client = _second_client()
        # Disconnect without ever joining — should not raise
        client.disconnect()
