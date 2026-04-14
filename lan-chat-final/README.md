# LAN Chat - Final Version

A WhatsApp-like chat app that works offline over your local WiFi or hotspot.

## Quick Start (Windows)

**Option A - Double-click:**
1. Double-click `start.bat`
2. Wait for "Running on http://..." to appear
3. Open that URL in your browser

**Option B - CMD:**
```
cd path\to\lan-chat-final
python server.py
```

## How others join
Everyone connects to your hotspot, then opens:
```
http://192.168.137.1:3000
```
(The exact IP will be shown when the server starts)

## Features
- ✅ Real-time messaging (Global + Private chats)
- ✅ Emoji picker (click 😊 button)
- ✅ File & image sharing (click 📎 button)
- ✅ Voice messages (click 🎤 and tap send when done)
- ✅ Voice & video calls (WebRTC, private chats only)
- ✅ Typing indicators
- ✅ Online user list
- ✅ Unread message badges
- ✅ Image lightbox (click any image to expand)
- ✅ PWA installable (install from browser)

## Requirements
- Python 3.x
- pip install flask flask-socketio

## Notes
- Messages are stored in RAM only (lost when server stops)
- Files are saved in the `uploads/` folder
- Works on local network / hotspot only (not internet)
