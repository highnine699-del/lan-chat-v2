# Socket.IO API Reference

This document describes every Socket.IO event the server sends and receives.
All payloads are JSON objects unless stated otherwise.

The client connects to the server's root URL using the Socket.IO client
library (`/static/` or CDN). The connection is established automatically
when the user logs in.

---

## Connection lifecycle

```
Client connects (Socket.IO handshake)
  → Client emits  'join'
  → Server emits  'joined'          back to caller
  → Server emits  'all_keys'        back to caller
  → Server emits  'message_history' back to caller
  → Server emits  'peer_key'        broadcast (exclude self)
  → Server emits  'user_list'       broadcast
  → Server emits  'system_message'  broadcast  ("<name> joined")

Client disconnects
  → Server emits  'user_list'       broadcast
  → Server emits  'system_message'  broadcast  ("<name> left")
```

---

## Events: client → server

### `join`

Register a username and share an E2E public key.

```jsonc
// payload
{
  "username":  "Alice",          // string, max 20 chars
  "publicKey": { /* JWK */ }     // optional — ECDH P-256 public key
}
```

If the username is already taken by another session, the server appends a
numeric suffix (`Alice2`, `Alice3`, …) and confirms the final name in the
`joined` response.

---

### `send_message`

Send a text message to global chat or a private recipient.

```jsonc
// global message
{
  "to":   "global",
  "text": "Hello everyone!"
}

// private plain-text message
{
  "to":   "Bob",
  "text": "Hey Bob"
}

// private end-to-end encrypted message
{
  "to":        "Bob",
  "text":      "🔒",
  "encrypted": "<base64(iv + AES-GCM ciphertext)>"
}
```

- `text` must be a non-empty string after trimming; empty messages are dropped.
- `encrypted` must be a non-empty string; any other type is silently dropped.
- The server forwards `encrypted` opaquely — it cannot read the content.

---

### `send_file`

Share a file that has already been uploaded via `POST /upload`.

```jsonc
{
  "to":        "global",           // or a username
  "url":       "/uploads/123_photo.jpg",
  "name":      "photo.jpg",        // original filename, capped at 260 chars
  "file_type": "image/jpeg"        // MIME type, capped at 128 chars
}
```

- `url` must start with `/uploads/`; any other value is silently dropped.

---

### `typing`

Notify others that the current user is typing.

```jsonc
{ "to": "global" }   // or a username for private chats
```

---

### `stop_typing`

Notify others that the current user stopped typing.

```jsonc
{ "to": "global" }   // or a username
```

---

### `webrtc_signal`

Forward a WebRTC signalling message to a specific peer.
The server routes the payload without inspecting it.

```jsonc
// offer (caller → server → callee)
{
  "to":       "Bob",
  "type":     "offer",
  "sdp":      { /* RTCSessionDescription */ },
  "callType": "voice"    // or "video"
}

// answer (callee → server → caller)
{
  "to":   "Alice",
  "type": "answer",
  "sdp":  { /* RTCSessionDescription */ }
}

// ICE candidate (either direction)
{
  "to":        "Bob",
  "type":      "ice",
  "candidate": { /* RTCIceCandidate */ }
}

// reject / end
{
  "to":   "Alice",
  "type": "reject"    // or "end"
}
```

If the target user is not connected, the server emits a `webrtc_signal`
error back to the caller:

```jsonc
{ "type": "error", "error": "User \"Bob\" is not connected" }
```

---

### Legacy call events

These events are kept for compatibility. The primary signalling path is
`webrtc_signal` above.

| Event | Payload | Triggers |
|---|---|---|
| `call-user` | `{ "to": "<username>" }` | `incoming-call` to target |
| `video-call-user` | `{ "to": "<username>" }` | `incoming-call` to target |
| `call-accepted` | `{ "to": "<username>" }` | `call-started` to target |
| `call-rejected` | `{ "to": "<username>" }` | `call-ended` to target |
| `end-call` | `{ "to": "<username>" }` | `call-ended` to target |

If the target is not connected the event is silently dropped (not broadcast).

---

## Events: server → client

### `joined`

Confirms the user's registration. Sent only to the joining client.

```jsonc
{
  "username": "Alice",    // may differ from requested name if a duplicate
  "color":    "#25D366"   // assigned avatar colour
}
```

---

### `all_keys`

All currently connected users' public keys. Sent only to the joining client.

```jsonc
{
  "Bob":     { /* ECDH P-256 JWK */ },
  "Charlie": { /* ECDH P-256 JWK */ }
}
```

---

### `peer_key`

A single user's public key. Broadcast to all existing clients when a new
user joins.

```jsonc
{
  "username":  "Alice",
  "publicKey": { /* ECDH P-256 JWK */ }
}
```

---

### `message_history`

The last 100 global messages. Sent only to the joining client.

```jsonc
[
  {
    "type":  "text",
    "from":  "Bob",
    "color": "#00a884",
    "text":  "Hello!",
    "time":  1713000000000,
    "to":    "global"
  }
]
```

---

### `new_message`

A new message (text or file). Sent to all relevant clients.

**Text message:**

```jsonc
{
  "type":      "text",
  "from":      "Alice",
  "color":     "#25D366",
  "text":      "Hello!",
  "time":      1713000000000,
  "to":        "global",
  "encrypted": "<base64>"    // only present for E2E-encrypted private messages
}
```

**File message:**

```jsonc
{
  "type":      "file",
  "from":      "Alice",
  "color":     "#25D366",
  "url":       "/uploads/1713000000000_photo.jpg",
  "name":      "photo.jpg",
  "file_type": "image/jpeg",
  "time":      1713000000000,
  "to":        "global"
}
```

---

### `user_list`

The current list of connected users. Broadcast whenever someone joins or
leaves.

```jsonc
[
  { "username": "Alice", "color": "#25D366" },
  { "username": "Bob",   "color": "#00a884" }
]
```

---

### `system_message`

A server-generated status message (join/leave notifications).

```jsonc
{
  "type": "system",
  "text": "Alice joined",
  "time": 1713000000000
}
```

---

### `typing` / `stop_typing`

Typing indicator from another user.

```jsonc
{ "username": "Bob", "to": "global" }
```

- For global chat: broadcast to all except the sender.
- For private chat: sent only to the target user.

---

### `webrtc_signal`

A forwarded WebRTC signalling message. The `from` field is added by the
server.

```jsonc
{
  "from":  "Alice",
  "to":    "Bob",
  "type":  "offer",
  "sdp":   { /* RTCSessionDescription */ }
}
```

---

### `incoming-call` / `call-started` / `call-ended`

Legacy call state events (see legacy call events table above).
Payload is an empty object `{}`.

---

## Message timestamps

All `time` fields are Unix timestamps in **milliseconds** (JavaScript
`Date.now()` format). Use `new Date(msg.time)` in the browser to convert.

---

## Client-side encryption

The client uses the browser's built-in `crypto.subtle` API — no external
library required.

```
Login
  crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveKey'])
  → export publicKey as JWK → send in 'join' event

Receive peer key
  crypto.subtle.importKey('jwk', peerJwk, { name: 'ECDH', namedCurve: 'P-256' }, ...)
  crypto.subtle.deriveKey({ name: 'ECDH', public: peerKey }, myPrivateKey,
                          { name: 'AES-GCM', length: 256 }, false, ['encrypt','decrypt'])

Encrypt (send)
  iv = crypto.getRandomValues(new Uint8Array(12))
  cipherBuf = crypto.subtle.encrypt({ name: 'AES-GCM', iv }, sharedKey, encoded)
  payload = btoa( iv + cipherBuf )   // base64(12-byte IV || ciphertext)

Decrypt (receive)
  combined = Uint8Array.from(atob(payload))
  iv       = combined.slice(0, 12)
  cipher   = combined.slice(12)
  plain    = crypto.subtle.decrypt({ name: 'AES-GCM', iv }, sharedKey, cipher)
```
