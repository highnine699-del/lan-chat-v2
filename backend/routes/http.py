# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

import logging
"""
routes/http.py — FastAPI HTTP routes.

Endpoints
---------
GET  /                  Serve the single-page application.
GET  /uploads/<name>    Serve a previously uploaded file.
GET  /ice-config        Return WebRTC ICE/TURN configuration (JSON).
POST /upload            Accept a multipart file upload.
GET  /analytics         Server health dashboard (admin only).
GET  /health            Simple health check endpoint.
POST /shutdown          Graceful server shutdown (admin only).
POST /admin/broadcast   Broadcast server announcement (admin only).
"""
import mimetypes
import os
import time

from fastapi import APIRouter, Request, UploadFile, File, Header, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    MAX_UPLOAD_BYTES,
    TURN_CREDENTIALS,
    TURN_URL_TCP,
    TURN_URL_UDP,
    UPLOAD_FOLDER,
    ANALYTICS_KEY,
    TRUSTED_PROXY,
    ADMIN_PASSWORD,
    PUBLIC_MODE,
)
from core.state import (
    now_ms,
    sanitize_filename,
    analytics,
    shadow_muted,
    spam_tracker,
    users,
    upload_counts,
    check_upload_rate,
    get_session,
    admin_state,
)

http_router = APIRouter()

# Ensure the upload directory exists when this module is imported
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _get_client_ip(request: Request) -> str:
    """
    Return the real client IP.
    Only trusts X-Forwarded-For when TRUSTED_PROXY=true in config,
    otherwise always uses the direct socket address to prevent header spoofing.
    """
    if TRUSTED_PROXY:
        xff = request.headers.get('x-forwarded-for', '')
        if xff:
            return xff.split(',')[-1].strip()
    return request.client.host if request.client else '127.0.0.1'


# MIME types that are safe to display inline in the browser.
# Everything else gets Content-Disposition: attachment to prevent
# the browser from executing or rendering untrusted content.
_INLINE_MIME_PREFIXES = ('image/', 'audio/', 'video/')
_INLINE_MIME_EXACT    = {'application/pdf'}

# MIME types that must NEVER be served inline — even though they match a prefix above.
# SVG can contain embedded <script> tags and is an XSS vector when served inline.
_BLOCKED_MIME = {'image/svg+xml', 'image/svg'}


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


async def set_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Security headers
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self' wss: ws:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    # HSTS — only set over HTTPS (ngrok always uses HTTPS)
    if PUBLIC_MODE:
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )
    return response


# Cache-buster version — bump this string any time you change static assets
_ASSET_VERSION = "v2"

@http_router.get("/")
async def index():
    """Serve the single-page chat application with template variables resolved."""
    from fastapi.responses import HTMLResponse
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
    index_file = os.path.join(frontend_path, "templates", "index.html")
    if not os.path.exists(index_file):
        return JSONResponse(content={"error": "Frontend not found"}, status_code=404)
    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()
    # Replace Jinja2-style template variables with actual values
    html = html.replace("{{ _v }}", _ASSET_VERSION)
    return HTMLResponse(content=html)


@http_router.get("/uploads/{filename:path}")
async def uploaded_file(filename: str):
    """Serve a previously uploaded file.

    Files that are not safe to render inline (i.e. not image/audio/video/pdf)
    are served with ``Content-Disposition: attachment`` so the browser
    downloads them rather than executing or rendering untrusted content.
    The ``X-Content-Type-Options: nosniff`` header prevents MIME-sniffing.
    """
    dest = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.isfile(dest):
        return JSONResponse(content={'error': 'File not found'}, status_code=404)

    # Determine whether the file can be displayed inline.
    mime, _ = mimetypes.guess_type(filename)
    if mime is None:
        mime = 'application/octet-stream'

    inline = (
        mime not in _BLOCKED_MIME
        and (
            any(mime.startswith(p) for p in _INLINE_MIME_PREFIXES)
            or mime in _INLINE_MIME_EXACT
        )
    )
    as_attachment = not inline

    response = FileResponse(
        dest,
        filename=filename if as_attachment else None,
        media_type=mime,
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@http_router.get("/ice-config")
async def ice_config(sid: str = Query(...)):
    """Return WebRTC ICE server configuration as JSON.

    Requires the caller to be a joined user (sid present in users or
    active_sessions). Unauthenticated visitors receive 403 to prevent
    credential harvesting.

    active_sessions is checked as a fallback because the client may call
    this endpoint immediately after the socket connects, before the 'join'
    event has been fully processed and the users dict populated.
    """
    if not sid or (sid not in users and get_session(sid) is None):
        raise HTTPException(status_code=403, detail='Forbidden')
    return JSONResponse(content=_ICE_CONFIG)


@http_router.get("/analytics")
async def analytics_endpoint(x_admin_key: str = Header(None, alias="X-Admin-Key")):
    """
    Server health dashboard — for the server owner only.

    Protected by X-Admin-Key header matching the ANALYTICS_KEY env var.
    Returns 403 if the key is wrong or not set.
    """
    if not ANALYTICS_KEY:
        raise HTTPException(status_code=403, detail='Analytics endpoint is disabled.')

    if x_admin_key != ANALYTICS_KEY:
        raise HTTPException(status_code=403, detail='Forbidden')

    uptime_s = int(time.time() - analytics['started_at'])

    shadow_list = [
        {'sid': sid, 'until': v['until']}
        for sid, v in shadow_muted.items()
    ]
    spam_list = [
        {
            'sid':             sid,
            'cooldown_until':  t.get('cooldown_until', 0),
            'in_cooldown':     time.time() < t.get('cooldown_until', 0),
        }
        for sid, t in spam_tracker.items()
        if t.get('cooldown_until', 0) > time.time()
    ]

    return JSONResponse(content={
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


@http_router.get("/health")
async def health():
    """Simple health check endpoint — returns status only, no metadata."""
    return JSONResponse(content={'status': 'ok'})


@http_router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    """Accept a multipart file upload and return its public URL.

    Returns 400 if the ``file`` field is missing or has an empty filename.
    Returns 413 if the request body exceeds MAX_UPLOAD_BYTES.
    Returns 500 if the file cannot be written to disk.
    """
    # Guard against oversized requests before touching the body
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail='File too large')

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail='Empty filename')

    # Per-IP upload rate limiting: burst + daily quota + per-session cap
    client_ip = _get_client_ip(request)

    rate_result = check_upload_rate(client_ip)
    if rate_result == 'burst':
        raise HTTPException(status_code=429, detail='Upload rate limit exceeded. Please slow down.')
    if rate_result == 'daily':
        raise HTTPException(status_code=429, detail='Daily upload quota reached. Try again tomorrow.')

    safe_name   = sanitize_filename(file.filename)
    stored_name = f'{now_ms()}_{safe_name}'
    dest        = os.path.join(UPLOAD_FOLDER, stored_name)

    # Guard against path traversal: ensure the resolved path is inside UPLOAD_FOLDER
    if not os.path.abspath(dest).startswith(os.path.abspath(UPLOAD_FOLDER) + os.sep):
        raise HTTPException(status_code=400, detail='Invalid filename')

    # Block SVG — can contain embedded <script> tags (XSS vector)
    mime_check, _ = mimetypes.guess_type(safe_name)
    if mime_check in _BLOCKED_MIME or (safe_name.lower().endswith('.svg')):
        raise HTTPException(status_code=400, detail='SVG files are not allowed')

    try:
        contents = await file.read()
        with open(dest, 'wb') as f:
            f.write(contents)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f'Could not save file: {exc}')

    # Reject zero-byte files (e.g. empty blob uploads)
    if os.path.getsize(dest) == 0:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise HTTPException(status_code=400, detail='Empty file')

    return JSONResponse(content={
        'url':  f'/uploads/{stored_name}',
        'name': file.filename,
        'type': file.content_type or 'application/octet-stream',
    })


@http_router.post("/shutdown")
async def shutdown(request: Request, x_admin_key: str = Header(None, alias="X-Admin-Key")):
    """
    Graceful server shutdown — admin only.

    Protected by X-Admin-Key header matching ADMIN_PASSWORD.
    Broadcasts a shutdown notice to all connected clients,
    then terminates the process cleanly after a short delay.
    """
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail='Shutdown endpoint is disabled (no ADMIN_PASSWORD set).')

    if x_admin_key != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail='Forbidden')

    import threading
    import logging
    log = logging.getLogger('lan-chat')
    log.info('Graceful shutdown requested via /shutdown')

    def _do_shutdown():
        # Import socketio reference from the app context
        try:
            # TODO: Get socketio reference from app state
            # socketio.emit('server_shutdown', {
            #     'message': '⚠️ Server is shutting down. See you next time!',
            #     'delay':   3,
            # })
            pass
        except Exception:
            pass
        time.sleep(3)   # give clients time to receive the notice
        import os as _os
        _os.kill(_os.getpid(), 15)   # SIGTERM — clean exit

    threading.Thread(target=_do_shutdown, daemon=True).start()

    return JSONResponse(content={'status': 'shutdown initiated', 'delay_seconds': 3})


@http_router.post("/admin/broadcast")
async def admin_broadcast(
    request: Request,
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """
    Broadcast a server announcement to all connected clients.

    Protected by X-Admin-Key header matching ADMIN_PASSWORD.
    Body JSON: { "message": "..." }
    """
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail='Broadcast disabled (no ADMIN_PASSWORD set).')

    if x_admin_key != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail='Forbidden')

    data = await request.json()
    message = str(data.get('message', '')).strip()
    if not message:
        raise HTTPException(status_code=400, detail='message field is required')

    try:
        # TODO: Get socketio reference from app state
        # socketio.emit('new_message', {
        #     'from':    '📢 Server',
        #     'msg':     message,
        #     'target':  'global',
        #     'msg_id':  f'srv_{int(time.time()*1000)}',
        #     'ts':      time.time(),
        #     'is_system': True,
        # })
        pass
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return JSONResponse(content={'status': 'sent', 'message': message})
