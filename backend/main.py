import os
import sys
import uvicorn

# Ensure directories exist
backend_dir = os.path.dirname(__file__)
events_dir = os.path.join(backend_dir, "events")
core_dir = os.path.join(backend_dir, "core")

os.makedirs(events_dir, exist_ok=True)
os.makedirs(core_dir, exist_ok=True)

# Initialize database
import db
db.init_db()

# Create __init__.py files if they don't exist
for init_file in [
    os.path.join(events_dir, "__init__.py"),
    os.path.join(core_dir, "__init__.py"),
]:
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("")

# Create chat_events.py if it doesn't exist
chat_events_path = os.path.join(events_dir, "chat_events.py")
if not os.path.exists(chat_events_path):
    with open(chat_events_path, "w") as f:
        f.write('''from socket_manager import sio

@sio.event
async def connect(sid, environ):
    print("Client connected:", sid)

@sio.event
async def disconnect(sid):
    print("Client disconnected:", sid)

@sio.event
async def message(sid, data):
    print("Message received:", data)
    await sio.emit("message", data)
''')

from socket_manager import socket_app

# register events
import events.chat_events

if __name__ == "__main__":
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=8000
    )
