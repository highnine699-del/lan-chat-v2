#!/usr/bin/env python
"""Verify all imports work without starting server"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")
try:
    import db
    db.init_db()
    print("✓ db")
except Exception as e:
    print(f"✗ db: {e}")
    sys.exit(1)

try:
    from socket_manager import socket_app, sio
    print("✓ socket_manager")
except Exception as e:
    print(f"✗ socket_manager: {e}")
    sys.exit(1)

try:
    from core.state import registry
    from core.events import event_bus
    from core.messages import Message, MessageBuilder
    from core.rooms import room_manager
    from core.presence import presence_manager
    print("✓ core modules")
except Exception as e:
    print(f"✗ core modules: {e}")
    sys.exit(1)

try:
    import events.chat_events
    print("✓ events.chat_events")
except Exception as e:
    print(f"✗ events.chat_events: {e}")
    sys.exit(1)

try:
    from app import app
    print("✓ app (FastAPI)")
except Exception as e:
    print(f"✗ app: {e}")
    sys.exit(1)

try:
    import uvicorn
    print(f"✓ uvicorn {uvicorn.__version__}")
except Exception as e:
    print(f"✗ uvicorn: {e}")
    sys.exit(1)

print("\n✓ All imports successful")
