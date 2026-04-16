"""
routes/http.py — Flask HTTP routes.

Endpoints
---------
GET  /                  Serve the single-page application.
GET  /uploads/<name>    Serve a previously uploaded file.
GET  /ice-config        Return WebRTC ICE/TURN configuration (JSON).
POST /upload            Accept a multipart file upload.
"""
import mimetypes
import os

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

from config import (
    MAX_UPLOAD_BYTES,
    TURN_CREDENTIALS,
    TURN_URL_TCP,
    TURN_URL_UDP,
    UPLOAD_FOLDER,
    ANALYTICS_KEY,
)
from state import now_ms, sanitize_filename, analytics, shadow_muted, spam_tracker, users

http_bp = Blueprint('http', __name__)

# Ensure the upload directory exists when this module is imported
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@http_bp.after_request
def set_no_cache(response):
    """Force browsers and proxies to never cache any response from this app."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# MIME types that are safe to display inline in the browser.
# Everything else gets Content-Disposition: attachment to prevent
# the browser from executing or rendering untrusted content.
_INLINE_MIME_PREFIXES = ('image/', 'audio/', 'video/')
_INLINE_MIME_EXACT    = {'application/pdf'}

# ── Build the ICE config once at startup ──────────────────────────────────────
# The ICE server list is static for the lifetime of the process.
# Building it once avoids repeated list construction and conditional checks
# on every /ice-config request.
def _build_ice_servers() -> list:
    servers = [
        {'urls': 'stun:stun.l.google.com:19302'},
        {'urls': 'stun:stun1.l.google.com:19302'},
        {'urls': 'stun:stun2.l.google.com:19302'},
        {'urls': 'stun:stun3.l.google.com:19302'},
        {'urls': 'stun:stun4.l.google.com:19302'},
    ]
    if TURN_CREDENTIALS:
        turn_user, _, turn_cred = TURN_CREDENTIALS.partition(':')
        if turn_user and turn_cred:
            for url in (TURN_URL_UDP, TURN_URL_TCP):
                servers.append({
                    'urls':       url,
                    'username':   turn_user,
                    'credential': turn_cred,
                })
    return servers

_ICE_CONFIG = {
    'iceServers':           _build_ice_servers(),
    'iceCandidatePoolSize': 20,
    'bundlePolicy':         'max-bundle',
    'rtcpMuxPolicy':        'require',
}


@http_bp.route('/')
def index():
    """Serve the single-page chat application."""
    return render_template('index.html')


@http_bp.route('/uploads/<path:filename>')
def uploaded_file(filename: str):
    """Serve a previously uploaded file.

    The ``path:`` converter rejects ``..`` path-traversal segments at the
    Werkzeug routing layer before this function is even called.
    Returns 404 explicitly if the file does not exist.

    Files that are not safe to render inline (i.e. not image/audio/video/pdf)
    are served with ``Content-Disposition: attachment`` so the browser
    downloads them rather than executing or rendering untrusted content.
    The ``X-Content-Type-Options: nosniff`` header prevents MIME-sniffing.
    """
    dest = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.isfile(dest):
        return jsonify({'error': 'File not found'}), 404

    # Determine whether the file can be displayed inline.
    mime, _ = mimetypes.guess_type(filename)
    if mime is None:
        mime = 'application/octet-stream'

    inline = (
        any(mime.startswith(p) for p in _INLINE_MIME_PREFIXES)
        or mime in _INLINE_MIME_EXACT
    )
    as_attachment = not inline

    response = send_from_directory(
        UPLOAD_FOLDER,
        filename,
        as_attachment=as_attachment,
        mimetype=mime,
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@http_bp.route('/ice-config')
def ice_config():
    """Return WebRTC ICE server configuration as JSON."""
    return jsonify(_ICE_CONFIG)


@http_bp.route('/analytics')
def analytics_endpoint():
    """
    Server health dashboard — for the server owner only.

    Protected by X-Admin-Key header matching the ANALYTICS_KEY env var.
    Returns 403 if the key is wrong or not set.
    """
    if not ANALYTICS_KEY:
        return jsonify({'error': 'Analytics endpoint is disabled.'}), 403

    if request.headers.get('X-Admin-Key', '') != ANALYTICS_KEY:
        return jsonify({'error': 'Forbidden'}), 403

    import time as _time
    uptime_s = int(_time.time() - analytics['started_at'])

    shadow_list = [
        {'sid': sid, 'until': v['until']}
        for sid, v in shadow_muted.items()
    ]
    spam_list = [
        {
            'sid':             sid,
            'cooldown_until':  t.get('cooldown_until', 0),
            'in_cooldown':     _time.time() < t.get('cooldown_until', 0),
        }
        for sid, t in spam_tracker.items()
        if t.get('cooldown_until', 0) > _time.time()
    ]

    return jsonify({
        'uptime_seconds':  uptime_s,
        'active_users':    len(users),
        'peak_users':      analytics['peak_users'],
        'messages_sent':   analytics['messages_sent'],
        'files_uploaded':  analytics['files_uploaded'],
        'rooms_created':   analytics['rooms_created'],
        'errors':          analytics['errors'],
        'shadow_muted':    shadow_list,
        'active_cooldowns': spam_list,
    })


@http_bp.route('/health')
def health():
    """Simple health check endpoint."""
    import time as _time
    return jsonify({
        'status':       'ok',
        'active_users': len(users),
        'uptime_s':     int(_time.time() - analytics['started_at']),
    })


@http_bp.route('/upload', methods=['POST'])
def upload():
    """Accept a multipart file upload and return its public URL.

    Returns 400 if the ``file`` field is missing or has an empty filename.
    Returns 413 if the request body exceeds MAX_UPLOAD_BYTES.
    Returns 500 if the file cannot be written to disk.
    """
    # Guard against oversized requests before touching the body
    content_length = request.content_length
    if content_length and content_length > MAX_UPLOAD_BYTES:
        return jsonify({'error': 'File too large'}), 413

    if 'file' not in request.files:
        return jsonify({'error': 'No file field in request'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    safe_name   = sanitize_filename(file.filename)
    stored_name = f'{now_ms()}_{safe_name}'
    dest        = os.path.join(UPLOAD_FOLDER, stored_name)

    # Guard against path traversal: ensure the resolved path is inside UPLOAD_FOLDER
    if not os.path.abspath(dest).startswith(os.path.abspath(UPLOAD_FOLDER) + os.sep):
        return jsonify({'error': 'Invalid filename'}), 400

    try:
        file.save(dest)
    except OSError as exc:
        return jsonify({'error': f'Could not save file: {exc}'}), 500

    # Reject zero-byte files (e.g. empty blob uploads)
    if os.path.getsize(dest) == 0:
        try:
            os.remove(dest)
        except OSError:
            pass
        return jsonify({'error': 'Empty file'}), 400

    return jsonify({
        'url':  f'/uploads/{stored_name}',
        'name': file.filename,
        'type': file.content_type or 'application/octet-stream',
    })
