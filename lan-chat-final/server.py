"""
server.py — Entry point for LAN Chat.

Wires together the Flask app, Socket.IO, and all route modules,
then starts the development server when run directly.

Project layout
--------------
server.py          ← this file (entry point)
config.py          ← constants and environment-variable bindings
state.py           ← shared in-memory state + pure helper functions
routes/
  __init__.py      ← register_routes() wires everything to the app
  http.py          ← Flask HTTP routes  (/, /upload, /uploads, /ice-config)
  sockets.py       ← Socket.IO event handlers
"""
import os
import socket
import logging
from flask import Flask, jsonify
from flask_socketio import SocketIO

from config import (
    SECRET_KEY,
    MAX_HTTP_BUFFER_SIZE,
    MAX_UPLOAD_BYTES,
    PING_TIMEOUT,
    PING_INTERVAL,
)
from routes import register_routes

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('FLASK_DEBUG', '0') == '1' else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('lan-chat')

# ── Debug flag ────────────────────────────────────────────────────────────────
# Debug mode enables the Werkzeug interactive debugger, which exposes a
# Python REPL on the network. Keep it off unless you are actively developing
# on a trusted machine.
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

# ── Create app and Socket.IO instance ────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']        = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES  # Flask rejects oversized bodies early

socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    max_http_buffer_size=MAX_HTTP_BUFFER_SIZE,
    ping_timeout=PING_TIMEOUT,
    ping_interval=PING_INTERVAL,
    engineio_logger=False,
)

# ── Register all HTTP routes and Socket.IO handlers ───────────────────────────
register_routes(app, socketio)

# ── Start background cleanup worker ──────────────────────────────────────────
from state import start_cleanup_worker
start_cleanup_worker()


# ── ngrok browser-warning bypass ─────────────────────────────────────────────
# ngrok shows a warning page to first-time visitors unless this header is
# present. Adding it to every response skips that page automatically.

@app.after_request
def add_ngrok_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(413)
def request_entity_too_large(e):
    """Return JSON instead of the default HTML page for oversized uploads."""
    log.warning('Upload rejected: request body too large')
    return jsonify({'error': 'File too large'}), 413


@app.errorhandler(404)
def not_found(e):
    """Return JSON for 404s on API paths; let Flask handle page 404s."""
    log.debug('404: %s', e)
    return jsonify({'error': 'Not found'}), 404


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_local_ip() -> str:
    """Return the machine's LAN IP address, falling back to 127.0.0.1."""
    try:
        # Connect to an external address (no data sent) to discover the
        # outbound interface the OS would use for LAN traffic.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except OSError:
        return '127.0.0.1'


# ── Dev-server entry point ────────────────────────────────────────────────────
if __name__ == '__main__':
    local_ip = _get_local_ip()
    bar = '=' * 50

    print(f'\n{bar}')
    print('  LAN CHAT — Starting server...')
    print(bar)
    print(f'\n  Local:   http://127.0.0.1:5000')
    print(f'  Network: http://{local_ip}:5000')
    print(f'\n  Share the Network URL with others on your WiFi.')
    print(f'\n  NOTE: LAN traffic is plain HTTP.')
    print(f'        Private messages are E2E encrypted in the browser.')
    print(f'        Use the ngrok HTTPS URL for full transport encryption.')
    print(f'{bar}\n')

    socketio.run(app, host='0.0.0.0', port=5000, debug=DEBUG)
