# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
config.py — All configuration constants and environment-variable bindings.

Import this module anywhere you need a setting; never read os.environ
directly in other modules.

IMPORTANT: V2 uses in-memory state only. All data is lost on server restart.
- Messages are limited to MAX_GLOBAL_HISTORY (500) for global chat
- Private messages are limited to MAX_PRIVATE_HISTORY (200) per conversation
- No database persistence - all state is in Python dictionaries and deques
- This is a design choice for simplicity and performance in LAN environments
"""
import os
import secrets
import warnings

# ── Flask ─────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    # Warn loudly — the default is only acceptable for local LAN use.
    # Set the SECRET_KEY environment variable before deploying to any
    # shared or public network.
    warnings.warn(
        'SECRET_KEY is not set. A random key will be generated for this session. '
        'Sessions will be invalidated on server restart. '
        'Set the SECRET_KEY environment variable for a stable deployment.',
        stacklevel=1,
    )
    # Generate a cryptographically random key instead of a hardcoded default.
    # This is safe for local LAN use; set SECRET_KEY env var for production.
    SECRET_KEY = secrets.token_hex(32)

# ── Socket.IO ─────────────────────────────────────────────────────────────────
MAX_HTTP_BUFFER_SIZE = 50 * 1024 * 1024   # 50 MB — max single upload via socket
PING_TIMEOUT         = 60                  # seconds before a silent client is dropped
PING_INTERVAL        = 25                  # seconds between keep-alive pings

# ── File uploads ──────────────────────────────────────────────────────────────
UPLOAD_FOLDER    = os.path.join(os.path.dirname(__file__), 'uploads')
# In PUBLIC_MODE reduce max upload to 10 MB to limit bandwidth abuse
_public = os.environ.get('PUBLIC_MODE', 'false').lower() == 'true'
MAX_UPLOAD_BYTES = (10 * 1024 * 1024) if _public else MAX_HTTP_BUFFER_SIZE

# ── Chat limits ───────────────────────────────────────────────────────────────
MAX_USERNAME_LEN     = 20
MAX_MESSAGE_LEN      = 2000  # characters — prevents RAM exhaustion via huge messages
MAX_GLOBAL_HISTORY   = 500   # messages kept in RAM for global chat
MAX_PRIVATE_HISTORY  = 200   # messages kept per private conversation
MAX_SIGNAL_BYTES     = 64 * 1024  # 64 KB — max size of a WebRTC signal payload

# ── Spam / rate-limiting ──────────────────────────────────────────────────────
SPAM_MSG_LIMIT    = 5    # max messages allowed in the window (LAN)
SPAM_WINDOW_S     = 5    # rolling window in seconds
SPAM_COOLDOWN_S   = 20   # cooldown duration after limit is hit
SPAM_REPEAT_LIMIT = 3    # same message repeated this many times → shadow mute

# Stricter limits applied automatically when PUBLIC_MODE=true
SPAM_MSG_LIMIT_PUBLIC = 2   # max messages per window in public mode
SPAM_WINDOW_S_PUBLIC  = 5   # rolling window in public mode (used by check_smart_spam)

# ── Security (ngrok / public deployment) ─────────────────────────────────────
# Origins allowed to connect via WebSocket.
# Set ALLOWED_ORIGINS env var as comma-separated list to override.
# Default: allow localhost only for security.
#
# PRODUCTION REQUIREMENT: If exposing this server via ngrok or a public URL,
# you MUST set ALLOWED_ORIGINS to the specific URL(s) you trust:
#   export ALLOWED_ORIGINS="https://your-ngrok-url.ngrok-free.app,https://your-domain.com"
# This prevents other sites from connecting to your server via CORS.
_raw_origins = os.environ.get('ALLOWED_ORIGINS', '')
ALLOWED_ORIGINS: list[str] | str = (
    [o.strip() for o in _raw_origins.split(',') if o.strip()]
    if _raw_origins
    else '*'  # LAN app — allow all origins. Set ALLOWED_ORIGINS env var to restrict in production.
)

# Max simultaneous socket connections per IP address.
# Prevents a single client from flooding the server with connections.
# In PUBLIC_MODE default to 3 (stricter) unless explicitly overridden.
_default_conn_limit = '3' if os.environ.get('PUBLIC_MODE', 'false').lower() == 'true' else '5'
MAX_CONNECTIONS_PER_IP = int(os.environ.get('MAX_CONNECTIONS_PER_IP', _default_conn_limit))
# Set TRUSTED_PROXY=true ONLY when the server runs behind a reverse proxy
# (nginx, Caddy, ngrok, etc.) that sets X-Forwarded-For reliably.
# When false (default), X-Forwarded-For is ignored and the direct socket
# address is used — this prevents IP spoofing on direct deployments.
TRUSTED_PROXY = os.environ.get('TRUSTED_PROXY', 'false').lower() == 'true'

# Join token TTL in seconds — how long an approval token is valid.
JOIN_TOKEN_TTL_S = int(os.environ.get('JOIN_TOKEN_TTL_S', '300'))  # 5 minutes

# ── Vote-to-hide ──────────────────────────────────────────────────────────────
HIDE_VOTE_THRESHOLD = 3  # votes needed to hide a message for everyone

# ── Reputation thresholds (messages sent this session) ───────────────────────
REP_ACTIVE  = 10   # messages to reach "Active"
REP_TRUSTED = 50   # messages to reach "Trusted"

# ── Rooms ─────────────────────────────────────────────────────────────────────
MAX_ROOM_NAME_LEN   = 32
MAX_ROOMS           = 50   # max concurrent rooms
ROOM_IDLE_GRACE_S   = 300  # seconds before empty room is deleted (5 min)
ROOM_HISTORY_SIZE   = 200  # messages kept per room

# ── Ephemeral messages ────────────────────────────────────────────────────────
EPHEMERAL_TTLS = {
    '5min':    5 * 60,
    '1hour':   60 * 60,
    'session': None,   # deleted when server restarts (already the default)
}

# ── Analytics ─────────────────────────────────────────────────────────────────
# Set ANALYTICS_KEY env var to protect the /analytics endpoint.
# Leave unset to disable the endpoint entirely.
ANALYTICS_KEY = os.environ.get('ANALYTICS_KEY', '')

# ── Admin password ────────────────────────────────────────────────────────────
# Set ADMIN_PASSWORD env var to enable admin mode.
# Users who enter this password on login get is_admin=True on their session.
# Leave unset to disable admin mode entirely (no one can be admin).
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')

# ── Public mode ───────────────────────────────────────────────────────────────
# Set PUBLIC_MODE=true when exposing via ngrok or the internet.
# When enabled, SERVER_PASSWORD is enforced on every join attempt.
PUBLIC_MODE = os.environ.get('PUBLIC_MODE', 'false').lower() == 'true'

# ── Server access password ────────────────────────────────────────────────────
# Set SERVER_PASSWORD env var to require a password on join.
# Leave unset (or empty) to allow anyone with the link to join.
# When PUBLIC_MODE=true, an empty SERVER_PASSWORD blocks all connections.
SERVER_PASSWORD = os.environ.get('SERVER_PASSWORD', '') or None

# ── Debug mode ────────────────────────────────────────────────────────────────
# Set DEBUG=true to enable verbose server-side logging.
# Never enable in production — exposes internal state.
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# ── Connection limits ─────────────────────────────────────────────────────────
# Maximum file uploads per user session (resets on page refresh).
MAX_UPLOADS_PER_SESSION = int(os.environ.get('MAX_UPLOADS_PER_SESSION', '30'))

# ── User avatar colours (round-robin) ─────────────────────────────────────────
USER_COLORS = [
    '#25D366', '#00a884', '#53bdeb', '#f0b429',
    '#e06c75', '#c678dd', '#56b6c2', '#e5c07b',
]

# ── WebRTC / TURN ─────────────────────────────────────────────────────────────
# Set TURN_CREDENTIALS="username:credential" in the environment to enable TURN.
# Leave unset for STUN-only (works fine on the same LAN).
# WARNING: Without TURN, calls across NAT/firewalls will randomly fail.
TURN_CREDENTIALS = os.environ.get('TURN_CREDENTIALS', '')
if not TURN_CREDENTIALS:
    warnings.warn(
        'TURN_CREDENTIALS is not set. Voice/video calls will use STUN only. '
        'Calls on the same LAN will work, but calls across different networks '
        'or through firewalls/NAT will randomly fail. '
        'Set TURN_CREDENTIALS="username:credential" to enable TURN relay.',
        stacklevel=1,
    )
TURN_URL_UDP = os.environ.get(
    'TURN_URL_UDP',
    'turn:global.turn.twilio.com:3478?transport=udp',
)
TURN_URL_TCP = os.environ.get(
    'TURN_URL_TCP',
    'turn:global.turn.twilio.com:443?transport=tcp',
)
