# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

import logging
import os

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from socket_manager import sio, create_socket_app
from routes.http import http_router, set_security_headers
from routes.sockets import register_socket_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background workers on startup, clean up on shutdown."""
    from core.state import start_cleanup_worker
    start_cleanup_worker()
    logging.getLogger('lan-chat').info('LAN Chat V2 — cleanup worker started')
    yield
    # Shutdown: nothing special needed (in-memory state)


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan)

# Security headers middleware (must be on the FastAPI app, not APIRouter)
app.middleware("http")(set_security_headers)

# Register Socket.IO event handlers
register_socket_handlers(sio)

# HTTP routes (handles /, /upload, /health, /ice-config, etc.)
app.include_router(http_router)

# Static files
static_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "static"
)
if os.path.isdir(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# ── ASGI root app — this is what uvicorn runs ─────────────────────────────────
# socketio.ASGIApp wraps FastAPI and handles /socket.io/* internally.
# Must be the ROOT ASGI app, NOT mounted as a FastAPI sub-app.
asgi_app = create_socket_app(app)

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("app:asgi_app", host="0.0.0.0", port=8000, reload=False)
