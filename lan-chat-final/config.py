"""
config.py — All configuration constants and environment-variable bindings.

Import this module anywhere you need a setting; never read os.environ
directly in other modules.
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
MAX_UPLOAD_BYTES = MAX_HTTP_BUFFER_SIZE    # same 50 MB cap applied at the HTTP layer

# ── Chat limits ───────────────────────────────────────────────────────────────
MAX_USERNAME_LEN     = 20
MAX_MESSAGE_LEN      = 2000  # characters — prevents RAM exhaustion via huge messages
MAX_GLOBAL_HISTORY   = 500   # messages kept in RAM for global chat
MAX_PRIVATE_HISTORY  = 200   # messages kept per private conversation
MAX_SIGNAL_BYTES     = 64 * 1024  # 64 KB — max size of a WebRTC signal payload

# ── Spam / rate-limiting ──────────────────────────────────────────────────────
SPAM_MSG_LIMIT    = 5    # max messages allowed in the window
SPAM_WINDOW_S     = 5    # rolling window in seconds
SPAM_COOLDOWN_S   = 20   # cooldown duration after limit is hit
SPAM_REPEAT_LIMIT = 3    # same message repeated this many times → shadow mute
SPAM_FLOOD_WINDOW = 10   # seconds to check for copy-paste floods

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

# ── User avatar colours (round-robin) ─────────────────────────────────────────
USER_COLORS = [
    '#25D366', '#00a884', '#53bdeb', '#f0b429',
    '#e06c75', '#c678dd', '#56b6c2', '#e5c07b',
]

# ── WebRTC / TURN ─────────────────────────────────────────────────────────────
# Set TURN_CREDENTIALS="username:credential" in the environment to enable TURN.
# Leave unset for STUN-only (works fine on the same LAN).
TURN_CREDENTIALS = os.environ.get('TURN_CREDENTIALS', '')
TURN_URL_UDP = os.environ.get(
    'TURN_URL_UDP',
    'turn:global.turn.twilio.com:3478?transport=udp',
)
TURN_URL_TCP = os.environ.get(
    'TURN_URL_TCP',
    'turn:global.turn.twilio.com:443?transport=tcp',
)
