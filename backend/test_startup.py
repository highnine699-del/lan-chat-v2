import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

print("=== Testing Startup ===")
print("Step 1: Import db...")
try:
    import db
    db.init_db()
    print("✓ DB initialized")
except Exception as e:
    print(f"✗ DB failed: {e}")
    import traceback
    traceback.print_exc()

print("\nStep 2: Import socket_manager...")
try:
    from socket_manager import socket_app
    print("✓ socket_app imported")
except Exception as e:
    print(f"✗ socket_manager failed: {e}")
    import traceback
    traceback.print_exc()

print("\nStep 3: Import events.chat_events...")
try:
    import events.chat_events
    print("✓ chat_events imported")
except Exception as e:
    print(f"✗ chat_events failed: {e}")
    import traceback
    traceback.print_exc()

print("\nStep 4: Check socket_app...")
try:
    print(f"socket_app type: {type(socket_app)}")
    print(f"socket_app: {socket_app}")
except Exception as e:
    print(f"✗ socket_app check failed: {e}")

print("\n=== Startup Test Complete ===")
