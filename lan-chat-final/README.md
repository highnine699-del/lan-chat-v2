# LAN Chat

A WhatsApp-style real-time chat app that runs entirely on your local WiFi or
hotspot — no internet required for messaging. Private messages are
end-to-end encrypted in the browser using the Web Crypto API.

---

## Quick start

### Option A — double-click (Windows)

1. Double-click `start.bat`
2. Wait for the startup banner to appear in the console
3. The browser opens automatically at your network URL

### Option B — command line

```bash
cd lan-chat-final
pip install flask flask-socketio
python server.py
```

The console will print two URLs:

```
  Local:   http://127.0.0.1:5000      ← your own browser
  Network: http://192.168.x.x:5000    ← share this with others on the same WiFi
```

### Option C — GUI launcher (with ngrok public URL)

```bash
python launcher.py
```

The launcher window lets you start/stop the server, see the public ngrok URL,
and copy it to the clipboard.

---

## How others join

Everyone must be on the **same WiFi network or hotspot** as the machine
running the server. They open the Network URL shown in the console.

---

## Features

| Feature | Notes |
|---|---|
| Global chat | Broadcast to everyone on the network |
| Private DMs | 1-to-1, end-to-end encrypted |
| Emoji picker | Bundled locally — works offline |
| File & image sharing | Up to 50 MB per file |
| Voice messages | Recorded in-browser, sent as WebM audio |
| Voice calls | WebRTC peer-to-peer, private chats only |
| Video calls | WebRTC peer-to-peer, private chats only |
| Typing indicators | Shows who is typing in real time |
| Unread badges | Per-conversation unread count |
| Image lightbox | Click any image to expand it |
| PWA installable | "Add to Home Screen" from the browser |

---

## Requirements

- Python 3.10 or later
- `flask` and `flask-socketio` (installed automatically by `start.bat`)

```bash
pip install flask flask-socketio
```

---

## Project layout

```
lan-chat-final/
├── server.py              Entry point — creates the app and runs the server
├── config.py              All constants and environment-variable bindings
├── state.py               Shared in-memory state + pure helper functions
├── routes/
│   ├── __init__.py        register_routes() wires HTTP + Socket.IO to the app
│   ├── http.py            Flask HTTP routes (/, /upload, /uploads, /ice-config)
│   └── sockets.py         All Socket.IO event handlers
├── templates/
│   └── index.html         Single-page application (HTML + CSS + JS)
├── static/
│   ├── emoji-picker.js         Offline emoji picker entry point
│   ├── emoji-picker-picker.js  Emoji picker component (bundled)
│   ├── emoji-picker-database.js Emoji data (bundled)
│   ├── manifest.json           PWA manifest
│   └── wallpaper.svg           Chat background
├── tests/
│   ├── test_state.py      Unit tests for state.py helpers
│   ├── test_http.py       Integration tests for HTTP routes
│   └── test_sockets.py    Integration tests for Socket.IO events
├── uploads/               Uploaded files (created automatically)
├── download_assets.py     Downloads emoji picker files for offline use
├── launcher.py            Tkinter GUI launcher with ngrok integration
├── start.bat              One-click Windows launcher
├── create-shortcut.ps1    Creates a desktop shortcut for start.bat
└── create-gui-shortcut.ps1 Creates a desktop shortcut for launcher.py
```

---

## Configuration

All settings live in `config.py` and can be overridden with environment
variables before starting the server.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `lanchatsecret2024` | Flask session secret — change in production |
| `TURN_CREDENTIALS` | *(unset)* | `"username:credential"` for a TURN server |
| `TURN_URL_UDP` | Twilio global UDP | TURN server UDP URL |
| `TURN_URL_TCP` | Twilio global TCP | TURN server TCP URL |

**Example — set a custom TURN server on Windows:**

```bat
set TURN_CREDENTIALS=myuser:mypassword
set TURN_URL_UDP=turn:myturn.example.com:3478?transport=udp
python server.py
```

**Example — set a custom TURN server on Linux/macOS:**

```bash
TURN_CREDENTIALS=myuser:mypassword python server.py
```

> TURN credentials are served to clients via the `/ice-config` endpoint and
> are **never** embedded in the HTML source.

---

## Security notes

| Concern | Status |
|---|---|
| Private message content | ✅ E2E encrypted (ECDH P-256 + AES-256-GCM) |
| LAN transport | ⚠️ Plain HTTP — use ngrok HTTPS URL for full encryption |
| TURN credentials | ✅ Server-side only, served via `/ice-config` |
| File upload path traversal | ✅ Sanitised — `os.path.basename` + regex |
| Oversized uploads | ✅ Rejected at 50 MB (Flask `MAX_CONTENT_LENGTH`) |
| Duplicate usernames | ✅ Auto-suffixed (`Alice` → `Alice2`) |

---

## Running the tests

```bash
cd lan-chat-final
pip install pytest
python -m pytest tests/ -v
```

Expected output: **82 passed** across three test files covering state helpers,
HTTP routes, and Socket.IO events.

---

## Bundling the emoji picker (offline use)

The emoji picker is bundled locally so the app works without internet.
If the `static/emoji-picker*.js` files are missing, run:

```bash
python download_assets.py
```

`start.bat` runs this automatically on first launch.

---

## Notes

- All messages are stored in RAM only — they are lost when the server stops.
- Uploaded files are saved to `uploads/` and persist across restarts.
- The server runs in debug mode by default; set `debug=False` in `server.py`
  before deploying to a shared network you do not fully trust.
