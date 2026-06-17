# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
socket_manager.py — Socket.IO configuration and initialization.

This module sets up the Socket.IO server with V1 configuration including:
- Max HTTP buffer size
- Ping timeout and interval
- CORS settings
- Error handlers
- PID file handling
- Template integrity check
- ngrok browser-warning bypass
"""
import os
import sys
import socket
import logging
import atexit
import socketio

import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    MAX_HTTP_BUFFER_SIZE,
    PING_TIMEOUT,
    PING_INTERVAL,
    ALLOWED_ORIGINS,
    DEBUG as CONFIG_DEBUG,
)

# Force UTF-8 stdout so the GUI log panel renders correctly on Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# ── PID file — lets stop.bat kill the server without needing a password ───────
_PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.pid")

def _write_pid():
    try:
        with open(_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass

def _remove_pid():
    try:
        if os.path.exists(_PID_FILE):
            os.remove(_PID_FILE)
    except OSError:
        pass

_write_pid()
atexit.register(_remove_pid)


# ── Template integrity check ──────────────────────────────────────────────────
# Catches duplicate HTML element IDs before the server starts.
# Duplicate IDs break getElementById and silently kill JS event listeners.

def _check_template_integrity():
    import re
    from collections import Counter
    template = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'frontend', 'templates', 'index.html')
    if not os.path.isfile(template):
        return
    with open(template, encoding='utf-8', errors='replace') as f:
        content = f.read()
    ids = re.findall(r'id="([\w-]+)"', content)
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    if dupes:
        print('\n' + '!' * 60, file=sys.stderr)
        print('  STARTUP ABORTED — duplicate HTML element IDs detected:', file=sys.stderr)
        for d in sorted(dupes):
            print(f'    • #{d}', file=sys.stderr)
        print('  Fix index.html before starting the server.', file=sys.stderr)
        print('!' * 60 + '\n', file=sys.stderr)
        sys.exit(1)

_check_template_integrity()


# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('DEBUG', '0') == '1' else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('lan-chat')


# ── Create Socket.IO instance with V1 configuration ────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=ALLOWED_ORIGINS,
    max_http_buffer_size=MAX_HTTP_BUFFER_SIZE,
    ping_timeout=PING_TIMEOUT,
    ping_interval=PING_INTERVAL,
    engineio_logger=False,
)


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


# ── Startup logging ───────────────────────────────────────────────────────────
def log_startup_info(port: int = 5000):
    """Log server startup information."""
    from config import ADMIN_PASSWORD, PUBLIC_MODE
    local_ip = _get_local_ip()
    bar = '=' * 50

    log.info(f'{bar}')
    log.info('  LAN CHAT — Starting server...')
    log.info(bar)
    log.info(f'  Local:   http://127.0.0.1:{port}')
    log.info(f'  Network: http://{local_ip}:{port}')
    log.info(f'  Share the Network URL with others on your WiFi.')
    log.info(f'  Mode:        {"[PUBLIC MODE - ngrok/internet]" if PUBLIC_MODE else "[LAN MODE - local network]"}')
    log.info(f'  Admin mode:  {"ENABLED  (Ctrl+Shift+A on login screen)" if ADMIN_PASSWORD else "DISABLED  (set ADMIN_PASSWORD env var to enable)"}')
    log.info(f'  NOTE: Traffic over ngrok is HTTPS-encrypted.')
    log.info(f'        Messages are E2E encrypted in the browser.')
    log.info(f'        Use the ngrok HTTPS URL for full transport encryption.')

    # ── Unmissable security warnings ─────────────────────────────────────────
    warn_lines = []
    if not os.environ.get('SECRET_KEY'):
        warn_lines.append(
            '  ⚠  SECRET_KEY is not set — sessions will reset on each restart.'
        )
    if os.environ.get('DEBUG', '0') == '1':
        warn_lines.append(
            '  ⚠  DEBUG mode is ON — interactive debugger is exposed on the network.'
        )
    if warn_lines:
        log.warning(''.join(warn_lines))


# ── Create ASGI app (will be mounted in app.py) ───────────────────────────────
# This will be imported and used in app.py to create the full ASGI app
def create_socket_app(fastapi_app):
    """Create the Socket.IO ASGI app with the FastAPI app."""
    return socketio.ASGIApp(sio, fastapi_app)

# ── Module-level socket_app for uvicorn/run.bat compatibility ──────────────────
# This is a placeholder that will be replaced when app.py calls create_socket_app
# It's defined here to allow uvicorn to import socket_manager:socket_app
socket_app = None
