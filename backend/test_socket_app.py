#!/usr/bin/env python
"""Test if socket_app can be imported and accessed"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

with open('test_output.txt', 'w') as f:
    f.write("Testing socket_app import...\n")
    try:
        from socket_manager import socket_app, sio
        f.write(f"✓ socket_app imported: {type(socket_app)}\n")
        f.write(f"✓ sio imported: {type(sio)}\n")
        
        # Check if socket_app has the expected attributes
        f.write(f"socket_app attributes: {dir(socket_app)}\n")
        
        # Try to get the ASGI app
        f.write(f"ASGI app: {socket_app}\n")
        
    except Exception as e:
        f.write(f"✗ Error: {e}\n")
        import traceback
        f.write(traceback.format_exc())
        sys.exit(1)

    f.write("\n✓ socket_app test passed\n")

print("Test complete - check test_output.txt")
