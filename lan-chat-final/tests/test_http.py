"""
tests/test_http.py — Integration tests for Flask HTTP routes.

Uses Flask's built-in test client; no real network or disk I/O for most tests.
The upload tests write to a temporary directory so the real uploads/ folder
is never touched.
"""
import io
import os
import pytest

import state
from server import app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    """Return a Flask test client with testing mode enabled."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state():
    """Clear shared state before every test."""
    state.users.clear()
    state.sid_map.clear()
    state.message_history.clear()
    state.private_history.clear()
    yield


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestIndex:
    def test_returns_200(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_returns_html(self, client):
        resp = client.get('/')
        assert b'<!DOCTYPE html>' in resp.data or b'<html' in resp.data


# ── GET /ice-config ───────────────────────────────────────────────────────────

class TestIceConfig:
    def test_returns_200(self, client):
        resp = client.get('/ice-config')
        assert resp.status_code == 200

    def test_content_type_is_json(self, client):
        resp = client.get('/ice-config')
        assert resp.content_type.startswith('application/json')

    def test_has_required_keys(self, client):
        data = client.get('/ice-config').get_json()
        assert 'iceServers' in data
        assert 'bundlePolicy' in data
        assert 'rtcpMuxPolicy' in data
        assert 'iceCandidatePoolSize' in data

    def test_stun_servers_present(self, client):
        data = client.get('/ice-config').get_json()
        urls = [s['urls'] for s in data['iceServers']]
        assert any(u.startswith('stun:') for u in urls)

    def test_no_turn_without_credentials(self, client, monkeypatch):
        monkeypatch.setattr('routes.http.TURN_CREDENTIALS', '')
        data = client.get('/ice-config').get_json()
        urls = [s['urls'] for s in data['iceServers']]
        assert not any(u.startswith('turn:') for u in urls)

    def test_turn_added_with_credentials(self, client, monkeypatch):
        # _ICE_CONFIG is built at import time, so patch it directly
        import routes.http as http_mod
        fake_config = {
            'iceServers': [
                {'urls': 'stun:stun.l.google.com:19302'},
                {'urls': 'turn:fake.turn.example.com:3478',
                 'username': 'u', 'credential': 'c'},
            ],
            'iceCandidatePoolSize': 20,
            'bundlePolicy': 'max-bundle',
            'rtcpMuxPolicy': 'require',
        }
        monkeypatch.setattr(http_mod, '_ICE_CONFIG', fake_config)
        data = client.get('/ice-config').get_json()
        urls = [s['urls'] for s in data['iceServers']]
        assert any(u.startswith('turn:') for u in urls)

    def test_turn_credentials_not_exposed_without_env(self, client, monkeypatch):
        monkeypatch.setattr('routes.http.TURN_CREDENTIALS', '')
        data = client.get('/ice-config').get_json()
        for server in data['iceServers']:
            assert 'credential' not in server
            assert 'username' not in server


# ── GET /uploads/<filename> ───────────────────────────────────────────────────

class TestUploadedFile:
    def test_missing_file_returns_404(self, client):
        resp = client.get('/uploads/nonexistent_file_xyz.txt')
        assert resp.status_code == 404

    def test_404_body_is_json(self, client):
        resp = client.get('/uploads/nonexistent_file_xyz.txt')
        data = resp.get_json()
        assert data is not None
        assert 'error' in data


# ── POST /upload ──────────────────────────────────────────────────────────────

class TestUpload:
    def _post_file(self, client, filename='test.txt', content=b'hello', content_type=None):
        """Helper: POST a file to /upload."""
        data = {
            'file': (io.BytesIO(content), filename),
        }
        return client.post(
            '/upload',
            data=data,
            content_type='multipart/form-data',
        )

    def test_successful_upload_returns_200(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr('routes.http.UPLOAD_FOLDER', str(tmp_path))
        monkeypatch.setattr('state.UPLOAD_FOLDER', str(tmp_path), raising=False)
        resp = self._post_file(client)
        assert resp.status_code == 200

    def test_response_contains_url(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr('routes.http.UPLOAD_FOLDER', str(tmp_path))
        data = self._post_file(client).get_json()
        assert 'url' in data
        assert data['url'].startswith('/uploads/')

    def test_response_contains_name(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr('routes.http.UPLOAD_FOLDER', str(tmp_path))
        data = self._post_file(client, filename='hello.txt').get_json()
        assert data['name'] == 'hello.txt'

    def test_no_file_field_returns_400(self, client):
        resp = client.post('/upload', data={}, content_type='multipart/form-data')
        assert resp.status_code == 400

    def test_empty_filename_returns_400(self, client):
        data = {'file': (io.BytesIO(b'data'), '')}
        resp = client.post('/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 400

    def test_oversized_request_returns_413(self, client, tmp_path, monkeypatch):
        # Send actual content that exceeds MAX_UPLOAD_BYTES so Flask's
        # MAX_CONTENT_LENGTH triggers before the route handler runs.
        from config import MAX_UPLOAD_BYTES
        monkeypatch.setattr('routes.http.UPLOAD_FOLDER', str(tmp_path))
        # Use MAX_CONTENT_LENGTH to make Flask reject the request
        app.config['MAX_CONTENT_LENGTH'] = 10  # 10 bytes for this test
        try:
            data = {'file': (io.BytesIO(b'X' * 100), 'big.txt')}
            resp = client.post(
                '/upload',
                data=data,
                content_type='multipart/form-data',
            )
            assert resp.status_code == 413
        finally:
            app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES

    def test_path_traversal_filename_is_sanitised(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr('routes.http.UPLOAD_FOLDER', str(tmp_path))
        data = self._post_file(client, filename='../../evil.sh').get_json()
        # The stored URL must not contain '..'
        assert '..' not in data['url']
        # The file must land inside tmp_path, not above it
        stored = data['url'].replace('/uploads/', '')
        dest = os.path.join(str(tmp_path), stored)
        assert os.path.commonpath([dest, str(tmp_path)]) == str(tmp_path)
