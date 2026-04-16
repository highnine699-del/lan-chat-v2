"""
routes/__init__.py — Registers all route modules with the Flask app.

Usage (in server.py):
    from routes import register_routes
    register_routes(app, socketio)
"""
from routes.http    import http_bp
from routes.sockets import register_socket_handlers


def register_routes(app, socketio):
    """Attach HTTP blueprint and Socket.IO handlers to *app*."""
    app.register_blueprint(http_bp)
    register_socket_handlers(socketio)
