#!/usr/bin/env python
"""
Test script to verify LAN Chat V2 can start properly
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("LAN CHAT V2 STARTUP TEST")
print("=" * 60)

# Test 1: Import database
print("\n[1/6] Testing database import...")
try:
    import db
    db.init_db()
    print("✓ Database initialized successfully")
except Exception as e:
    print(f"✗ Database failed: {e}")
    sys.exit(1)

# Test 2: Import core modules
print("\n[2/6] Testing core modules...")
try:
    from core.state import registry
    from core.events import event_bus
    from core.messages import Message, MessageBuilder
    from core.rooms import room_manager
    from core.presence import presence_manager
    print("✓ All core modules imported successfully")
except Exception as e:
    print(f"✗ Core modules failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Import socket manager
print("\n[3/6] Testing socket manager...")
try:
    from socket_manager import socket_app, sio
    print(f"✓ Socket manager imported successfully")
    print(f"  - socket_app type: {type(socket_app)}")
    print(f"  - sio type: {type(sio)}")
except Exception as e:
    print(f"✗ Socket manager failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Import event handlers
print("\n[4/6] Testing event handlers...")
try:
    import events.chat_events
    print("✓ Event handlers imported successfully")
except Exception as e:
    print(f"✗ Event handlers failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Check FastAPI app
print("\n[5/6] Testing FastAPI app...")
try:
    from app import app
    print(f"✓ FastAPI app imported successfully")
    print(f"  - app type: {type(app)}")
except Exception as e:
    print(f"✗ FastAPI app failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Verify uvicorn can run
print("\n[6/6] Testing uvicorn import...")
try:
    import uvicorn
    print(f"✓ Uvicorn imported successfully")
    print(f"  - uvicorn version: {uvicorn.__version__}")
except Exception as e:
    print(f"✗ Uvicorn failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED - Server should start successfully")
print("=" * 60)
print("\nTo start the server, run:")
print("  python main.py")
print("\nOr use the batch file:")
print("  run.bat")
