# LAN Chat

A WhatsApp-style real-time chat application that runs entirely on your local
WiFi or hotspot — no internet required. Private messages are end-to-end
encrypted in the browser using the Web Crypto API (ECDH P-256 + AES-256-GCM).

---

## Ownership

This project was independently designed and developed by the repository owner.

Initial development began: January 2026

Core system includes real-time LAN communication, WebRTC peer-to-peer audio/video
calls, ECDH-AES-GCM end-to-end encryption for private messages, AES-GCM room
encryption, a room approval/knock system, reconnect sync with sequence tracking,
admin controls, and a full Socket.IO event architecture.

All architecture, design decisions, and implementation are original work.

---

## Features

| Feature | Details |
|---|---|
| Global chat | Broadcast to everyone on the network |
| Private DMs | 1-to-1, end-to-end encrypted (ECDH P-256 + AES-256-GCM) |
| Rooms | Named group chats with AES-GCM session encryption |
| Room approval | Knock/approve join flow for private rooms |
| Voice & video calls | WebRTC peer-to-peer, private chats only |
| File & image sharing | Up to 50 MB per file |
| Voice messages | Recorded in-browser, sent as WebM audio |
| Emoji picker | Bundled locally — works fully offline |
| Typing indicators | Real-time per-conversation |
| Unread badges | Per-conversation unread count |
| Reconnect sync | Sequence-tracked message resync on reconnect |
| Admin controls | Hidden admin panel, room freeze/unfreeze, mod roles |
| PWA installable | "Add to Home Screen" from any mobile browser |

---

## Architecture summary

```
server.py          Entry point — Flask + Socket.IO
config.py          All constants and environment-variable bindings
state.py           Shared in-memory state + pure helper functions
routes/
  http.py          HTTP routes (/, /upload, /uploads, /ice-config)
  sockets.py       All Socket.IO event handlers
templates/
  index.html       Single-page application shell
static/
  app.js           All client-side logic (~3000 lines)
  style.css        All styles
  emoji-picker.*   Bundled offline emoji picker
tests/             pytest suite — state, HTTP, and Socket.IO integration tests
```

The server is a dumb relay for encrypted payloads — it never sees plaintext
private message content. All encryption/decryption happens in the browser.

See [`lan-chat-final/ARCHITECTURE.md`](lan-chat-final/ARCHITECTURE.md) for the
full architecture document.

---

## Quick start

```bash
cd lan-chat-final
pip install flask flask-socketio
python server.py
```

Or on Windows, double-click `lan-chat-final/start.bat`.

See [`lan-chat-final/README.md`](lan-chat-final/README.md) for full setup
instructions, configuration options, and test instructions.

---

## Project structure

```
lan-chat-final/     ⭐ Current working version
archive/            📦 Earlier iterations (preserved for reference)
  lan-chat-python/
  lan-chat-advanced/
  lan-chat-v3/
```

---

## License

MIT License — see [LICENSE](LICENSE).
