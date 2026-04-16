# Architecture

This document describes how the server-side code is structured, how the
modules relate to each other, and the design decisions behind them.

---

## Module map

```
server.py   ──imports──▶  config.py
    │                     state.py
    │                     routes/__init__.py
    │                          │
    │                          ├──▶ routes/http.py     (Flask Blueprint)
    │                          └──▶ routes/sockets.py  (Socket.IO handlers)
    │
    └── creates Flask app + SocketIO instance, then calls register_routes()
```

Each module has a single responsibility and a strict import direction —
lower-level modules never import from higher-level ones.

---

## `config.py` — configuration

Single source of truth for every constant and environment variable.
No other module reads `os.environ` directly.

```python
from config import MAX_UPLOAD_BYTES, TURN_CREDENTIALS
```

Changing a limit (e.g. max message history, upload size) means editing
one line in one file.

---

## `state.py` — shared state + helpers

Holds all mutable in-memory state:

| Variable | Type | Contents |
|---|---|---|
| `users` | `dict` | `sid → {username, color, joined_at}` |
| `sid_map` | `dict` | `username → sid` (reverse lookup) |
| `public_keys` | `dict` | `username → ECDH JWK` (E2E encryption) |
| `message_history` | `list` | Global chat messages (capped at 500) |
| `private_history` | `dict` | `"userA\|userB" → list[msg]` (capped at 200 each) |

Also contains pure helper functions with no Flask/Socket.IO imports, making
them independently testable:

| Function | Purpose |
|---|---|
| `clean_username(raw)` | Coerce and trim a username string |
| `unique_username(wanted, sid)` | Resolve duplicate names with numeric suffix |
| `next_color()` | Round-robin avatar colour from the palette |
| `private_key(a, b)` | Canonical sorted key for a private conversation |
| `append_private(key, msg)` | Append to private history with cap enforcement |
| `sanitize_filename(raw)` | Strip path components, replace unsafe characters |
| `get_user_list()` | Serialisable list of connected users |
| `now_ms()` | Current Unix time in milliseconds |

---

## `routes/http.py` — HTTP endpoints

A Flask `Blueprint` registered on the app by `register_routes()`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves `templates/index.html` |
| `GET` | `/uploads/<file>` | Serves an uploaded file; 404 JSON if missing |
| `GET` | `/ice-config` | Returns WebRTC ICE/TURN config as JSON |
| `POST` | `/upload` | Accepts a multipart file, returns `{url, name, type}` |

**Upload flow:**

```
Client POSTs multipart/form-data
  → Flask checks Content-Length ≤ 50 MB  (MAX_CONTENT_LENGTH)
  → route checks content_length header   (early 413)
  → filename sanitised via sanitize_filename()
  → stored as  <timestamp_ms>_<safe_name>  in uploads/
  → returns JSON  {url, name, type}
```

**ICE config flow:**

```
Client GETs /ice-config on page load
  → server reads TURN_CREDENTIALS from environment
  → if set: appends TURN entries with username/credential
  → returns JSON ICE config
  → client caches result; credentials never appear in HTML
```

---

## `routes/sockets.py` — Socket.IO events

All handlers are registered inside `register_socket_handlers(socketio)`.
This closure pattern gives every handler access to shared inner helpers
(`current_sid`, `current_user`, `dispatch_message`, `relay_to_target`)
without polluting the module namespace.

### Message dispatch

Both `send_message` and `send_file` share a single `dispatch_message(msg, target)` helper:

```
target == 'global'
  → append to message_history (pop oldest if > MAX_GLOBAL_HISTORY)
  → emit 'new_message' broadcast

target == <username>
  → append to private_history[key] (pop oldest if > MAX_PRIVATE_HISTORY)
  → emit 'new_message' to recipient's sid
  → emit 'new_message' echo to sender's sid
```

### Call signalling

Legacy call events (`call-user`, `call-accepted`, etc.) are registered from
a table rather than five identical functions:

```python
_CALL_EVENT_MAP = {
    'call-user':       'incoming-call',
    'video-call-user': 'incoming-call',
    'call-accepted':   'call-started',
    'call-rejected':   'call-ended',
    'end-call':        'call-ended',
}
```

The primary WebRTC signalling path is `webrtc_signal`, which forwards SDP
offers/answers and ICE candidates directly between peers. The server never
inspects the payload.

---

## End-to-end encryption

Private messages are encrypted in the browser before being sent to the server.
The server relays the ciphertext opaquely.

```
Alice logs in
  → browser generates ECDH P-256 key pair  (Web Crypto API)
  → public key JWK sent to server in 'join' event
  → server stores it in public_keys['Alice']
  → server sends all existing public keys back to Alice  ('all_keys')
  → server broadcasts Alice's key to everyone else       ('peer_key')

Alice sends a DM to Bob
  → browser derives shared secret:  ECDH(Alice.private, Bob.public)
  → encrypts message:  AES-256-GCM(shared_secret, plaintext)
  → sends {text: '🔒', encrypted: '<base64 iv+ciphertext>'}
  → server forwards the payload unchanged
  → Bob's browser decrypts:  AES-256-GCM(shared_secret, ciphertext)
```

Global messages are not encrypted — they are broadcast to everyone, so
encryption would provide no benefit.

---

## In-memory state and restarts

All chat state is RAM-only by design. This keeps the server stateless and
simple — no database setup required. The trade-off is that messages are lost
when the server stops.

Uploaded files in `uploads/` do persist across restarts.

---

## Testing

Tests are in `tests/` and use `pytest` with Flask and Socket.IO test clients.

```
tests/test_state.py    — pure unit tests, no server needed  (28 tests)
tests/test_http.py     — HTTP route integration tests       (18 tests)
tests/test_sockets.py  — Socket.IO event integration tests  (36 tests)
```

Run with:

```bash
python -m pytest tests/ -v
```

The `autouse` fixture in each file resets all shared state before every test,
so tests are fully isolated and can run in any order.
