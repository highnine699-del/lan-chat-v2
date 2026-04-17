// ─── DEV MODE ─────────────────────────────────────────────
// Active on localhost automatically, or manually via:
//   localStorage.setItem("dev_mode", "true")  → reload
//   localStorage.removeItem("dev_mode")        → reload to disable
const DEV_MODE =
  location.hostname === 'localhost' ||
  location.hostname === '127.0.0.1' ||
  localStorage.getItem('dev_mode') === 'true';

const debugState = {
  connected: false,
  userId: null,
  roomId: null,
  hasKey: false,
  queueSize: 0,
  lastDecrypt: 'N/A',
};

function updateDebugPanel() {
  if (!DEV_MODE) return;
  const panel = document.getElementById('debugPanel');
  if (!panel) return;
  panel.style.display = 'block';
  document.getElementById('dbg-conn').textContent =
    'Connection: ' + (debugState.connected ? '✅ Connected' : '❌ Disconnected');
  document.getElementById('dbg-user').textContent =
    'User: ' + (debugState.userId || 'N/A');
  document.getElementById('dbg-room').textContent =
    'Room: ' + (debugState.roomId || 'None');
  document.getElementById('dbg-key').textContent =
    'Room Key: ' + (debugState.hasKey ? '✅ Loaded' : '❌ Missing');
  document.getElementById('dbg-queue').textContent =
    'Queue: ' + debugState.queueSize + ' pending';
  document.getElementById('dbg-decrypt').textContent =
    'Last Decrypt: ' + debugState.lastDecrypt;
  document.getElementById('dbg-socket').textContent =
    'Socket: ' + (state.socket
      ? (state.socket.connected ? '🟢 connected' : '🔴 disconnected')
      : '—');
}

// Auto-refresh every second in dev mode
if (DEV_MODE) setInterval(updateDebugPanel, 1000);

// ─── STATE ────────────────────────────────────────────────
const state = {
  socket: null,
  username: '',
  tag: '',
  display: '',        // "username#tag" — the canonical identity string
  uid: '',            // session-only device ID — never persisted to disk
  currentChat: 'global',
  users: [],
  chatMessages: { global: [] },
  typingTimers: {},
  typingUsers: {},
  unread: {},
  mutedUsers: new Set(),   // display strings the local user has muted
  currentRoom: null,       // room_id of the active room (null = global/DM)
  roomList: [],            // cached list of public rooms from server
  mediaRecorder: null,
  audioChunks: [],
  recordTimer: null,
  recordSeconds: 0,
  peerConnection: null,
  localStream: null,
  callTarget: null,
  callType: null,
  muted: false,
  camOff: false,
  callState: 'idle',
  callTimeout: null,
  iceCandidateBuffer: [],
  // ── E2E Encryption ──────────────────────────────────────────────
  myKeyPair: null,
  myPublicKeyJwk: null,
  peerPublicKeys: {},
  sharedSecrets: {},
  roomKeys: {},        // room_id -> CryptoKey (AES-GCM, session-only)
  currentRoomName: '', // display name of the active room (for header fallback)
  isServerAdmin: false, // set to true if admin password was correct on login
  // ── Reliability ─────────────────────────────────────────────────
  pendingDecrypt: {},  // room_id -> [msg, ...] buffered until key arrives
  msgStatus: {},       // tempId -> 'sending'|'delivered'|'seen'
  tempIdMap: {},       // tempId -> DOM element id (for status updates)
  offlineQueue: [],    // messages queued while disconnected
  preJoinQueue: [],    // messages that arrived before identity was confirmed
  // ── Reply-to ────────────────────────────────────────────────────
  replyTo: null,       // {msg_id, from, text} — message being replied to
  // ── Settings ────────────────────────────────────────────────────
  soundMuted: false,   // mute notification sounds
  serverPassword: '',  // server join password (if required)
};

// ─── E2E ENCRYPTION ───────────────────────────────────────────────
const E2E = {
  /** Generate our ECDH key pair on login */
  async generateKeys() {
    state.myKeyPair = await crypto.subtle.generateKey(
      { name: 'ECDH', namedCurve: 'P-256' },
      true,
      ['deriveKey']
    );
    state.myPublicKeyJwk = await crypto.subtle.exportKey('jwk', state.myKeyPair.publicKey);
    return state.myPublicKeyJwk;
  },

  /** Import a peer's JWK public key */
  async importPeerKey(jwk) {
    return crypto.subtle.importKey(
      'jwk', jwk,
      { name: 'ECDH', namedCurve: 'P-256' },
      true,
      []
    );
  },

  /** Derive a shared AES-GCM key from our private key + peer's public key */
  async deriveSharedKey(peerPublicKey) {
    return crypto.subtle.deriveKey(
      { name: 'ECDH', public: peerPublicKey },
      state.myKeyPair.privateKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  },

  /** Get (or derive) the shared key for a peer */
  async getSharedKey(username) {
    if (state.sharedSecrets[username]) return state.sharedSecrets[username];
    const peerKey = state.peerPublicKeys[username];
    if (!peerKey) return null;
    const key = await E2E.deriveSharedKey(peerKey);
    state.sharedSecrets[username] = key;
    return key;
  },

  /** Encrypt a plaintext string for a peer. Returns base64(iv + ciphertext) */
  async encrypt(plaintext, username) {
    const key = await E2E.getSharedKey(username);
    if (!key) return null;
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(plaintext);
    const cipherBuf = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded);
    // Prepend IV to ciphertext
    const combined = new Uint8Array(iv.byteLength + cipherBuf.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(cipherBuf), iv.byteLength);
    return btoa(String.fromCharCode(...combined));
  },

  /** Decrypt a base64(iv + ciphertext) string from a peer */
  async decrypt(b64, username) {
    const key = await E2E.getSharedKey(username);
    if (!key) return null;
    try {
      const combined = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const iv = combined.slice(0, 12);
      const cipherBuf = combined.slice(12);
      const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, cipherBuf);
      return new TextDecoder().decode(plainBuf);
    } catch {
      return null; // decryption failed (wrong key or tampered)
    }
  },

  /** Register a peer's public key, derive shared secret immediately */
  async registerPeerKey(username, jwk) {
    if (state.peerPublicKeys[username]) return; // already have it
    const pubKey = await E2E.importPeerKey(jwk);
    state.peerPublicKeys[username] = pubKey;
    // Pre-derive shared key
    const shared = await E2E.deriveSharedKey(pubKey);
    state.sharedSecrets[username] = shared;
    console.log(`[E2E] Shared key derived with ${username}`);
  },

  // ── Room session key methods ─────────────────────────────────────────

  /** Generate a fresh AES-GCM-256 session key for a room */
  async generateRoomKey(roomId) {
    const key = await crypto.subtle.generateKey(
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );
    state.roomKeys[roomId] = key;
    return key;
  },

  /** Export a room key as JWK for server relay */
  async exportRoomKey(roomId) {
    const key = state.roomKeys[roomId];
    if (!key) return null;
    return crypto.subtle.exportKey('jwk', key);
  },

  /** Import a JWK room key received from the server */
  async importRoomKey(roomId, jwk) {
    const key = await crypto.subtle.importKey(
      'jwk', jwk,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
    state.roomKeys[roomId] = key;
    console.log(`[E2E] Room key imported for ${roomId}`);
    // Update debug state
    debugState.hasKey = true;
    debugState.roomId = roomId;
    debugState.queueSize = (state.pendingDecrypt[roomId] || []).length;
    updateDebugPanel();

    // Compute and display fingerprint for manual verification
    try {
      const raw = new TextEncoder().encode(JSON.stringify(jwk));
      const hash = await crypto.subtle.digest('SHA-256', raw);
      const hex = Array.from(new Uint8Array(hash))
        .map(b => b.toString(16).padStart(2, '0').toUpperCase())
        .join('');
      // Format as pairs: A1:B2:C3...
      const fp = hex.match(/.{2}/g).slice(0, 8).join(':');
      state.roomKeyFingerprint = fp;
      const fpEl = document.getElementById('room-key-fingerprint');
      if (fpEl) fpEl.textContent = fp;
    } catch (_) { }

    // Flush any messages that arrived before the key was ready
    const pending = state.pendingDecrypt[roomId] || [];
    delete state.pendingDecrypt[roomId];
    if (pending.length) {
      // Remove placeholder DOM elements and cached placeholder entries
      const chatArr = state.chatMessages[roomId];
      if (chatArr) {
        // Strip out all _pending placeholders for this room
        const toRemove = chatArr.filter(m => m._pending);
        toRemove.forEach(m => {
          if (m.msg_id) {
            const el = document.querySelector(`[data-msg-id="${m.msg_id}"]`);
            if (el) el.remove();
          }
        });
        state.chatMessages[roomId] = chatArr.filter(m => !m._pending);
      }
      // Re-render each buffered message now that the key is available
      for (const msg of pending) {
        await addMessage(msg, true);
      }
      console.log(`[E2E] Flushed ${pending.length} buffered message(s) for room ${roomId}`);
    }
  },

  /** Encrypt plaintext for a room. Returns base64(iv + ciphertext) */
  async encryptRoom(plaintext, roomId) {
    const key = state.roomKeys[roomId];
    if (!key) {
      console.warn(`[E2E] No room key for ${roomId} — cannot encrypt`);
      return null;
    }
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(plaintext);
    const cipherBuf = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded);
    const combined = new Uint8Array(iv.byteLength + cipherBuf.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(cipherBuf), iv.byteLength);
    return btoa(String.fromCharCode(...combined));
  },

  /** Decrypt a base64(iv + ciphertext) room message */
  async decryptRoom(b64, roomId) {
    const key = state.roomKeys[roomId];
    if (!key) {
      console.warn(`[E2E] No room key for ${roomId} — cannot decrypt`);
      return null;
    }
    try {
      const combined = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const iv = combined.slice(0, 12);
      const cipherBuf = combined.slice(12);
      const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, cipherBuf);
      return new TextDecoder().decode(plainBuf);
    } catch (err) {
      console.error(`[E2E] Room decrypt failed for ${roomId}:`, err);
      return null;
    }
  },
};

document.getElementById('username-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('password-input').focus();
});
document.getElementById('password-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') doLogin();
});

function toggleAdminField() {
  const wrap = document.getElementById('admin-field-wrap');
  const t = document.getElementById('admin-toggle');
  const f = document.getElementById('admin-password-input');
  if (wrap.style.display === 'none') {
    wrap.style.display = 'block';
    f.focus();
    t.style.opacity = '1';
    t.style.color = 'gold';
    t.textContent = '🔑 Admin';
  } else {
    wrap.style.display = 'none';
    f.value = '';
    t.style.opacity = '0.4';
    t.style.color = 'var(--text-muted)';
    t.textContent = '· · ·';
  }
}

// Ctrl+Shift+A keyboard shortcut to reveal admin field
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.shiftKey && e.key === 'A') {
    const loginScreen = document.getElementById('login-screen');
    if (loginScreen && loginScreen.style.display !== 'none') {
      e.preventDefault();
      toggleAdminField();
    }
  }
});

document.getElementById('admin-password-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') doLogin();
  if (e.key === 'Escape') toggleAdminField();
});

// ─── LOGIN ────────────────────────────────────────────────
async function doLogin() {
  const name = document.getElementById('username-input').value.trim();
  if (!name) { alert('Please enter a name'); return; }
  state.username = name;
  state.serverPassword = document.getElementById('admin-password-input').value;

  // Generate a session-only UID — never stored to disk or browser storage.
  // Tag will reset on page refresh (ephemeral by design).
  const uid = crypto.randomUUID
    ? crypto.randomUUID()
    : Array.from(crypto.getRandomValues(new Uint8Array(16)))
      .map(b => b.toString(16).padStart(2, '0')).join('');
  state.uid = uid;

  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
  document.getElementById('active-chat').style.display = 'flex';
  document.getElementById('chat-placeholder').style.display = 'none';

  // Set avatar
  const color = stringToColor(name);
  document.getElementById('my-avatar').style.background = color;
  document.getElementById('my-avatar').textContent = name[0].toUpperCase();
  document.getElementById('my-name').textContent = name;

  // Generate E2E key pair before connecting
  await E2E.generateKeys();

  connectSocket();
  switchChat('global');
}

// ─── SOCKET ────────────────────────────────────────────────
function connectSocket() {
  state.socket = io({
    reconnection: true,
    reconnectionAttempts: 10,          // cap — prevents infinite battery drain
    reconnectionDelay: 500,
    reconnectionDelayMax: 5000,        // exponential backoff ceiling
  });
  const s = state.socket;

  // Guard: prevents duplicate room rejoin when connect fires multiple times
  let _hasRejoined = false;

  // ── Connection state UI ───────────────────────────────────────────────
  function setConnBanner(text, bg, color) {
    const b = document.getElementById('conn-banner');
    if (!b) return;
    b.textContent = text;
    b.style.background = bg;
    b.style.color = color;
    b.style.display = text ? 'block' : 'none';
    document.body.classList.toggle('conn-banner-visible', !!text);
  }

  s.on('connect', () => {
    setConnBanner('', '', '');   // hide banner — connected
    debugState.connected = true;
    debugState.userId = state.display || state.username;
    updateDebugPanel();
    // Re-join with identity on every connect (handles reconnects too)
    s.emit('join', {
      username: state.username,
      uid: state.uid,
      publicKey: state.myPublicKeyJwk,
      server_password: state.serverPassword || '',
    });
    // Rejoin room on every connect cycle (disconnect resets _hasRejoined)
    if (state.currentRoom && !_hasRejoined) {
      s.emit('room:join', { room_id: state.currentRoom });
      _hasRejoined = true;
    }
    // Re-upload room key if we have it, so other members get it after reconnect
    if (state.currentRoom && state.roomKeys[state.currentRoom]) {
      E2E.exportRoomKey(state.currentRoom).then(jwk => {
        if (jwk) s.emit('room:key', { room_id: state.currentRoom, key: jwk });
      });
    }
    // If we're in a room but lost the key (server restarted),
    // room:joined from the rejoin above will deliver the key back.
    // Flush offline message queue
    if (state.offlineQueue.length) {
      const queued = [...state.offlineQueue];
      state.offlineQueue = [];
      queued.forEach(payload => {
        s.emit('send_message', payload);
      });
      showToast(`📤 Sent ${queued.length} queued message${queued.length > 1 ? 's' : ''}`);
    }
  });

  s.on('disconnect', () => {
    _hasRejoined = false;   // reset so next connect can rejoin
    debugState.connected = false;
    updateDebugPanel();
    setConnBanner('🔴 Disconnected — reconnecting…', '#1a0a0a', '#ff4455');
  });

  s.on('reconnecting', (attempt) => {
    setConnBanner(`🟡 Reconnecting… (${attempt}/10)`, '#1a1500', '#f0b429');
  });

  s.on('reconnect', () => {
    setConnBanner('🟢 Reconnected', '#0a1a0f', '#00ff88');
    setTimeout(() => setConnBanner('', '', ''), 2000);
  });

  s.on('reconnect_failed', () => {
    // All 10 attempts exhausted — show a manual "Tap to reconnect" button
    const b = document.getElementById('conn-banner');
    if (b) {
      b.innerHTML = '🔴 Connection lost. <button onclick="state.socket.connect()" ' +
        'style="margin-left:10px;padding:3px 10px;border-radius:8px;' +
        'background:#00ff88;color:#0a0e13;border:none;cursor:pointer;font-weight:700;">' +
        'Tap to reconnect</button>';
      b.style.background = '#1a0a0a';
      b.style.color = '#ff4455';
      b.style.display = 'block';
      document.body.classList.add('conn-banner-visible');
    }
  });

  s.on('joined', data => {
    // Server confirms identity with tag
    state.tag = data.tag;
    state.display = data.display;   // "username#tag"
    state.isServerAdmin = !!data.is_server_admin;
    if (data.username !== state.username) {
      state.username = data.username;
    }
    document.getElementById('my-name').textContent = state.display;
    const color = stringToColor(state.username);
    document.getElementById('my-avatar').style.background = color;
    document.getElementById('my-avatar').textContent = state.username[0].toUpperCase();
    // Show subtle admin badge on avatar if admin
    if (state.isServerAdmin) {
      document.getElementById('my-avatar').title = '👑 Server Admin';
      document.getElementById('my-avatar').style.boxShadow = '0 0 0 2px gold';
    }
    // Update debug state with confirmed identity
    debugState.userId = state.display;
    updateDebugPanel();

    // Flush any messages that arrived before identity was confirmed
    if (state.preJoinQueue.length) {
      const queued = [...state.preJoinQueue];
      state.preJoinQueue = [];
      queued.forEach(msg => {
        addMessage(msg, true);
        if (msg.from !== state.display) {
          notifyNewMessage(msg.from, msg.text || msg.name || '[File]');
        }
      });
    }
  });

  // Receive a peer's public key
  s.on('peer_key', async data => {
    if (data.username && data.publicKey) {
      await E2E.registerPeerKey(data.username, data.publicKey);
    }
  });

  // Receive all current peers' public keys on join
  s.on('all_keys', async keys => {
    for (const [display, jwk] of Object.entries(keys)) {
      if (display !== state.display) {
        await E2E.registerPeerKey(display, jwk);
      }
    }
  });

  // Spam cooldown notification
  s.on('cooldown', data => {
    const input = document.getElementById('msg-input');
    input.disabled = true;
    input.placeholder = `⏳ Slow down! Wait ${data.seconds}s…`;
    input.style.opacity = '0.5';
    setTimeout(() => {
      input.disabled = false;
      input.placeholder = 'Type a message';
      input.style.opacity = '';
    }, data.seconds * 1000);
  });

  // Vote-to-hide feedback
  s.on('vote_count', data => {
    const el = document.querySelector(`[data-msg-id="${data.msg_id}"] .vote-count`);
    if (el) el.textContent = `${data.votes}/${data.needed} votes to hide`;
  });

  // Hide a message that reached the vote threshold
  s.on('hide_message', data => {
    const el = document.querySelector(`[data-msg-id="${data.msg_id}"]`);
    if (el) {
      el.style.opacity = '0.3';
      el.style.filter = 'blur(3px)';
      el.title = 'Hidden by community vote';
      el.onclick = () => {
        el.style.opacity = '';
        el.style.filter = '';
        el.onclick = null;
      };
    }
  });

  s.on('user_list', users => {
    state.users = users;
    renderUserList(users);
  });

  s.on('message_history', msgs => {
    msgs.forEach(m => addMessage(m, false)); // addMessage is async but fire-and-forget is fine for history
  });

  s.on('new_message', msg => {
    // If identity not yet confirmed (reconnect race), buffer the message
    if (!state.display) {
      state.preJoinQueue.push(msg);
      return;
    }
    addMessage(msg, true);

    // Notify about new message
    if (msg.from !== state.display) {
      notifyNewMessage(msg.from, msg.text || msg.name || '[File]');
    }

    // Unread badge
    if (msg.to === 'global' && state.currentChat !== 'global') {
      incrementUnread('global');
    } else if (msg.to !== 'global') {
      const other = msg.from === state.display ? msg.to : msg.from;
      if (other !== state.currentChat) {
        incrementUnread(other);
      }
    }
  });

  s.on('system_message', msg => {
    const div = document.createElement('div');
    div.className = 'system-msg';
    div.textContent = msg.text;
    document.getElementById('messages').appendChild(div);
    scrollToBottom();
  });

  // ── Message edit / delete / seen ──────────────────────────────────────
  s.on('message:edited', async data => {
    const { msg_id, text, encrypted, to } = data;
    // Update in chatMessages store
    for (const arr of Object.values(state.chatMessages)) {
      const m = arr.find(m => m.msg_id === msg_id);
      if (m) {
        if (encrypted) {
          // Decrypt the new ciphertext
          let plain = text;
          if (to && state.roomKeys[to]) {
            plain = await E2E.decryptRoom(encrypted, to) || '🔒 [decryption failed]';
          } else if (to && to !== 'global') {
            const peer = m.from === state.display ? to : m.from;
            plain = await E2E.decrypt(encrypted, peer) || '🔒 [decryption failed]';
          }
          m.text = plain;
        } else {
          m.text = text;
        }
        m.edited = true;
        break;
      }
    }
    // Update DOM
    const wrapper = document.querySelector(`[data-msg-id="${msg_id}"]`);
    if (wrapper) {
      const textEl = wrapper.querySelector('.bubble-text');
      if (textEl) {
        textEl.textContent = data._plaintext || text;
        // Add edited label if not already there
        if (!wrapper.querySelector('.edited-label')) {
          const label = document.createElement('span');
          label.className = 'edited-label';
          label.textContent = ' (edited)';
          textEl.appendChild(label);
        }
      }
    }
  });

  s.on('message:deleted', data => {
    const { msg_id } = data;
    // Soft-delete in store
    for (const arr of Object.values(state.chatMessages)) {
      const m = arr.find(m => m.msg_id === msg_id);
      if (m) { m.deleted = true; m.text = '🗑 This message was deleted'; break; }
    }
    // Update DOM
    const wrapper = document.querySelector(`[data-msg-id="${msg_id}"]`);
    if (wrapper) {
      const textEl = wrapper.querySelector('.bubble-text');
      if (textEl) {
        textEl.textContent = '🗑 This message was deleted';
        textEl.style.opacity = '0.5';
        textEl.style.fontStyle = 'italic';
      }
      // Remove action buttons
      wrapper.querySelectorAll('.msg-action-btn').forEach(b => b.remove());
    }
  });

  s.on('message:seen', data => {
    // data.msg_ids = array of msg_ids the peer has seen
    // data.by = who saw them
    if (!Array.isArray(data.msg_ids)) return;
    data.msg_ids.forEach(id => {
      if (state.msgStatus[id] !== 'seen') {
        state.msgStatus[id] = 'seen';
        _updateMsgStatus(id, '✅✅');
      }
    });
  });

  s.on('typing', data => {
    if (data.username === state.display) return;   // ignore own typing echo
    const chatId = data.to === 'global' ? 'global' : data.username;
    if (!state.typingUsers[chatId]) state.typingUsers[chatId] = new Set();
    state.typingUsers[chatId].add(data.username);
    renderTyping();
    clearTimeout(state.typingTimers[data.username]);
    state.typingTimers[data.username] = setTimeout(() => {
      if (state.typingUsers[chatId]) state.typingUsers[chatId].delete(data.username);
      renderTyping();
    }, 2000);
  });

  s.on('stop_typing', data => {
    const chatId = data.to === 'global' ? 'global' : data.username;
    if (state.typingUsers[chatId]) state.typingUsers[chatId].delete(data.username);
    renderTyping();
  });

  s.on('webrtc_signal', handleSignal);

  // ── Server error messages ─────────────────────────────────────────────
  s.on('error', data => {
    const code = data.code ? `[${data.code}] ` : '';
    showToast('⚠️ ' + code + (data.message || 'An error occurred'));

    // Server password required — show the field and prompt user
    if (data.code === 'AUTH_FAILED') {
      // Disconnect and go back to login
      s.disconnect();
      document.getElementById('app').style.display = 'none';
      document.getElementById('login-screen').style.display = 'flex';
      const pwField = document.getElementById('server-password-input');
      pwField.placeholder = 'Server password (required)';
      pwField.focus();
      alert('⚠️ Wrong server password. Please enter the correct password.');
    }
  });

  // ── Presence updates ──────────────────────────────────────────────────
  s.on('user:presence', data => {
    // Update the presence dot colour in the user list
    const item = document.getElementById('chat-item-' + CSS.escape(data.display));
    if (item) {
      const dot = item.querySelector('.online-dot');
      if (dot) {
        const colours = {
          'active': 'var(--accent)',
          'idle': '#f0b429',
          'typing': 'var(--accent)',
          'in-call': '#ff4455',
          'recording': '#ff4455',
          'uploading': '#53bdeb',
        };
        dot.style.background = colours[data.state] || 'var(--accent)';
        dot.title = data.state;
      }
    }
  });

  // ── Persona switch announcement ───────────────────────────────────────
  s.on('persona_switched', data => {
    // Update any chat items that used the old display name
    const oldItem = document.getElementById('chat-item-' + CSS.escape(data.old));
    if (oldItem) {
      oldItem.id = 'chat-item-' + CSS.escape(data.new);
      const nameSpan = oldItem.querySelector('.chat-item-name span');
      if (nameSpan) nameSpan.textContent = data.new;
    }
    // If we were chatting with this person, update the header
    if (state.currentChat === data.old) {
      state.currentChat = data.new;
      document.getElementById('header-name').textContent = data.new;
    }
  });

  // ── Room events ───────────────────────────────────────────────────────
  s.on('room:created', async data => {
    state.currentRoom = data.room_id;
    state.currentRoomName = data.name;

    // Switch the chat view to this room immediately
    state.currentChat = data.room_id;
    if (!state.chatMessages[data.room_id]) state.chatMessages[data.room_id] = [];
    document.getElementById('chat-placeholder').style.display = 'none';
    document.getElementById('active-chat').style.display = 'flex';
    document.getElementById('messages').innerHTML = '';
    document.getElementById('header-name').textContent = data.name;
    document.getElementById('header-status').textContent = '1 member · 🔒 encrypted';
    const av = document.getElementById('header-avatar');
    av.style.background = '#1a3a5c'; av.style.fontSize = '18px'; av.textContent = '🏠';
    const ha = document.querySelector('.header-actions');
    if (ha) ha.style.display = 'flex';
    document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));

    showToast(`Room "${data.name}" created`);

    // For private rooms, show the persistent room ID banner
    if (data.visibility === 'private') {
      showRoomIdBanner(data.room_id);
      setTimeout(() => {
        showToast(`🔑 Room ID: ${data.room_id} — share this to invite people`);
      }, 1500);
    } else {
      hideRoomIdBanner();
    }

    // Generate a session key for this room and upload it to the server.
    try {
      await E2E.generateRoomKey(data.room_id);
      const jwk = await E2E.exportRoomKey(data.room_id);
      console.log(`[E2E] Room key generated for ${data.room_id}, uploading to server`);
      s.emit('room:key', { room_id: data.room_id, key: jwk });
    } catch (err) {
      console.error('[E2E] Room key generation failed:', err);
    }

    s.emit('room:list', {});
  });

  s.on('room:joined', async data => {
    // Set currentRoom FIRST so incoming messages during key import
    // are correctly identified as room messages and buffered in pendingDecrypt
    state.currentRoom = data.room_id;
    state.currentRoomName = data.name;
    state.currentChat = data.room_id;

    if (!state.chatMessages[data.room_id]) state.chatMessages[data.room_id] = [];

    // Import the room session key BEFORE rendering history.
    // importRoomKey will flush pendingDecrypt automatically when done.
    if (data.session_key) {
      try {
        await E2E.importRoomKey(data.room_id, data.session_key);
      } catch (err) {
        console.error('[E2E] Failed to import room key:', err);
      }
    }
    // If no key in payload, it will arrive via room:key event shortly.

    // Switch the chat view to this room
    document.getElementById('chat-placeholder').style.display = 'none';
    document.getElementById('active-chat').style.display = 'flex';
    document.getElementById('messages').innerHTML = '';
    document.getElementById('header-name').textContent = data.name;
    document.getElementById('header-status').textContent =
      `${(data.members || []).length} members · 🔒 encrypted`;
    const av = document.getElementById('header-avatar');
    av.style.background = '#1a3a5c'; av.style.fontSize = '18px'; av.textContent = '🏠';
    const ha = document.querySelector('.header-actions');
    if (ha) ha.style.display = 'flex';
    document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
    const roomItem = document.getElementById('chat-item-room-' + data.room_id);
    if (roomItem) roomItem.classList.add('active');

    // Load room history
    if (data.history && data.history.length) {
      data.history.forEach(m => addMessage(m, false));
    }
    scrollToBottom();
    showToast(`Joined room "${data.name}"`);
    if (data.is_frozen) {
      showToast('⚠️ This room is frozen — messages are disabled');
    }
    // Show room ID banner for private rooms
    if (data.visibility === 'private') {
      showRoomIdBanner(data.room_id);
    } else {
      hideRoomIdBanner();
    }
  });

  // Receive a room session key distributed after we joined
  s.on('room:key', async data => {
    if (data.room_id && data.key) {
      console.log(`[E2E] Received room:key event for ${data.room_id}`);
      try {
        await E2E.importRoomKey(data.room_id, data.key);
      } catch (err) {
        console.error('[E2E] Failed to import late room key:', err);
      }
    }
  });

  s.on('room:left', () => {
    if (state.currentRoom) {
      delete state.roomKeys[state.currentRoom];
    }
    state.currentRoom = null;
    state.currentRoomName = '';
    hideRoomIdBanner();
    switchChat('global');
  });

  s.on('room:list', rooms => {
    // Store for the room browser UI
    state.roomList = rooms;
    renderRoomList(rooms);
  });

  s.on('room:members', members => {
    // Update member count in header if we're in a room
    if (state.currentRoom) {
      const statusEl = document.getElementById('header-status');
      if (statusEl) statusEl.textContent = `${members.length} members`;
    }
  });

  s.on('room:frozen', data => {
    if (data.room_id === state.currentRoom) {
      const input = document.getElementById('msg-input');
      const sendBtn = document.querySelector('.send-btn');
      if (data.is_frozen) {
        if (input) { input.disabled = true; input.placeholder = '🔒 Room is frozen'; }
        if (sendBtn) sendBtn.disabled = true;
        showToast('🔒 Room frozen by admin');
      } else {
        if (input) { input.disabled = false; input.placeholder = 'Type a message'; }
        if (sendBtn) sendBtn.disabled = false;
        showToast('✅ Room unfrozen');
      }
    }
  });

  s.on('room:deleted', data => {
    if (data.room_id === state.currentRoom) {
      delete state.roomKeys[data.room_id];
      state.currentRoom = null;
      state.currentRoomName = '';
      showToast('Room was deleted (empty for too long)');
      switchChat('global');
    }
  });

  s.on('admin:kicked', data => {
    if (data.room_id === state.currentRoom) {
      delete state.roomKeys[data.room_id];
      state.currentRoom = null;
      state.currentRoomName = '';
      showToast('⚠️ You were removed from the room by an admin');
      switchChat('global');
    }
  });

  // ── Room call events ──────────────────────────────────────────────────

  s.on('room:incoming_call', data => {
    // Another room member started a call — show a join notification
    const callType = data.call_type === 'video' ? '📹 video' : '📞 voice';
    notifyIncomingCall(data.from, data.call_type);

    // Use a dedicated call-banner element so it never conflicts with the
    // shared toast queue (knock toasts, message toasts, etc.)
    let banner = document.getElementById('call-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'call-banner';
      banner.style.cssText = [
        'position:fixed', 'top:16px', 'left:50%', 'transform:translateX(-50%)',
        'background:#0d2a1f', 'border:1.5px solid var(--accent)',
        'color:var(--text-primary)', 'padding:10px 18px', 'border-radius:12px',
        'z-index:9999', 'display:flex', 'align-items:center', 'gap:8px',
        'box-shadow:0 4px 24px rgba(0,255,136,0.25)', 'font-size:14px',
        'max-width:90vw', 'opacity:0', 'transition:opacity 0.2s',
      ].join(';');
      document.body.appendChild(banner);
    }

    // Clear any previous call-banner timer
    if (banner._dismissTimer) clearTimeout(banner._dismissTimer);

    banner.innerHTML = '';
    const msg = document.createElement('span');
    msg.textContent = `${data.from} started a ${callType} call in "${data.room_name}" `;
    const btn = document.createElement('button');
    btn.textContent = 'Join';
    btn.style.cssText = 'padding:4px 12px;border-radius:8px;' +
      'background:var(--accent);color:#0a0e13;border:none;cursor:pointer;font-weight:700;flex-shrink:0;';
    btn.onclick = () => {
      banner.style.opacity = '0';
      setTimeout(() => { banner.style.display = 'none'; }, 200);
      if (state.callState !== 'idle') {
        showToast('⚠️ Already in a call — end it first.');
        return;
      }
      startDmCall(data.from, data.call_type);
    };
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = 'padding:2px 8px;border-radius:6px;background:transparent;' +
      'color:var(--text-secondary);border:none;cursor:pointer;font-size:12px;flex-shrink:0;';
    closeBtn.onclick = () => {
      banner.style.opacity = '0';
      setTimeout(() => { banner.style.display = 'none'; }, 200);
    };
    banner.appendChild(msg);
    banner.appendChild(btn);
    banner.appendChild(closeBtn);
    banner.style.display = 'flex';
    requestAnimationFrame(() => { banner.style.opacity = '1'; });

    // Auto-dismiss after 30s
    banner._dismissTimer = setTimeout(() => {
      banner.style.opacity = '0';
      setTimeout(() => { banner.style.display = 'none'; }, 200);
    }, 30000);
  });

  // ── Room knock events ─────────────────────────────────────────────────

  s.on('room:knock', data => {
    // Admin receives a knock — show approve/deny toast
    const toastEl = document.getElementById('toast');
    toastEl.innerHTML = '';
    const msg = document.createElement('span');
    msg.textContent = `${data.display} wants to join `;
    const approveBtn = document.createElement('button');
    approveBtn.textContent = '✓ Approve';
    approveBtn.style.cssText = 'margin-left:6px;padding:3px 10px;border-radius:8px;' +
      'background:var(--accent);color:#0a0e13;border:none;cursor:pointer;font-weight:700;';
    approveBtn.onclick = () => {
      state.socket.emit('room:knock_approve', { room_id: data.room_id, sid: data.sid });
      toastEl.classList.remove('show');
    };
    const denyBtn = document.createElement('button');
    denyBtn.textContent = '✕ Deny';
    denyBtn.style.cssText = 'margin-left:4px;padding:3px 10px;border-radius:8px;' +
      'background:rgba(255,68,85,0.2);color:var(--danger);border:1px solid var(--danger);' +
      'cursor:pointer;font-weight:700;';
    denyBtn.onclick = () => {
      state.socket.emit('room:knock_deny', { room_id: data.room_id, sid: data.sid });
      toastEl.classList.remove('show');
    };
    toastEl.appendChild(msg);
    toastEl.appendChild(approveBtn);
    toastEl.appendChild(denyBtn);
    toastEl.classList.add('show');
    setTimeout(() => toastEl.classList.remove('show'), 60000);
  });

  s.on('room:knock_pending', data => {
    showToast(`⏳ Waiting for admin approval to join "${data.name}"…`);
  });

  s.on('room:knock_denied', data => {
    showToast('❌ Your request to join the room was denied.');
  });

  // Token-based join — server approved the knock and issued a token
  s.on('room:join_approved', data => {
    showToast('✅ Approved! Joining room…');
    // Present the token to complete the join
    s.emit('room:join_with_token', {
      token: data.token,
      room_id: data.room_id,
    });
  });

  // Request notification permission
  requestNotificationPermission();
}

// ─── NOTIFICATIONS ────────────────────────────────────────

// Shared AudioContext — created once, reused for every sound.
// Lazy-initialised on first user gesture to satisfy autoplay policy.
let _audioCtx = null;
function getAudioCtx() {
  if (!_audioCtx || _audioCtx.state === 'closed') {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  // Resume if suspended (browser autoplay policy)
  if (_audioCtx.state === 'suspended') _audioCtx.resume();
  return _audioCtx;
}

// Per-sender throttle: suppress repeat browser notifications within this window (ms).
const _notifyThrottle = new Map();   // tag -> timestamp
const NOTIFY_THROTTLE_MS = 3000;

// Active Notification objects keyed by tag so we can close/replace them.
const _activeNotifs = new Map();

function requestNotificationPermission() {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'default') {
    Notification.requestPermission().then(perm => {
      if (perm === 'granted') {
        showToast('🔔 Desktop notifications enabled');
      }
    });
  }
}

/**
 * showNotification(title, options)
 *
 * options:
 *   body        – notification body text
 *   tag         – unique tag; replaces any existing notification with the same tag
 *   soundType   – 'beep' (default) | 'ring' | 'none'
 *   requireInteraction – keep notification until user dismisses (calls)
 *   onClick     – callback when the notification is clicked
 *
 * Rules:
 *  • Never fires if the window is focused AND the relevant chat is active.
 *  • Browser notification is throttled per-tag to avoid spam.
 *  • Sound plays only when the window is not focused (browser handles its own sound).
 */
function showNotification(title, options = {}) {
  const tag = options.tag || 'chat-notification';
  const soundType = options.soundType ?? 'beep';
  const windowFocused = document.hasFocus();

  // ── Browser notification ──────────────────────────────────────────────
  if ('Notification' in window && Notification.permission === 'granted') {
    const now = Date.now();
    const lastSent = _notifyThrottle.get(tag) || 0;

    if (now - lastSent >= NOTIFY_THROTTLE_MS) {
      _notifyThrottle.set(tag, now);

      // Close any existing notification with the same tag before creating a new one
      const prev = _activeNotifs.get(tag);
      if (prev) { try { prev.close(); } catch (_) { } }

      const notif = new Notification(title, {
        icon: '/static/icon.svg',
        body: options.body || '',
        tag,
        requireInteraction: options.requireInteraction || false,
        silent: true,   // we handle sound ourselves to avoid double-audio
      });

      notif.onclick = () => {
        window.focus();
        if (typeof options.onClick === 'function') options.onClick();
        notif.close();
      };

      notif.onclose = () => {
        if (_activeNotifs.get(tag) === notif) _activeNotifs.delete(tag);
      };

      _activeNotifs.set(tag, notif);
    }
  }

  // ── Sound ─────────────────────────────────────────────────────────────
  // Only play sound when the window is not focused; focused window already
  // has the message appearing in the chat area.
  if (!windowFocused && soundType !== 'none' && !state.soundMuted) {
    if (soundType === 'ring') {
      playRingTone();
    } else {
      playNotificationSound();
    }
  }
}

function playNotificationSound() {
  try {
    const ctx = getAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.frequency.value = 880;
    osc.type = 'sine';

    const t = ctx.currentTime;
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.25, t + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.4);

    osc.start(t);
    osc.stop(t + 0.4);
  } catch (e) {
    console.warn('[Notification] Could not play sound:', e.message);
  }
}

// Stop an active ring tone early (e.g. call accepted/rejected).
let _ringStopFns = [];
function stopRingTone() {
  _ringStopFns.forEach(fn => { try { fn(); } catch (_) { } });
  _ringStopFns = [];
}

function playRingTone() {
  stopRingTone(); // cancel any previous ring
  try {
    const ctx = getAudioCtx();
    const oscillators = [];

    // Classic telephone double-ring pattern: RING-RING ... pause ... RING-RING
    // Each "ring" = two 0.4s bursts separated by 0.2s gap; then 1.6s silence. Repeats 5×.
    const burst = 0.4;   // duration of one tone burst
    const gap = 0.2;   // gap between the two bursts in a double-ring
    const pause = 1.6;   // silence between double-rings
    const cycle = burst + gap + burst + pause; // 2.6 s per cycle
    const repeats = 5;

    function makeBurst(startTime) {
      // Layer three harmonics for a warm, telephone-like timbre
      const freqs = [
        { f: 480, vol: 0.22, type: 'sine' },
        { f: 960, vol: 0.10, type: 'sine' },
        { f: 1440, vol: 0.05, type: 'triangle' },
      ];
      freqs.forEach(({ f, vol, type }) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = f;
        osc.type = type;
        // Quick attack, sustain, quick release
        gain.gain.setValueAtTime(0, startTime);
        gain.gain.linearRampToValueAtTime(vol, startTime + 0.02);
        gain.gain.setValueAtTime(vol, startTime + burst - 0.04);
        gain.gain.linearRampToValueAtTime(0, startTime + burst);
        osc.start(startTime);
        osc.stop(startTime + burst);
        oscillators.push(osc);
      });
    }

    for (let i = 0; i < repeats; i++) {
      const base = ctx.currentTime + i * cycle;
      makeBurst(base);               // first burst
      makeBurst(base + burst + gap); // second burst (double-ring)
    }

    _ringStopFns.push(() => {
      oscillators.forEach(o => { try { o.stop(); } catch (_) { } });
    });
  } catch (e) {
    console.warn('[Notification] Could not play ring tone:', e.message);
  }
}

// Per-sender message notification throttle (separate from the browser-notif throttle).
const _msgNotifyTimers = new Map();  // chatId -> timer handle

function notifyNewMessage(from, preview) {
  // Don't notify if this chat is currently active AND the window is focused
  const chatId = from === state.display ? 'global' : from;
  if (chatId === state.currentChat && document.hasFocus()) return;

  // Debounce: if multiple messages arrive quickly from the same sender,
  // only fire one notification after a short delay (shows latest preview).
  clearTimeout(_msgNotifyTimers.get(chatId));
  _msgNotifyTimers.set(chatId, setTimeout(() => {
    _msgNotifyTimers.delete(chatId);

    // Truncate preview safely (handles multi-byte / emoji)
    const maxLen = 60;
    const safePreview = [...preview].slice(0, maxLen).join('') +
      ([...preview].length > maxLen ? '…' : '');

    showNotification(`📨 ${from}`, {
      body: safePreview,
      tag: `msg-${chatId}`,
      soundType: 'beep',
      onClick: () => switchChat(chatId),
    });
  }, 400));
}

function notifyIncomingCall(from, callType) {
  const title = callType === 'video' ? '📹 Incoming video call' : '☎️ Incoming call';

  showNotification(title, {
    body: `${from} is calling…`,
    tag: `call-${from}`,
    requireInteraction: true,
    soundType: 'ring',
    onClick: () => {
      // Bring the call overlay into view
      document.getElementById('call-overlay')?.classList.add('active');
    },
  });
}

// ─── MESSAGES ─────────────────────────────────────────────
async function addMessage(msg, live) {
  // Decrypt encrypted messages
  if (msg.encrypted) {
    const isRoomMsg = msg.to && state.roomKeys[msg.to] !== undefined;
    // A message is a room target if:
    // 1. msg.to matches our current room, OR
    // 2. msg.to is an 8-char hex room ID format (even if key not yet loaded)
    const isRoomTarget = msg.to && (
      msg.to === state.currentRoom ||
      state.roomKeys[msg.to] !== undefined ||
      /^[0-9A-F]{8}$/i.test(msg.to)
    );

    if (isRoomMsg) {
      // Key available — decrypt now
      const plaintext = await E2E.decryptRoom(msg.encrypted, msg.to);
      msg = { ...msg, text: plaintext !== null ? plaintext : '🔒 [decryption failed]' };
      debugState.lastDecrypt = plaintext !== null ? '✅ Success' : '❌ Failed';
      updateDebugPanel();
    } else if (isRoomTarget && !isRoomMsg) {
      // Room message but key not yet available — buffer it
      if (!state.pendingDecrypt[msg.to]) state.pendingDecrypt[msg.to] = [];
      state.pendingDecrypt[msg.to].push(msg);
      // Show a placeholder
      const placeholder = { ...msg, text: '⏳ waiting for encryption key…', _pending: true };
      const chatId = msg.to;
      if (!state.chatMessages[chatId]) state.chatMessages[chatId] = [];
      state.chatMessages[chatId].push(placeholder);
      updatePreview(chatId, placeholder);
      if (chatId === state.currentChat) { renderMsg(placeholder); if (live) scrollToBottom(); }
      return;
    } else if (msg.to !== 'global') {
      // DM decryption
      const peer = msg.from === state.display ? msg.to : msg.from;
      const plaintext = await E2E.decrypt(msg.encrypted, peer);
      msg = { ...msg, text: plaintext !== null ? plaintext : '🔒 [encrypted — key not available]' };
    }
  }

  // Mark own messages as delivered when we receive them back from server.
  // The server echo has the real msg_id; our local copy used a tempId.
  // Find and update the local copy instead of adding a duplicate.
  if (msg.msg_id && msg.from === state.display && !msg._local) {
    // Look for a local temp message to replace
    const chatId2 = msg.to === 'global' ? 'global'
      : (msg.to === state.currentRoom || state.roomKeys[msg.to]) ? msg.to
        : (msg.from === state.display ? msg.to : msg.from);
    const msgs = state.chatMessages[chatId2] || [];
    const localIdx = msgs.findIndex(m => m._local && m.text === (msg._origText || msg.text));
    if (localIdx !== -1) {
      // Replace temp with real, update status tick
      const tempId = msgs[localIdx].msg_id;
      msgs[localIdx] = { ...msg, _origText: undefined };
      state.msgStatus[msg.msg_id] = 'delivered';
      _updateMsgStatus(tempId, '✅', msg.msg_id);
      return; // don't re-render
    }
    // No local copy found (e.g. history replay) — just mark delivered
    state.msgStatus[msg.msg_id] = 'delivered';
  }

  // Determine chatId: room messages use room_id as chatId
  // Room message: msg.to is a room_id (matches state.currentRoom or is in roomKeys)
  const isRoomMsg = msg.to && (msg.to === state.currentRoom || state.roomKeys[msg.to] !== undefined);
  const chatId = msg.to === 'global' ? 'global'
    : isRoomMsg ? msg.to
      : (msg.from === state.display ? msg.to : msg.from);

  if (!state.chatMessages[chatId]) state.chatMessages[chatId] = [];
  // Insert in sequence/timestamp order to handle out-of-order delivery
  const arr = state.chatMessages[chatId];
  // Use seq for room messages (more reliable), time for others
  const msgOrder = msg.seq !== undefined ? msg.seq : msg.time;
  const insertAt = arr.findIndex(m => {
    const mOrder = m.seq !== undefined ? m.seq : m.time;
    return mOrder > msgOrder;
  });
  if (insertAt === -1) {
    arr.push(msg);
  } else {
    arr.splice(insertAt, 0, msg);
  }

  // Update sidebar preview
  updatePreview(chatId, msg);

  // Only render to DOM if we're viewing this chat
  if (chatId === state.currentChat) {
    renderMsg(msg);
    if (live) scrollToBottom();
  }
}

function renderMsg(msg) {
  const isMe = msg.from === state.display;

  // Skip messages from muted users
  if (!isMe && state.mutedUsers.has(msg.from)) return;

  const wrapper = document.createElement('div');
  wrapper.className = 'msg-wrapper ' + (isMe ? 'me' : 'other');
  if (msg.msg_id) wrapper.dataset.msgId = msg.msg_id;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  // Sender name + tag + reputation (global chat and rooms, not DMs)
  const isRoomContext = msg.to && msg.to !== 'global' && state.roomKeys[msg.to] !== undefined;
  if (!isMe && (msg.to === 'global' || isRoomContext)) {
    const senderRow = document.createElement('div');
    senderRow.className = 'bubble-sender';
    senderRow.style.color = msg.color || '#25d366';

    const nameSpan = document.createElement('span');
    nameSpan.textContent = msg.from;   // already "username#tag"

    const repBadge = document.createElement('span');
    repBadge.className = 'rep-badge rep-' + (msg.reputation || 'New').toLowerCase();
    repBadge.textContent = msg.reputation || 'New';

    senderRow.appendChild(nameSpan);
    senderRow.appendChild(repBadge);
    bubble.appendChild(senderRow);
  }

  // Reply-to preview
  if (msg.reply_to) {
    const replyDiv = document.createElement('div');
    replyDiv.className = 'reply-preview';
    const orig = _findMsgById(msg.reply_to.msg_id);
    const origText = orig ? (orig.text || '[file]') : (msg.reply_to.text || '…');
    replyDiv.innerHTML = `<strong>${msg.reply_to.from || '?'}</strong>${_escapeHtml(origText.slice(0, 80))}`;
    replyDiv.onclick = () => _scrollToMsg(msg.reply_to.msg_id);
    bubble.appendChild(replyDiv);
  }

  // Content
  if (msg.deleted) {
    const text = document.createElement('div');
    text.className = 'bubble-text';
    text.textContent = '🗑 This message was deleted';
    text.style.opacity = '0.5';
    text.style.fontStyle = 'italic';
    bubble.appendChild(text);
  } else if (msg.type === 'text') {
    const text = document.createElement('div');
    text.className = 'bubble-text';
    text.textContent = msg.text;
    if (msg.edited) {
      const label = document.createElement('span');
      label.className = 'edited-label';
      label.textContent = ' (edited)';
      text.appendChild(label);
    }
    bubble.appendChild(text);
  } else if (msg.type === 'file') {
    const el = renderFileContent(msg);
    bubble.appendChild(el);
  } else {
    // Unknown message type — render a safe fallback
    const text = document.createElement('div');
    text.className = 'bubble-text';
    text.textContent = '[Unsupported message type]';
    bubble.appendChild(text);
  }

  // Time + status tick (own messages only)
  const time = document.createElement('div');
  time.className = 'bubble-time';
  if (isMe && msg.msg_id) {
    const status = state.msgStatus[msg.msg_id];
    const tick = status === 'seen' ? ' ✅✅' : (status === 'delivered' ? ' ✅' : ' ⏳');
    time.textContent = formatTime(msg.time) + tick;
    time.dataset.msgId = msg.msg_id;
    time.id = 'status-' + msg.msg_id;
  } else {
    time.textContent = formatTime(msg.time);
  }
  bubble.appendChild(time);

  // Vote-to-hide button (only on others' messages in global chat)
  if (!isMe && msg.msg_id && msg.to === 'global') {
    const voteBtn = document.createElement('button');
    voteBtn.className = 'vote-hide-btn';
    voteBtn.title = 'Vote to hide this message';
    voteBtn.textContent = '🚩';
    voteBtn.onclick = (e) => {
      e.stopPropagation();
      state.socket.emit('vote_hide', { msg_id: msg.msg_id });
      voteBtn.disabled = true;
      voteBtn.style.opacity = '0.4';
      // Show a small counter placeholder
      const counter = document.createElement('span');
      counter.className = 'vote-count';
      counter.textContent = '1/3 votes';
      bubble.appendChild(counter);
    };
    bubble.appendChild(voteBtn);

    // Mute user — long-press on mobile, right-click on desktop
    const senderRow = bubble.querySelector('.bubble-sender');
    if (senderRow) {
      senderRow.style.cursor = 'pointer';
      senderRow.title = 'Hold to mute this user';

      function _toggleMuteSender(e) {
        e.preventDefault();
        if (state.mutedUsers.has(msg.from)) {
          state.mutedUsers.delete(msg.from);
          showToast(`Unmuted ${msg.from}`);
        } else {
          state.mutedUsers.add(msg.from);
          showToast(`Muted ${msg.from} — their messages are now hidden`);
        }
      }

      // Desktop: right-click
      senderRow.addEventListener('contextmenu', _toggleMuteSender);
      // Mobile: long-press (500 ms)
      attachLongPress(senderRow, _toggleMuteSender);
    }
  }

  // Message action buttons: reply (all), edit/delete (own or admin)
  if (msg.msg_id && !msg.deleted && msg.type === 'text') {
    const actions = document.createElement('div');
    actions.className = 'msg-actions';

    // Reply button — available on all messages
    const replyBtn = document.createElement('button');
    replyBtn.className = 'msg-action-btn';
    replyBtn.title = 'Reply';
    replyBtn.textContent = '↩';
    replyBtn.onclick = () => startReply(msg);
    actions.appendChild(replyBtn);

    // Edit/delete — own messages only (or room admin)
    const isRoomAdmin = msg.to && state.currentRoom === msg.to &&
      state.socket && state.socket.connected;  // simplified; server enforces auth
    if (isMe) {
      const editBtn = document.createElement('button');
      editBtn.className = 'msg-action-btn';
      editBtn.title = 'Edit';
      editBtn.textContent = '✏️';
      editBtn.onclick = () => startEdit(msg);
      actions.appendChild(editBtn);

      const delBtn = document.createElement('button');
      delBtn.className = 'msg-action-btn';
      delBtn.title = 'Delete';
      delBtn.textContent = '🗑';
      delBtn.onclick = () => {
        if (confirm('Delete this message?')) {
          state.socket.emit('message:delete', {
            msg_id: msg.msg_id,
            to: msg.to,
            from: msg.from,
          });
        }
      };
      actions.appendChild(delBtn);
    }

    bubble.appendChild(actions);
  }

  wrapper.appendChild(bubble);
  document.getElementById('messages').appendChild(wrapper);
}

function renderFileContent(msg) {
  const ft = msg.file_type || '';
  if (ft.startsWith('image/')) {
    const img = document.createElement('img');
    img.src = msg.url;
    img.alt = msg.name;
    img.onclick = () => openLightbox(msg.url);
    return img;
  } else if (ft.startsWith('audio/') || msg.name?.endsWith('.webm') || msg.name?.endsWith('.ogg') || msg.name?.endsWith('.mp3')) {
    const audio = document.createElement('audio');
    audio.controls = true;
    audio.src = msg.url;
    return audio;
  } else if (ft.startsWith('video/')) {
    const video = document.createElement('video');
    video.controls = true;
    video.src = msg.url;
    video.style.maxWidth = '260px';
    video.style.borderRadius = '6px';
    return video;
  } else {
    const a = document.createElement('a');
    a.className = 'file-attach';
    a.href = msg.url;
    a.target = '_blank';
    a.download = msg.name;
    a.rel = 'noopener noreferrer';

    // Build child nodes with textContent — never innerHTML — to prevent XSS
    const icon = document.createElement('span');
    icon.className = 'file-attach-icon';
    icon.textContent = '📄';

    const info = document.createElement('div');

    const nameEl = document.createElement('div');
    nameEl.className = 'file-attach-name';
    nameEl.textContent = msg.name;   // safe: textContent, not innerHTML

    const sizeEl = document.createElement('div');
    sizeEl.className = 'file-attach-size';
    sizeEl.textContent = 'Tap to download';

    info.appendChild(nameEl);
    info.appendChild(sizeEl);
    a.appendChild(icon);
    a.appendChild(info);
    return a;
  }
}

function renderTyping() {
  const indicator = document.getElementById('typing-indicator');
  const users = state.typingUsers[state.currentChat];
  if (!users || users.size === 0) {
    indicator.textContent = '';
    return;
  }
  const names = [...users];
  if (names.length === 1) indicator.textContent = `${names[0]} is typing...`;
  else indicator.textContent = `${names.join(', ')} are typing...`;
}

function scrollToBottom() {
  const el = document.getElementById('messages');
  el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  document.getElementById('jump-to-bottom').classList.remove('visible');
}

// Show jump-to-bottom button when user scrolls up
document.getElementById('messages').addEventListener('scroll', function () {
  const btn = document.getElementById('jump-to-bottom');
  const distFromBottom = this.scrollHeight - this.scrollTop - this.clientHeight;
  btn.classList.toggle('visible', distFromBottom > 150);
});

function _updateMsgStatus(msgId, tick, newId) {
  const el = document.getElementById('status-' + msgId);
  if (el) {
    // Strip any existing tick (single or double checkmark, hourglass)
    const time = el.textContent.replace(/ [⏳✅🟡]$/, '').replace(/ ✅✅$/, '');
    el.textContent = time + ' ' + tick;
    if (newId) el.id = 'status-' + newId;  // re-key to real server msg_id
  }
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ─── SEND MESSAGE ──────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById('msg-input');
  const text = input.value.trim();
  if (!text) return;

  // ── Edit mode: emit edit instead of new message ───────────────────────
  if (state._editingMsg) {
    const editMsg = state._editingMsg;
    state._editingMsg = null;
    cancelReply();
    input.value = '';
    input.style.height = 'auto';

    let editPayload = { msg_id: editMsg.msg_id, to: editMsg.to, text, from: editMsg.from };

    // Re-encrypt if needed
    if (editMsg.encrypted) {
      if (state.currentRoom && state.roomKeys[state.currentRoom]) {
        const ct = await E2E.encryptRoom(text, state.currentRoom);
        if (ct) { editPayload.encrypted = ct; editPayload.text = '🔒'; }
      } else if (state.currentChat !== 'global') {
        const ct = await E2E.encrypt(text, state.currentChat);
        if (ct) { editPayload.encrypted = ct; editPayload.text = '🔒'; }
      }
    }

    state.socket.emit('message:edit', editPayload);
    // Optimistic local update
    const m = _findMsgById(editMsg.msg_id);
    if (m) { m.text = text; m.edited = true; }
    const wrapper = document.querySelector(`[data-msg-id="${editMsg.msg_id}"]`);
    if (wrapper) {
      const textEl = wrapper.querySelector('.bubble-text');
      if (textEl) {
        textEl.textContent = text;
        if (!wrapper.querySelector('.edited-label')) {
          const label = document.createElement('span');
          label.className = 'edited-label';
          label.textContent = ' (edited)';
          textEl.appendChild(label);
        }
      }
    }
    return;
  }

  input.value = '';
  input.style.height = 'auto';

  const sendBtn = document.querySelector('.send-btn');
  if (sendBtn) { sendBtn.style.opacity = '0.5'; sendBtn.disabled = true; }

  // Generate a client-side temp ID so we can track delivery
  const tempId = 'tmp_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);

  let payload = { to: state.currentChat, text, _tempId: tempId };

  // Attach reply-to if set
  if (state.replyTo) {
    payload.reply_to = state.replyTo;
    cancelReply();
  }

  // Encrypt private DMs end-to-end (ECDH-derived shared key)
  if (state.currentChat !== 'global' && !state.currentRoom) {
    const ciphertext = await E2E.encrypt(text, state.currentChat);
    if (ciphertext) { payload.encrypted = ciphertext; payload.text = '🔒'; }
  }

  // Encrypt room messages with the room session key (AES-GCM)
  if (state.currentRoom && state.roomKeys[state.currentRoom]) {
    const ciphertext = await E2E.encryptRoom(text, state.currentRoom);
    if (ciphertext) { payload.encrypted = ciphertext; payload.text = '🔒'; }
  }

  // Render the message locally immediately with ⏳ status
  const localMsg = {
    type: 'text',
    from: state.display,
    color: '',
    text,
    time: Date.now(),
    to: state.currentChat,
    msg_id: tempId,
    _local: true,
    _origText: text,  // keep original for echo matching
    reply_to: payload.reply_to,
  };
  state.msgStatus[tempId] = 'sending';
  await addMessage(localMsg, true);

  // If offline, queue for later; otherwise send now
  if (!state.socket || !state.socket.connected) {
    state.offlineQueue.push(payload);
    showToast('📶 Offline — message queued');
  } else {
    state.socket.emit('send_message', payload);
    state.socket.emit('stop_typing', { to: state.currentChat });
  }

  if (sendBtn) { sendBtn.style.opacity = ''; sendBtn.disabled = false; }
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(); // async, fire-and-forget is fine here
  }
}

// ─── REPLY-TO ──────────────────────────────────────────────
function startReply(msg) {
  state.replyTo = { msg_id: msg.msg_id, from: msg.from, text: msg.text || '[file]' };
  const bar = document.getElementById('reply-bar');
  const barText = document.getElementById('reply-bar-text');
  barText.textContent = `${msg.from}: ${(msg.text || '[file]').slice(0, 60)}`;
  bar.classList.add('active');
  document.getElementById('msg-input').focus();
}

function cancelReply() {
  state.replyTo = null;
  document.getElementById('reply-bar').classList.remove('active');
}

// ─── EDIT MESSAGE ──────────────────────────────────────────
function startEdit(msg) {
  const input = document.getElementById('msg-input');
  input.value = msg.text || '';
  input.focus();
  // Store edit context so sendMessage knows to emit edit instead of new message
  state._editingMsg = msg;
  const bar = document.getElementById('reply-bar');
  const barText = document.getElementById('reply-bar-text');
  barText.textContent = `Editing: ${(msg.text || '').slice(0, 60)}`;
  bar.classList.add('active');
}

// ─── SOUND MUTE TOGGLE ─────────────────────────────────────
function toggleSoundMute() {
  state.soundMuted = !state.soundMuted;
  const btn = document.getElementById('sound-mute-btn');
  if (btn) btn.textContent = state.soundMuted ? '🔕' : '🔔';
  showToast(state.soundMuted ? '🔕 Notification sounds muted' : '🔔 Notification sounds on');
}

// ─── MESSAGE HELPERS ───────────────────────────────────────
function _findMsgById(msgId) {
  for (const arr of Object.values(state.chatMessages)) {
    const m = arr.find(m => m.msg_id === msgId);
    if (m) return m;
  }
  return null;
}

function _scrollToMsg(msgId) {
  const el = document.querySelector(`[data-msg-id="${msgId}"]`);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.style.outline = '2px solid var(--accent)';
    setTimeout(() => { el.style.outline = ''; }, 1500);
  }
}

function _escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

let typingTimeout;
function onTyping(el) {
  // Auto-resize
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';

  state.socket.emit('typing', { to: state.currentChat });
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    state.socket.emit('stop_typing', { to: state.currentChat });
  }, 1500);
}

// ─── FILE UPLOAD ────────────────────────────────────────────
async function sendFile(input) {
  const file = input.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      // Server returned an error (413, 400, 500, etc.)
      alert('Upload failed: ' + (data.error || `Server error ${res.status}`));
      return;
    }

    state.socket.emit('send_file', {
      to: state.currentChat,
      url: data.url,
      name: data.name,
      file_type: file.type
    });
  } catch (err) {
    alert('Upload failed: ' + err.message);
  }

  input.value = '';
}

// ─── VOICE RECORDING ────────────────────────────────────────
let recInterval;

async function toggleRecord() {
  if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
    stopRecord();
  } else {
    await startRecord();
  }
}

async function startRecord() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder = new MediaRecorder(stream);
    state.audioChunks = [];
    state.recordSeconds = 0;

    state.mediaRecorder.ondataavailable = e => state.audioChunks.push(e.data);
    state.mediaRecorder.start(100);

    document.getElementById('record-bar').classList.add('active');
    document.getElementById('mic-btn').style.color = '#ef4444';

    recInterval = setInterval(() => {
      state.recordSeconds++;
      const m = Math.floor(state.recordSeconds / 60);
      const s = state.recordSeconds % 60;
      document.getElementById('record-time').textContent = `${m}:${s.toString().padStart(2, '0')}`;
    }, 1000);
  } catch (err) {
    alert('Microphone access denied. Please allow microphone in your browser.');
  }
}

function stopRecord() {
  if (!state.mediaRecorder) return;
  clearInterval(recInterval);

  state.mediaRecorder.onstop = async () => {
    const blob = new Blob(state.audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('file', blob, 'voice_' + Date.now() + '.webm');

    try {
      const res = await fetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (!res.ok) {
        console.error('[Record] Upload failed:', data.error || res.status);
        return;
      }
      state.socket.emit('send_file', {
        to: state.currentChat,
        url: data.url,
        name: data.name,
        file_type: 'audio/webm'
      });
    } catch (err) {
      console.error('[Record] Upload error:', err.message);
    }
  };

  state.mediaRecorder.stop();
  state.mediaRecorder.stream.getTracks().forEach(t => t.stop());
  state.mediaRecorder = null;
  document.getElementById('record-bar').classList.remove('active');
  document.getElementById('mic-btn').style.color = '';
}

function cancelRecord() {
  if (!state.mediaRecorder) return;
  clearInterval(recInterval);
  state.mediaRecorder.stream.getTracks().forEach(t => t.stop());
  state.mediaRecorder = null;
  state.audioChunks = [];
  document.getElementById('record-bar').classList.remove('active');
  document.getElementById('mic-btn').style.color = '';
}

// ─── EMOJI PICKER ────────────────────────────────────────────
// The emoji-picker custom element is registered by a type="module" script
// which loads asynchronously. We wait for it to be defined before showing
// the picker so it never opens as an empty/broken element.
let _emojiReady = false;
customElements.whenDefined('emoji-picker').then(() => {
  _emojiReady = true;
}).catch(() => {
  // Custom elements not supported — picker will be unavailable
  const btn = document.getElementById('emoji-btn');
  if (btn) btn.style.display = 'none';
});

function toggleEmoji() {
  if (!_emojiReady) {
    showToast('Emoji picker loading…');
    return;
  }
  const container = document.getElementById('emoji-container');
  // getComputedStyle reads the actual display value regardless of whether
  // it was set via inline style or the stylesheet.
  const isVisible = getComputedStyle(container).display !== 'none';
  container.style.display = isVisible ? 'none' : 'block';
}

// emoji-click bubbles to document — works even after DOM re-renders
document.addEventListener('emoji-click', e => {
  const input = document.getElementById('msg-input');
  if (input) {
    input.value += e.detail.unicode;
    input.focus();
  }
  document.getElementById('emoji-container').style.display = 'none';
});

// Close picker when clicking outside it
document.addEventListener('click', e => {
  if (!e.target.closest('#emoji-container') && !e.target.closest('#emoji-btn')) {
    const c = document.getElementById('emoji-container');
    if (c) c.style.display = 'none';
  }
});

// ─── CHAT SWITCHING ───────────────────────────────────────────
function switchChat(chatId) {
  state.currentChat = chatId;

  // Update active state in sidebar
  document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
  const item = document.getElementById('chat-item-' + chatId) ||
    document.getElementById('chat-item-room-' + chatId);
  if (item) item.classList.add('active');

  // Determine context: global, room, or DM
  // A chat is a room if chatId matches the currently active room_id
  const isGlobal = chatId === 'global';
  const isRoom = !isGlobal && chatId === state.currentRoom;
  const isDM = !isGlobal && !isRoom;

  // Show call buttons for rooms and DMs, hide for global
  const headerActions = document.querySelector('.header-actions');
  if (headerActions) {
    headerActions.style.display = isGlobal ? 'none' : 'flex';
  }

  // Update header
  if (isGlobal) {
    document.getElementById('header-name').textContent = 'Global Chat';
    document.getElementById('header-status').textContent = state.users.length + ' members online';
    const av = document.getElementById('header-avatar');
    av.style.background = '#1a4a3a';
    av.style.fontSize = '20px';
    av.textContent = '🌍';
  } else if (isRoom) {
    document.getElementById('header-name').textContent = state.currentRoomName || chatId;
    // status is kept up-to-date by room:members event
    const av = document.getElementById('header-avatar');
    av.style.background = '#1a3a5c';
    av.style.fontSize = '18px';
    av.textContent = '🏠';
  } else {
    const user = state.users.find(u => u.display === chatId);
    document.getElementById('header-name').textContent = chatId;
    document.getElementById('header-status').textContent = '🔒 End-to-end encrypted';
    const av = document.getElementById('header-avatar');
    av.style.background = user ? user.color : stringToColor(chatId);
    av.style.fontSize = '18px';
    av.textContent = chatId[0].toUpperCase();
  }

  // Show active-chat panel, hide placeholder
  document.getElementById('chat-placeholder').style.display = 'none';
  document.getElementById('active-chat').style.display = 'flex';

  // Hide room ID banner when not in a private room
  if (!isRoom) hideRoomIdBanner();

  // Clear unread
  state.unread[chatId] = 0;
  const item2 = document.getElementById('chat-item-' + chatId) ||
    document.getElementById('chat-item-room-' + chatId);
  if (item2) {
    const badge = item2.querySelector('.unread-badge');
    if (badge) badge.remove();
  }

  // Render messages
  document.getElementById('messages').innerHTML = '';
  const msgs = state.chatMessages[chatId] || [];
  msgs.forEach(m => renderMsg(m));
  scrollToBottom();

  // Clear typing
  document.getElementById('typing-indicator').textContent = '';

  // Emit seen for DM messages from the other party
  if (isDM && state.socket && state.socket.connected) {
    const unseenIds = (state.chatMessages[chatId] || [])
      .filter(m => m.from === chatId && m.msg_id && state.msgStatus[m.msg_id] !== 'seen')
      .map(m => m.msg_id);
    if (unseenIds.length) {
      state.socket.emit('message:seen', { msg_ids: unseenIds, sender: chatId });
      unseenIds.forEach(id => { state.msgStatus[id] = 'seen'; });
    }
  }
}

// ─── USER LIST ────────────────────────────────────────────────
function renderUserList(users) {
  // Remove old user items (keep global)
  document.querySelectorAll('.chat-item.user-item').forEach(el => el.remove());

  const list = document.getElementById('chat-list');

  users.forEach(u => {
    if (u.display === state.display) return;   // skip self
    const chatId = u.display;
    let item = document.getElementById('chat-item-' + CSS.escape(chatId));
    if (!item) {
      item = document.createElement('div');
      item.className = 'chat-item user-item';
      item.id = 'chat-item-' + CSS.escape(chatId);
      item.onclick = () => switchChat(chatId);

      // Mute — long-press on mobile, right-click on desktop
      function _toggleMuteUser(e) {
        e.preventDefault();
        if (state.mutedUsers.has(chatId)) {
          state.mutedUsers.delete(chatId);
          showToast(`Unmuted ${chatId}`);
        } else {
          state.mutedUsers.add(chatId);
          showToast(`Muted ${chatId}`);
        }
      }
      item.addEventListener('contextmenu', _toggleMuteUser);
      attachLongPress(item, _toggleMuteUser);

      const avatar = document.createElement('div');
      avatar.className = 'chat-avatar';
      avatar.style.background = u.color;
      avatar.textContent = u.username[0].toUpperCase();

      const info = document.createElement('div');
      info.className = 'chat-item-info';

      const nameRow = document.createElement('div');
      nameRow.className = 'chat-item-name';

      const nameSpan = document.createElement('span');
      nameSpan.textContent = u.display;

      const repBadge = document.createElement('span');
      repBadge.className = 'rep-badge rep-' + (u.reputation || 'new').toLowerCase();
      repBadge.textContent = u.reputation || 'New';

      nameRow.appendChild(nameSpan);
      nameRow.appendChild(repBadge);

      const preview = document.createElement('div');
      preview.className = 'chat-item-preview';
      preview.id = 'preview-' + CSS.escape(chatId);
      preview.textContent = 'Click to chat privately';

      const dot = document.createElement('div');
      dot.className = 'online-dot';

      info.appendChild(nameRow);
      info.appendChild(preview);
      item.appendChild(avatar);
      item.appendChild(info);
      item.appendChild(dot);
      list.appendChild(item);
    }

    if (chatId === state.currentChat) item.classList.add('active');
  });

  // Update header status
  if (state.currentChat === 'global') {
    document.getElementById('header-status').textContent = users.length + ' members online';
  }
}

function updatePreview(chatId, msg) {
  const preview = document.getElementById('preview-' + chatId);
  if (!preview) return;
  const text = msg.type === 'text' ? msg.text
    : msg.file_type?.startsWith('image') ? '📷 Image'
      : msg.file_type?.startsWith('audio') ? '🎤 Voice message'
        : '📎 File';
  preview.textContent = (msg.from === state.display ? 'You: ' : '') + text;
}

function incrementUnread(chatId) {
  state.unread[chatId] = (state.unread[chatId] || 0) + 1;
  const item = document.getElementById('chat-item-' + chatId);
  if (!item) return;
  let badge = item.querySelector('.unread-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.className = 'unread-badge';
    badge.style.cssText = 'background:var(--accent);color:#0a0e13;border-radius:50%;width:20px;height:20px;font-size:11px;font-weight:600;display:flex;align-items:center;justify-content:center;margin-left:auto;flex-shrink:0;';
    item.appendChild(badge);
  }
  badge.textContent = state.unread[chatId];
}

function filterChats() {
  const query = document.getElementById('search-box').value.trim().toLowerCase();
  document.querySelectorAll('.chat-item').forEach(item => {
    const name = item.querySelector('.chat-item-name')?.textContent.toLowerCase() || '';
    // Use includes for substring match; handles accented chars reasonably
    item.style.display = name.includes(query) ? '' : 'none';
  });
}

// ─── ROOM ID BANNER ───────────────────────────────────────
function showRoomIdBanner(roomId) {
  const banner = document.getElementById('room-id-banner');
  document.getElementById('room-id-display').textContent = roomId;
  document.getElementById('room-key-fingerprint').textContent = '—';
  banner.style.display = 'flex';
  // Update debug state
  debugState.roomId = roomId;
  debugState.hasKey = !!state.roomKeys[roomId];
  updateDebugPanel();
}

function hideRoomIdBanner() {
  document.getElementById('room-id-banner').style.display = 'none';
  document.getElementById('room-id-display').textContent = '';
  document.getElementById('room-key-fingerprint').textContent = '—';
  // Update debug state
  debugState.roomId = null;
  debugState.hasKey = false;
  updateDebugPanel();
}

// Legacy stubs — kept so nothing breaks if called
function toggleDebugPanel() { if (DEV_MODE) updateDebugPanel(); }
function refreshDebug() { updateDebugPanel(); }

async function rotateRoomKey() {
  if (!state.currentRoom) return;
  try {
    await E2E.generateRoomKey(state.currentRoom);
    const jwk = await E2E.exportRoomKey(state.currentRoom);
    state.socket.emit('room:key', { room_id: state.currentRoom, key: jwk });
    showToast('🔄 Room key rotated — new key distributed to members');
  } catch (err) {
    showToast('❌ Key rotation failed');
  }
}

function copyRoomId() {
  const roomId = document.getElementById('room-id-display').textContent;
  if (!roomId) return;
  navigator.clipboard.writeText(roomId).then(() => {
    const btn = document.getElementById('copy-room-id-btn');
    btn.textContent = '✓ Copied!';
    btn.style.background = 'rgba(0,255,136,0.3)';
    setTimeout(() => {
      btn.textContent = '📋 Copy';
      btn.style.background = 'rgba(0,255,136,0.15)';
    }, 2000);
  }).catch(() => {
    // Fallback for browsers that block clipboard
    prompt('Copy this Room ID:', roomId);
  });
}

// ─── ROOM MODAL ───────────────────────────────────────────
let _roomVis = 'public';

function openRoomModal(mode) {
  const modal = document.getElementById('room-modal');
  document.getElementById('room-modal-create').style.display = mode === 'create' ? 'block' : 'none';
  document.getElementById('room-modal-join').style.display = mode === 'join' ? 'block' : 'none';
  modal.style.display = 'flex';
  // Reset fields
  if (mode === 'create') {
    document.getElementById('rm-name').value = '';
    document.getElementById('rm-password').value = '';
    document.getElementById('rm-ttl').value = 'session';
    setRoomVis('public');
    setTimeout(() => document.getElementById('rm-name').focus(), 50);
  } else {
    document.getElementById('rm-join-id').value = '';
    document.getElementById('rm-join-password').value = '';
    setTimeout(() => document.getElementById('rm-join-id').focus(), 50);
  }
}

function closeRoomModal() {
  document.getElementById('room-modal').style.display = 'none';
}

function setRoomVis(vis) {
  _roomVis = vis;
  const pubBtn = document.getElementById('rm-vis-public');
  const privBtn = document.getElementById('rm-vis-private');
  const pwWrap = document.getElementById('rm-password-wrap');
  if (vis === 'public') {
    pubBtn.style.border = '1.5px solid var(--accent)';
    pubBtn.style.background = 'rgba(0,255,136,0.15)';
    pubBtn.style.color = 'var(--accent)';
    privBtn.style.border = '1.5px solid var(--border)';
    privBtn.style.background = 'var(--bg-tertiary)';
    privBtn.style.color = 'var(--text-secondary)';
    pwWrap.style.display = 'none';
  } else {
    privBtn.style.border = '1.5px solid var(--accent)';
    privBtn.style.background = 'rgba(0,255,136,0.15)';
    privBtn.style.color = 'var(--accent)';
    pubBtn.style.border = '1.5px solid var(--border)';
    pubBtn.style.background = 'var(--bg-tertiary)';
    pubBtn.style.color = 'var(--text-secondary)';
    pwWrap.style.display = 'block';
  }
}

function submitCreateRoom() {
  const name = document.getElementById('rm-name').value.trim();
  if (!name) { document.getElementById('rm-name').focus(); return; }
  const password = document.getElementById('rm-password').value.trim();
  const ttl = document.getElementById('rm-ttl').value;
  const requireApproval = _roomVis === 'private' &&
    document.getElementById('rm-require-approval').checked;
  // Hash password before sending — server never sees plaintext
  _hashPassword(_roomVis === 'private' ? password : '').then(hashed => {
    state.socket.emit('room:create', {
      name,
      visibility: _roomVis,
      password: hashed,
      ttl,
      require_approval: requireApproval,
    });
  });
  closeRoomModal();
}

function submitJoinPrivateRoom() {
  const roomId = document.getElementById('rm-join-id').value.trim().toUpperCase();
  const password = document.getElementById('rm-join-password').value.trim();
  if (!roomId) { document.getElementById('rm-join-id').focus(); return; }
  // Hash password before sending — server never sees plaintext
  _hashPassword(password).then(hashed => {
    state.socket.emit('room:join_private', { room_id: roomId, password: hashed });
  });
  closeRoomModal();
}

async function _hashPassword(pw) {
  if (!pw) return '';
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(pw));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// Close modal on backdrop click
document.getElementById('room-modal').addEventListener('click', function (e) {
  if (e.target === this) closeRoomModal();
});

// ─── ROOM LIST ────────────────────────────────────────────────
// Renders public rooms into the sidebar chat list.
// Private rooms are never listed — users join them by room_id directly.
function renderRoomList(rooms) {
  // Remove stale room items
  document.querySelectorAll('.chat-item.room-item').forEach(el => el.remove());
  if (!rooms || !rooms.length) return;

  const list = document.getElementById('chat-list');

  rooms.forEach(r => {
    const id = 'chat-item-room-' + r.room_id;
    if (document.getElementById(id)) return;   // already rendered

    const item = document.createElement('div');
    item.className = 'chat-item room-item';
    item.id = id;
    item.onclick = () => {
      state.socket.emit('room:join', { room_id: r.room_id });
      // Optimistically switch to the room chat view (room:joined will populate it)
      state.currentRoom = r.room_id;
      state.currentRoomName = r.name;
      if (!state.chatMessages[r.room_id]) state.chatMessages[r.room_id] = [];
      switchChat(r.room_id);
      toggleSidebar(false);
    };

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.style.background = '#1a3a5c';
    avatar.style.fontSize = '18px';
    avatar.textContent = '🏠';

    const info = document.createElement('div');
    info.className = 'chat-item-info';

    const nameEl = document.createElement('div');
    nameEl.className = 'chat-item-name';
    nameEl.textContent = r.name;

    const preview = document.createElement('div');
    preview.className = 'chat-item-preview';
    preview.textContent = `${r.members} member${r.members !== 1 ? 's' : ''}` +
      (r.is_frozen ? ' · 🔒 frozen' : '');

    info.appendChild(nameEl);
    info.appendChild(preview);
    item.appendChild(avatar);
    item.appendChild(info);
    list.appendChild(item);
  });
}

// ─── LIGHTBOX ────────────────────────────────────────────────
function openLightbox(url) {
  document.getElementById('lightbox-img').src = url;
  document.getElementById('lightbox').classList.add('active');
}

// ─── WEBRTC CALLS ────────────────────────────────────────────
// ICE config is fetched from the server so TURN credentials are never
// embedded in client-side code. Falls back to STUN-only if fetch fails.
let ICE_CONFIG = null;

async function getIceConfig() {
  if (ICE_CONFIG) return ICE_CONFIG;
  try {
    const res = await fetch('/ice-config');
    if (res.ok) {
      ICE_CONFIG = await res.json();
      console.log('[ICE] Config loaded from server, servers:', ICE_CONFIG.iceServers.length);
    } else {
      throw new Error('HTTP ' + res.status);
    }
  } catch (err) {
    console.warn('[ICE] Could not fetch config, using STUN-only fallback:', err.message);
    ICE_CONFIG = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
      ],
      iceCandidatePoolSize: 10,
      bundlePolicy: 'max-bundle',
      rtcpMuxPolicy: 'require',
    };
  }
  return ICE_CONFIG;
}

async function startCall(type) {
  // Prevent multiple simultaneous calls
  if (state.callState !== 'idle') {
    alert('You are already in a call. End it first.');
    return;
  }

  if (state.currentChat === 'global' && !state.currentRoom) {
    alert('Voice/video calls are only available in rooms or private chats.');
    return;
  }

  // Check browser support
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('⚠️ Your browser does not support calls.\n\nTry:\n• Chrome, Firefox, Safari, or Edge\n• Access over HTTPS (or localhost)\n• Allow camera/microphone when prompted');
    return;
  }

  // ── Room call: broadcast invite to all members, then call each who accepts ──
  if (state.currentRoom) {
    state.callType = type;
    state.callState = 'calling';
    state.callTarget = null;   // room call has no single target

    // Notify all room members
    state.socket.emit('room:call', {
      room_id: state.currentRoom,
      call_type: type,
    });

    // Show overlay in "waiting for members" state
    const overlay = document.getElementById('call-overlay');
    overlay.classList.add('active');
    document.getElementById('call-avatar').textContent = '🏠';
    document.getElementById('call-avatar').style.background = '#1a3a5c';
    document.getElementById('call-name').textContent =
      document.getElementById('header-name').textContent;
    document.getElementById('call-status').textContent =
      type === 'video' ? '📹 Room video call — waiting for members…'
        : '📞 Room voice call — waiting for members…';
    document.getElementById('call-action-buttons').style.display = 'none';
    document.getElementById('call-control-buttons').style.display = 'flex';
    const isVideo = type === 'video';
    document.getElementById('call-video-pip').style.display = isVideo ? 'block' : 'none';
    document.getElementById('cam-btn').style.display = isVideo ? 'flex' : 'none';

    // Acquire local media
    try {
      const constraints = isVideo
        ? { audio: true, video: { width: { ideal: 1280 }, height: { ideal: 720 } } }
        : { audio: true, video: false };
      state.localStream = await navigator.mediaDevices.getUserMedia(constraints);
      if (isVideo) {
        document.getElementById('local-video').srcObject = state.localStream;
      }
    } catch (err) {
      console.error('[Call] Media error:', err);
      alert('⚠️ Could not access microphone/camera: ' + err.message);
      endCall();
    }
    return;
  }

  // ── DM call (existing logic) ──────────────────────────────────────────
  state.callTarget = state.currentChat;
  state.callType = type;
  state.callState = 'calling';

  console.log('[Call] Starting', type, 'call to', state.callTarget);

  const overlay = document.getElementById('call-overlay');
  overlay.classList.add('active');

  const callAvatar = document.getElementById('call-avatar');
  const user = state.users.find(u => u.username === state.callTarget);
  callAvatar.style.background = user ? user.color : stringToColor(state.callTarget);
  callAvatar.textContent = state.callTarget[0].toUpperCase();
  document.getElementById('call-name').textContent = state.callTarget;
  document.getElementById('call-status').textContent = type === 'voice' ? 'Calling...' : 'Video calling...';
  document.getElementById('call-action-buttons').style.display = 'none';
  document.getElementById('call-control-buttons').style.display = 'flex';

  // Show video PiP and camera button only for video calls
  const isVideo = type === 'video';
  document.getElementById('call-video-pip').style.display = isVideo ? 'block' : 'none';
  document.getElementById('cam-btn').style.display = isVideo ? 'flex' : 'none';

  // Set timeout for unanswered calls (30 seconds)
  state.callTimeout = setTimeout(() => {
    if (state.callState === 'calling') {
      console.log('[Call] Call timeout - no answer from', state.callTarget);
      alert('📞 Call timeout - No answer from ' + state.callTarget);
      endCall();
    }
  }, 30000);

  try {
    console.log('[Call] Requesting', type === 'video' ? 'audio+video' : 'audio', 'media');

    // Try with advanced constraints first
    let constraints = type === 'video'
      ? {
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          autoGainControl: { ideal: true }
        },
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 }
        }
      }
      : {
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          autoGainControl: { ideal: true }
        },
        video: false
      };

    try {
      state.localStream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (constraintErr) {
      console.warn('[Call] Constraint error, trying fallback:', constraintErr.name);
      // Fallback to minimal constraints
      constraints = type === 'video' ? { audio: true, video: true } : { audio: true, video: false };
      state.localStream = await navigator.mediaDevices.getUserMedia(constraints);
    }

    console.log('[Call] Media obtained successfully');
    const audioTrack = state.localStream.getAudioTracks()[0];
    const videoTrack = state.localStream.getVideoTracks()[0];
    console.log('[Call] Audio track:', audioTrack ? 'YES (' + audioTrack.label + ')' : 'NO');
    console.log('[Call] Video track:', videoTrack ? 'YES (' + videoTrack.label + ')' : 'NO');

    if (type === 'video') {
      document.getElementById('local-video').srcObject = state.localStream;
    }

    // Clean up old peer connection if exists
    if (state.peerConnection) {
      console.log('[WebRTC] Cleaning up old peer connection');
      state.peerConnection.close();
      state.peerConnection = null;
    }

    console.log('[WebRTC] Creating new peer connection');
    state.peerConnection = new RTCPeerConnection(await getIceConfig());

    // Add all tracks
    const trackCount = { audio: 0, video: 0 };
    state.localStream.getTracks().forEach(track => {
      console.log('[WebRTC] Adding', track.kind, 'track (enabled:', track.enabled + ')');
      state.peerConnection.addTrack(track, state.localStream);
      trackCount[track.kind]++;
    });
    console.log('[WebRTC] Total tracks added - Audio:', trackCount.audio, 'Video:', trackCount.video);

    state.peerConnection.ontrack = e => {
      console.log('[WebRTC] Received remote', e.track.kind, 'track');
      if (e.streams && e.streams[0]) {
        const remoteStream = e.streams[0];

        // For video or audio, attach to video element (contains both audio and video)
        const videoEl = document.getElementById('remote-video');
        videoEl.srcObject = remoteStream;

        // Also attach to audio element as backup for better audio playback
        const audioEl = document.getElementById('remote-audio');
        audioEl.srcObject = remoteStream;

        // Try to play both elements
        const playPromises = [videoEl.play().catch(() => null), audioEl.play().catch(() => null)];
        Promise.all(playPromises).then(() => {
          console.log('[WebRTC] Remote media playing');
        }).catch(() => {
          console.warn('[WebRTC] Autoplay blocked by browser policy');
          console.log('[WebRTC] Audio will start on next user interaction');
          // On any user click, attempt to play
          const retryPlay = () => {
            videoEl.play().catch(() => { });
            audioEl.play().catch(() => { });
            document.removeEventListener('click', retryPlay);
          };
          document.addEventListener('click', retryPlay);
        });

        console.log('[WebRTC] Remote stream attached, tracks:', remoteStream.getTracks().map(t => `${t.kind}(${t.enabled ? 'on' : 'off'})`.toUpperCase()));
      } else {
        console.warn('[WebRTC] No streams in track event');
      }
    };

    state.peerConnection.onicecandidate = e => {
      if (e.candidate) {
        console.log('[WebRTC] Sending ICE candidate, type:', e.candidate.type);
        state.socket.emit('webrtc_signal', { to: state.callTarget, type: 'ice', candidate: e.candidate });
      }
    };

    state.peerConnection.onicegatheringstatechange = () => {
      console.log('[WebRTC] ICE gathering state:', state.peerConnection?.iceGatheringState);
    };

    state.peerConnection.oniceconnectionstatechange = () => {
      console.log('[WebRTC] ICE connection state:', state.peerConnection?.iceConnectionState);
      if (state.peerConnection?.iceConnectionState === 'failed') {
        console.warn('[WebRTC] ICE connection failed - attempting restart...');
      }
    };

    state.peerConnection.onconnectionstatechange = () => {
      console.log('[WebRTC] Connection state:', state.peerConnection?.connectionState);
      console.log('[WebRTC] ICE connection state:', state.peerConnection?.iceConnectionState);
      console.log('[WebRTC] ICE gathering state:', state.peerConnection?.iceGatheringState);
      console.log('[WebRTC] Signaling state:', state.peerConnection?.signalingState);

      if (state.peerConnection?.connectionState === 'connected') {
        document.getElementById('call-status').textContent = '✅ Connected - Audio/Video flowing';
      } else if (state.peerConnection?.connectionState === 'connecting') {
        document.getElementById('call-status').textContent = '🔗 Establishing connection...';
      }

      if (state.peerConnection?.connectionState === 'disconnected' || state.peerConnection?.connectionState === 'failed') {
        if (state.peerConnection?.connectionState === 'failed') {
          console.warn('[WebRTC] Connection FAILED - Attempting ICE restart...');
          document.getElementById('call-status').textContent = 'Reconnecting...';
          state.peerConnection.restartIce?.();
        } else {
          console.warn('[WebRTC] Connection disconnected');
        }
      }
    };

    // Create and send the offer
    console.log('[Call] Creating offer');
    const offer = await state.peerConnection.createOffer();
    console.log('[Call] Setting local description with offer');
    await state.peerConnection.setLocalDescription(offer);
    console.log('[Call] Sending offer to', state.callTarget);
    state.socket.emit('webrtc_signal', { to: state.callTarget, type: 'offer', sdp: offer, callType: type });
    startStatsMonitoring();

  } catch (err) {
    console.error('[Call Error] startCall failed:', err.name, err.message);
    let errorMsg = '❌ Call failed:\n\n';
    if (err.name === 'NotAllowedError') {
      errorMsg += '⚙️ Permission denied\n\n';
      errorMsg += 'When prompted, please:\n';
      errorMsg += '1️⃣  Allow camera/microphone access\n';
      errorMsg += '2️⃣  Tap "Allow" on all permission dialogs\n';
      errorMsg += '3️⃣  Try the call again\n\n';
      errorMsg += '📱 On mobile: Check if ngrok URL is HTTPS';
    } else if (err.name === 'NotFoundError') {
      errorMsg += 'No camera/microphone found on this device';
    } else if (err.name === 'NotSupportedError') {
      errorMsg += 'Your browser does not support WebRTC calls';
    } else {
      errorMsg += err.message || 'Could not access camera/microphone';
    }
    alert(errorMsg);
    endCall();
  }
} // end startCall

// ── startDmCall ───────────────────────────────────────────────────────────────
// Initiates a direct 1-to-1 WebRTC call to `target` without going through the
// room-broadcast branch of startCall.  Used by the room:incoming_call "Join"
// button so that a room member can dial the caller back directly.
async function startDmCall(target, type) {
  if (state.callState !== 'idle') return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('⚠️ Your browser does not support calls.');
    return;
  }

  state.callTarget = target;
  state.callType = type;
  state.callState = 'calling';

  const overlay = document.getElementById('call-overlay');
  overlay.classList.add('active');
  const callAvatar = document.getElementById('call-avatar');
  const user = state.users.find(u => u.display === target || u.username === target);
  callAvatar.style.background = user ? user.color : stringToColor(target);
  callAvatar.textContent = target[0].toUpperCase();
  document.getElementById('call-name').textContent = target;
  document.getElementById('call-status').textContent = type === 'video' ? 'Video calling…' : 'Calling…';
  document.getElementById('call-action-buttons').style.display = 'none';
  document.getElementById('call-control-buttons').style.display = 'flex';
  const isVideo = type === 'video';
  document.getElementById('call-video-pip').style.display = isVideo ? 'block' : 'none';
  document.getElementById('cam-btn').style.display = isVideo ? 'flex' : 'none';

  state.callTimeout = setTimeout(() => {
    if (state.callState === 'calling') {
      showToast('📞 No answer from ' + target);
      endCall();
    }
  }, 30000);

  try {
    const constraints = isVideo
      ? { audio: { echoCancellation: { ideal: true }, noiseSuppression: { ideal: true } }, video: { width: { ideal: 640 }, height: { ideal: 480 } } }
      : { audio: { echoCancellation: { ideal: true }, noiseSuppression: { ideal: true } }, video: false };
    try {
      state.localStream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (_) {
      state.localStream = await navigator.mediaDevices.getUserMedia(isVideo ? { audio: true, video: true } : { audio: true, video: false });
    }
    if (isVideo) document.getElementById('local-video').srcObject = state.localStream;

    if (state.peerConnection) { state.peerConnection.close(); state.peerConnection = null; }
    state.peerConnection = new RTCPeerConnection(await getIceConfig());
    state.localStream.getTracks().forEach(t => state.peerConnection.addTrack(t, state.localStream));

    state.peerConnection.ontrack = e => {
      if (e.streams && e.streams[0]) {
        const rs = e.streams[0];
        document.getElementById('remote-video').srcObject = rs;
        document.getElementById('remote-audio').srcObject = rs;
        document.getElementById('remote-video').play().catch(() => { });
        document.getElementById('remote-audio').play().catch(() => { });
      }
    };
    state.peerConnection.onicecandidate = e => {
      if (e.candidate) state.socket.emit('webrtc_signal', { to: state.callTarget, type: 'ice', candidate: e.candidate });
    };
    state.peerConnection.onconnectionstatechange = () => {
      const cs = state.peerConnection?.connectionState;
      if (cs === 'connected') document.getElementById('call-status').textContent = '✅ Connected';
      if (cs === 'failed') { state.peerConnection.restartIce?.(); }
    };

    const offer = await state.peerConnection.createOffer();
    await state.peerConnection.setLocalDescription(offer);
    state.socket.emit('webrtc_signal', { to: state.callTarget, type: 'offer', sdp: offer, callType: type });
    startStatsMonitoring();
  } catch (err) {
    console.error('[startDmCall]', err.name, err.message);
    alert('❌ Call failed: ' + (err.message || err.name));
    endCall();
  }
}


console.log('[Signal] Received:', {
  type: data.type,
  from: data.from,
  callState: state.callState,
  callTarget: state.callTarget,
  hasPeerConnection: !!state.peerConnection
});

if (data.type === 'offer') {
  // Incoming call offer.
  // Special case: if WE are the room caller (callState='calling', callTarget=null),
  // a room member is dialling us back after accepting our broadcast invite.
  // Auto-accept their offer so the connection completes without a second prompt.
  const isRoomCallBack = (state.callState === 'calling' && state.callTarget === null);

  if (state.callState !== 'idle' && !isRoomCallBack) {
    console.log('[Call] Already in a call, rejecting incoming');
    state.socket.emit('webrtc_signal', { to: data.from, type: 'reject' });
    return;
  }

  // Check browser support
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('⚠️ Your browser does not support calls.\n\nTry:\n• Chrome, Firefox, Safari, or Edge\n• Access over HTTPS (or localhost)\n• Allow camera/microphone when prompted');
    state.socket.emit('webrtc_signal', { to: data.from, type: 'reject' });
    return;
  }

  state.callTarget = data.from;
  state.callType = data.callType;
  state.callState = 'ringing';

  // For room call-backs: the caller already has media and is waiting.
  // Auto-accept without showing the incoming call UI again.
  if (isRoomCallBack) {
    console.log('[Call] Room call-back from', data.from, '— auto-accepting');
    document.getElementById('call-status').textContent = `🔗 Connecting to ${data.from}…`;
    document.getElementById('call-action-buttons').style.display = 'none';
    document.getElementById('call-control-buttons').style.display = 'flex';
  } else {
    // Send notification
    notifyIncomingCall(data.from, data.callType);

    document.getElementById('call-overlay').classList.add('active');
    document.getElementById('call-name').textContent = data.from;
    document.getElementById('call-status').textContent = `📞 ${data.callType === 'video' ? 'Video' : 'Voice'} call from ${data.from}...`;

    // Show/hide video PiP and camera button based on call type
    const isVideoCall = data.callType === 'video';
    document.getElementById('call-video-pip').style.display = isVideoCall ? 'block' : 'none';
    document.getElementById('cam-btn').style.display = isVideoCall ? 'flex' : 'none';

    // Show action buttons, hide control buttons
    document.getElementById('call-action-buttons').style.display = 'flex';
    document.getElementById('call-control-buttons').style.display = 'none';

    const callAvatar = document.getElementById('call-avatar');
    const user = state.users.find(u => u.username === data.from);
    callAvatar.style.background = user ? user.color : stringToColor(data.from);
    callAvatar.textContent = data.from[0].toUpperCase();
  }

  // Wait for user to click Accept or Reject (skipped for room call-backs)
  const userAccepted = isRoomCallBack ? true : await new Promise(resolve => {
    const acceptBtn = document.getElementById('accept-btn');
    const rejectBtn = document.getElementById('reject-btn');

    // 60s callee timeout — if caller disappears mid-ring, close the overlay
    const calleeTimeout = setTimeout(() => {
      acceptBtn.removeEventListener('click', handleAccept);
      rejectBtn.removeEventListener('click', handleReject);
      resolve(false);
    }, 60000);

    const handleAccept = () => {
      clearTimeout(calleeTimeout);
      stopRingTone();   // stop ring immediately on accept
      acceptBtn.removeEventListener('click', handleAccept);
      rejectBtn.removeEventListener('click', handleReject);
      resolve(true);
    };

    const handleReject = () => {
      clearTimeout(calleeTimeout);
      acceptBtn.removeEventListener('click', handleAccept);
      rejectBtn.removeEventListener('click', handleReject);
      resolve(false);
    };

    acceptBtn.addEventListener('click', handleAccept);
    rejectBtn.addEventListener('click', handleReject);
  });

  if (!userAccepted) {
    console.log('[Call] User rejected call from', data.from);
    state.socket.emit('webrtc_signal', { to: data.from, type: 'reject' });
    endCall();
    return;
  }

  // User accepted - proceed with connection setup
  console.log('[Call] User accepted call from', data.from);
  document.getElementById('call-status').textContent = 'Connecting...';
  document.getElementById('call-action-buttons').style.display = 'none';
  document.getElementById('call-control-buttons').style.display = 'flex';

  try {
    console.log('[Call] Accepting call - requesting media');

    // For room call-backs the caller already acquired media in startCall.
    // Reuse it instead of calling getUserMedia again.
    if (isRoomCallBack && state.localStream) {
      console.log('[Call] Reusing existing local stream for room call-back');
    } else {
      // Try with advanced constraints first
      let constraints = data.callType === 'video'
        ? {
          audio: {
            echoCancellation: { ideal: true },
            noiseSuppression: { ideal: true },
            autoGainControl: { ideal: true }
          },
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 }
          }
        }
        : {
          audio: {
            echoCancellation: { ideal: true },
            noiseSuppression: { ideal: true },
            autoGainControl: { ideal: true }
          },
          video: false
        };

      try {
        state.localStream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (constraintErr) {
        console.warn('[Call] Constraint error, trying fallback:', constraintErr.name);
        // Fallback to minimal constraints
        constraints = data.callType === 'video' ? { audio: true, video: true } : { audio: true, video: false };
        state.localStream = await navigator.mediaDevices.getUserMedia(constraints);
      }

      console.log('[Call] Media obtained, creating peer connection');
      const audioTrack = state.localStream.getAudioTracks()[0];
      const videoTrack = state.localStream.getVideoTracks()[0];
      console.log('[Call] Audio track:', audioTrack ? 'YES (' + audioTrack.label + ')' : 'NO');
      console.log('[Call] Video track:', videoTrack ? 'YES (' + videoTrack.label + ')' : 'NO');
      if (data.callType === 'video') document.getElementById('local-video').srcObject = state.localStream;
    } // end else (not a room call-back reuse)

    // Clean up old peer connection if exists
    if (state.peerConnection) {
      state.peerConnection.close();
      state.peerConnection = null;
    }

    state.peerConnection = new RTCPeerConnection(await getIceConfig());

    // Add all tracks
    const trackCount = { audio: 0, video: 0 };
    state.localStream.getTracks().forEach(track => {
      console.log('[WebRTC] Adding track:', track.kind, '(enabled:', track.enabled + ')');
      state.peerConnection.addTrack(track, state.localStream);
      trackCount[track.kind]++;
    });
    console.log('[WebRTC] Total tracks added - Audio:', trackCount.audio, 'Video:', trackCount.video);

    state.peerConnection.ontrack = e => {
      console.log('[WebRTC] Received remote track:', e.track.kind);
      if (e.streams && e.streams[0]) {
        const remoteStream = e.streams[0];

        // For video or audio, attach to video element (contains both audio and video)
        const videoEl = document.getElementById('remote-video');
        videoEl.srcObject = remoteStream;

        // Also attach to audio element as backup for better audio playback
        const audioEl = document.getElementById('remote-audio');
        audioEl.srcObject = remoteStream;

        // Try to play both elements
        const playPromises = [videoEl.play().catch(() => null), audioEl.play().catch(() => null)];
        Promise.all(playPromises).then(() => {
          console.log('[WebRTC] Remote media playing');
        }).catch(() => {
          console.warn('[WebRTC] Autoplay blocked by browser policy');
          console.log('[WebRTC] Audio will start on next user interaction');
          // On any user click, attempt to play
          const retryPlay = () => {
            videoEl.play().catch(() => { });
            audioEl.play().catch(() => { });
            document.removeEventListener('click', retryPlay);
          };
          document.addEventListener('click', retryPlay);
        });

        console.log('[WebRTC] Remote stream attached, tracks:', remoteStream.getTracks().map(t => `${t.kind}(${t.enabled ? 'on' : 'off'})`.toUpperCase()));
      } else {
        console.warn('[WebRTC] No streams in track event');
      }
    };

    state.peerConnection.onicecandidate = e => {
      if (e.candidate) {
        console.log('[WebRTC] ICE candidate generated, type:', e.candidate.type);
        state.socket.emit('webrtc_signal', { to: data.from, type: 'ice', candidate: e.candidate });
      }
    };

    state.peerConnection.onicegatheringstatechange = () => {
      console.log('[WebRTC] ICE gathering state:', state.peerConnection?.iceGatheringState);
    };

    state.peerConnection.oniceconnectionstatechange = () => {
      console.log('[WebRTC] ICE connection state:', state.peerConnection?.iceConnectionState);
      if (state.peerConnection?.iceConnectionState === 'failed') {
        console.warn('[WebRTC] ICE connection failed');
      }
    };

    state.peerConnection.onconnectionstatechange = () => {
      console.log('[WebRTC] Connection state:', state.peerConnection?.connectionState);
      console.log('[WebRTC] ICE connection state:', state.peerConnection?.iceConnectionState);
      console.log('[WebRTC] ICE gathering state:', state.peerConnection?.iceGatheringState);
      console.log('[WebRTC] Signaling state:', state.peerConnection?.signalingState);

      if (state.peerConnection?.connectionState === 'connected') {
        document.getElementById('call-status').textContent = '✅ Connected - Audio/Video flowing';
      } else if (state.peerConnection?.connectionState === 'connecting') {
        document.getElementById('call-status').textContent = '🔗 Establishing connection...';
      }

      if (state.peerConnection?.connectionState === 'disconnected' || state.peerConnection?.connectionState === 'failed') {
        if (state.peerConnection?.connectionState === 'failed') {
          console.warn('[WebRTC] Connection FAILED - Attempting ICE restart...');
          document.getElementById('call-status').textContent = 'Reconnecting...';
          state.peerConnection.restartIce?.();
        } else {
          console.warn('[WebRTC] Connection disconnected');
        }
      }
    };

    console.log('[Call] Setting remote description with offer');
    await state.peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));

    // Flush any ICE candidates that arrived before setRemoteDescription
    if (state.iceCandidateBuffer.length > 0) {
      console.log('[WebRTC] Flushing', state.iceCandidateBuffer.length, 'buffered ICE candidates (callee)');
      for (const candidate of state.iceCandidateBuffer) {
        try {
          await state.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (err) {
          console.warn('[WebRTC] Error adding buffered ICE (callee):', err.message);
        }
      }
      state.iceCandidateBuffer = [];
    }

    console.log('[Call] Creating answer');
    const answer = await state.peerConnection.createAnswer();

    console.log('[Call] Setting local description with answer');
    await state.peerConnection.setLocalDescription(answer);

    state.callState = 'connected';
    document.getElementById('call-status').textContent = 'Connected';
    startStatsMonitoring();

    console.log('[Call] Sending answer back to', data.from);
    state.socket.emit('webrtc_signal', { to: data.from, type: 'answer', sdp: answer });
  } catch (err) {
    console.error('[Call Error] Accepting offer:', err.name, err.message);
    let errorMsg = '❌ Call failed:\n\n';
    if (err.name === 'NotAllowedError') {
      errorMsg += '⚙️ Permission denied\n\n';
      errorMsg += 'When prompted, please:\n';
      errorMsg += '1️⃣  Allow camera/microphone access\n';
      errorMsg += '2️⃣  Tap "Allow" on all permission dialogs\n';
      errorMsg += '3️⃣  Try the call again\n\n';
      errorMsg += '📱 On mobile: Check if ngrok URL is HTTPS';
    } else if (err.name === 'NotFoundError') {
      errorMsg += 'No camera/microphone found on this device';
    } else if (err.name === 'InvalidStateError') {
      errorMsg += 'Call connection error - try again';
    } else {
      errorMsg += err.message || 'Could not accept call';
    }
    alert(errorMsg);
    console.log('[Call] Sending reject due to error:', err.name);
    state.socket.emit('webrtc_signal', { to: data.from, type: 'reject' });
    endCall();
  }

} else if (data.type === 'answer') {
  console.log('[Call] Received answer from', data.from);
  if (!state.peerConnection) {
    console.warn('[Call] Received answer but no peer connection exists');
    return;
  }
  try {
    console.log('[Call] Setting remote description with answer');
    await state.peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
    state.callState = 'connected';
    startStatsMonitoring();
    console.log('[WebRTC] Flushing', state.iceCandidateBuffer.length, 'buffered ICE candidates');
    for (const candidate of state.iceCandidateBuffer) {
      try {
        await state.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (err) {
        console.warn('[WebRTC] Error adding buffered ICE:', err.message);
      }
    }
    state.iceCandidateBuffer = [];

    // Clear call timeout — the callee answered
    if (state.callTimeout) {
      clearTimeout(state.callTimeout);
      state.callTimeout = null;
    }

    document.getElementById('call-status').textContent = '✅ Connected';
    console.log('[Call] Connected!');
  } catch (err) {
    console.error('[WebRTC Error] Setting answer:', err.name, err.message);
  }

} else if (data.type === 'ice') {
  console.log('[WebRTC] Received ICE candidate');
  if (!state.peerConnection || !state.peerConnection.remoteDescription) {
    // Buffer candidates until remote description is set
    console.log('[WebRTC] Buffering ICE candidate — remote description not yet set');
    state.iceCandidateBuffer.push(data.candidate);
    return;
  }
  try {
    await state.peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
    console.log('[WebRTC] ICE candidate added successfully');
  } catch (err) {
    console.warn('[WebRTC] ICE candidate error (may be normal):', err.message);
  }

} else if (data.type === 'reject') {
  console.log('[Call] Call rejected by', data.from);
  alert(`❌ ${data.from} declined the call.`);
  endCall();

} else if (data.type === 'end') {
  console.log('[Call] Call ended by', data.from);
  endCall();
} else {
  console.warn('[Signal] Unknown signal type:', data.type);
}
} // end handleSignal

// ─── WebRTC STATS MONITOR ─────────────────────────────────────────
let _lastAudioBytes = 0;
let _noAudioWarned = false;

function _showCallWarning(msg) {
  const el = document.getElementById('call-status');
  if (el && !el.dataset.warning) {
    el.dataset.warning = '1';
    const prev = el.textContent;
    el.textContent = msg;
    el.style.color = '#ffaa00';
    setTimeout(() => {
      el.textContent = prev;
      el.style.color = '';
      delete el.dataset.warning;
    }, 5000);
  }
}

async function monitorWebRTCStats() {
  if (!state.peerConnection || state.callState !== 'connected') return;

  try {
    const stats = await state.peerConnection.getStats();
    let audioStats = null, videoStats = null, candidatePair = null;

    stats.forEach(report => {
      if (report.type === 'inbound-rtp' && report.kind === 'audio') {
        audioStats = report;
      } else if (report.type === 'inbound-rtp' && report.kind === 'video') {
        videoStats = report;
      } else if (report.type === 'candidate-pair' && report.state === 'succeeded') {
        candidatePair = report;
      }
    });

    if (audioStats) {
      const bytesNow = audioStats.bytesReceived || 0;
      const packetsLost = audioStats.packetsLost || 0;
      const packetsReceived = audioStats.packetsReceived || 1;
      const lossRate = packetsLost / (packetsLost + packetsReceived);

      if (bytesNow === _lastAudioBytes && bytesNow > 0 && !_noAudioWarned) {
        _noAudioWarned = true;
        _showCallWarning('⚠️ No audio received — check remote mic');
      } else if (bytesNow > _lastAudioBytes) {
        _noAudioWarned = false;
      }
      _lastAudioBytes = bytesNow;

      if (lossRate > 0.1) {
        _showCallWarning(`⚠️ Poor connection — ${Math.round(lossRate * 100)}% packet loss`);
      }

      console.log('[WebRTC-Stats] Audio bytes:', bytesNow, 'loss:', Math.round(lossRate * 100) + '%');
    } else {
      console.warn('[WebRTC-Stats] No audio stats yet (still connecting or no audio track)');
    }

    if (videoStats) {
      console.log('[WebRTC-Stats] Video - Received:', videoStats.bytesReceived, 'packets:', videoStats.packetsReceived);
    }

    if (candidatePair) {
      console.log('[WebRTC-Stats] ICE - Current bitrate:', (candidatePair.availableOutgoingBitrate || 0).toFixed(0), 'bps');
    }
  } catch (err) {
    console.warn('[WebRTC-Stats] Error:', err.message);
  }
}

// Start monitoring stats every 2 seconds
let statsInterval = null;
function startStatsMonitoring() {
  if (statsInterval) clearInterval(statsInterval);
  statsInterval = setInterval(monitorWebRTCStats, 2000);
  console.log('[WebRTC-Stats] Started monitoring');
}

function stopStatsMonitoring() {
  if (statsInterval) {
    clearInterval(statsInterval);
    statsInterval = null;
    console.log('[WebRTC-Stats] Stopped monitoring');
  }
}

function endCall() {
  console.log('[Call] Ending call');
  stopRingTone();   // cancel any active ring tone immediately
  stopStatsMonitoring();
  _lastAudioBytes = 0;
  _noAudioWarned = false;

  // Clear ICE candidate buffer
  state.iceCandidateBuffer = [];

  // Clear call timeout
  if (state.callTimeout) {
    clearTimeout(state.callTimeout);
    state.callTimeout = null;
  }

  // Close peer connection
  if (state.peerConnection) {
    console.log('[WebRTC] Closing peer connection');
    try {
      state.peerConnection.close();
    } catch (err) {
      console.error('[WebRTC Error] Closing connection:', err);
    }
    state.peerConnection = null;
  }

  // Stop all tracks
  if (state.localStream) {
    console.log('[WebRTC] Stopping local stream tracks');
    state.localStream.getTracks().forEach(t => {
      try {
        t.stop();
      } catch (err) {
        console.error('[WebRTC Error] Stopping track:', err);
      }
    });
    state.localStream = null;
  }

  // Notify the other party
  if (state.callTarget && state.callState !== 'idle') {
    console.log('[Call] Notifying', state.callTarget, 'that call ended');
    state.socket.emit('webrtc_signal', { to: state.callTarget, type: 'end' });
  }

  // Clear UI
  document.getElementById('call-overlay').classList.remove('active');
  document.getElementById('remote-video').srcObject = null;
  document.getElementById('local-video').srcObject = null;
  document.getElementById('call-action-buttons').style.display = 'none';
  document.getElementById('call-control-buttons').style.display = 'flex';

  // Close any lingering call notification — must happen BEFORE nulling callTarget
  if (state.callTarget) {
    const callNotif = _activeNotifs.get(`call-${state.callTarget}`);
    if (callNotif) { try { callNotif.close(); } catch (_) { } }
    _activeNotifs.delete(`call-${state.callTarget}`);
  }

  // Reset state
  state.callTarget = null;
  state.callType = null;
  state.callState = 'idle';
  state.muted = false;
  state.camOff = false;

  // Reset button SVG icons to their default (unmuted / cam-on) state
  const muteIcon = document.getElementById('mute-icon');
  if (muteIcon) muteIcon.innerHTML = '<path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm0 2a2 2 0 0 0-2 2v7a2 2 0 0 0 4 0V5a2 2 0 0 0-2-2zm-7 8a1 1 0 0 1 1 1 6 6 0 0 0 12 0 1 1 0 0 1 2 0 8 8 0 0 1-7 7.93V21h2a1 1 0 0 1 0 2H9a1 1 0 0 1 0-2h2v-1.07A8 8 0 0 1 4 12a1 1 0 0 1 1-1z"/>';
  const camIcon = document.getElementById('cam-icon');
  if (camIcon) camIcon.innerHTML = '<path d="M15 8H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1.5l4 2.5V9l-4 2.5V10a2 2 0 0 0-2-2z"/>';
  document.getElementById('mute-btn')?.classList.remove('active-mute');
  document.getElementById('cam-btn')?.classList.remove('cam-off');
}

function toggleMute() {
  if (!state.localStream) return;
  state.muted = !state.muted;
  state.localStream.getAudioTracks().forEach(t => t.enabled = !state.muted);
  const btn = document.getElementById('mute-btn');
  btn.classList.toggle('active-mute', state.muted);
  // Swap icon: mic-off when muted
  document.getElementById('mute-icon').innerHTML = state.muted
    ? '<path d="M19 11a7 7 0 0 1-.78 3.22L5.92 2.35A4 4 0 0 1 16 5v6a4 4 0 0 1-.06.69M3.27 3.27 2 4.54l4 4A7 7 0 0 0 11 19.93V21H9a1 1 0 0 0 0 2h6a1 1 0 0 0 0-2h-2v-1.07A8 8 0 0 0 19.46 12l1.27-1.27M8 5v.18L16.82 14A4 4 0 0 1 8 12V5zM2.27 2.27 1 3.54l2 2A7.93 7.93 0 0 0 4 12a1 1 0 0 0 2 0 6 6 0 0 1-.08-1L2.27 2.27z"/>'
    : '<path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm0 2a2 2 0 0 0-2 2v7a2 2 0 0 0 4 0V5a2 2 0 0 0-2-2zm-7 8a1 1 0 0 1 1 1 6 6 0 0 0 12 0 1 1 0 0 1 2 0 8 8 0 0 1-7 7.93V21h2a1 1 0 0 1 0 2H9a1 1 0 0 1 0-2h2v-1.07A8 8 0 0 1 4 12a1 1 0 0 1 1-1z"/>';
}

function toggleCam() {
  if (!state.localStream) return;
  state.camOff = !state.camOff;
  state.localStream.getVideoTracks().forEach(t => t.enabled = !state.camOff);
  const btn = document.getElementById('cam-btn');
  btn.classList.toggle('cam-off', state.camOff);
  // Swap icon: camera-off when disabled
  document.getElementById('cam-icon').innerHTML = state.camOff
    ? '<path d="M2 2 1 3l4.586 4.586A2 2 0 0 0 5 8v6a2 2 0 0 0 2 2h8.414L21 22l1-1L2 2zm3 6.414L17.586 20H7a1 1 0 0 1-1-1V8.414zM21 7l-4 2.5V10a2 2 0 0 0-2-2h-1.586l-2-2H15a2 2 0 0 1 2 2v.086L21 7z"/>'
    : '<path d="M15 8H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1.5l4 2.5V9l-4 2.5V10a2 2 0 0 0-2-2z"/>';
}

// ─── UTILS ────────────────────────────────────────────────────
function stringToColor(str) {
  const colors = ['#1a5c3e', '#1a3a5c', '#5c1a3a', '#3a1a5c', '#5c3a1a', '#1a5c5c', '#5c1a1a', '#1a1a5c'];
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

let _toastTimer;
let _toastQueue = [];
let _toastBusy = false;

function showToast(msg, duration = 2500) {
  _toastQueue.push({ msg, duration });
  if (!_toastBusy) _drainToastQueue();
}

function _drainToastQueue() {
  if (!_toastQueue.length) { _toastBusy = false; return; }
  _toastBusy = true;
  const { msg, duration } = _toastQueue.shift();
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => {
    el.classList.remove('show');
    // Small gap between toasts so they feel distinct
    setTimeout(_drainToastQueue, 300);
  }, duration);
}

// ─── SIDEBAR TOGGLE (mobile) ─────────────────────────────────────────────
function toggleSidebar(open) {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!sidebar || !overlay) return;
  if (open) {
    sidebar.classList.add('mobile-open');
    overlay.classList.add('active');
  } else {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('active');
  }
}

// ─── LONG PRESS HELPER ───────────────────────────────────────────────────
// Works on both touch (mobile) and mouse (desktop).
// Fires callback after 500 ms hold.
// Cancels if the finger moves more than 10 px — prevents conflict with scroll.
function attachLongPress(el, callback, delay = 500) {
  let timer = null;
  let startX = 0;
  let startY = 0;

  function start(e) {
    if (e.type === 'mousedown' && e.button !== 0) return;
    if (e.type === 'touchstart') {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    }
    timer = setTimeout(() => {
      callback(e);
      // Haptic feedback on Android
      if (navigator.vibrate) navigator.vibrate(10);
      timer = null;
    }, delay);
  }

  function move(e) {
    if (!timer) return;
    if (e.type === 'touchmove') {
      const dx = Math.abs(e.touches[0].clientX - startX);
      const dy = Math.abs(e.touches[0].clientY - startY);
      // Cancel if finger moved more than 10 px — user is scrolling
      if (dx > 10 || dy > 10) cancel();
    }
  }

  function cancel() {
    if (timer) { clearTimeout(timer); timer = null; }
  }

  el.addEventListener('touchstart', start, { passive: true });
  el.addEventListener('touchmove', move, { passive: true });
  el.addEventListener('touchend', cancel, { passive: true });
  el.addEventListener('touchcancel', cancel, { passive: true });
  el.addEventListener('mousedown', start);
  el.addEventListener('mouseup', cancel);
  el.addEventListener('mouseleave', cancel);
}

// ─── BACKGROUND KILL PREVENTION ──────────────────────────────────────────
// When the user switches back to the tab/app after it was backgrounded,
// ensure the socket is still connected. Guard prevents reconnecting when
// already connected (avoids race conditions).
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && state.socket && !state.socket.connected) {
    state.socket.connect();
  }
});

// ─── NETWORK AWARENESS ───────────────────────────────────────────────────
window.addEventListener('offline', () => {
  const b = document.getElementById('conn-banner');
  if (b) {
    b.textContent = '📵 No network connection';
    b.style.background = '#1a0a0a';
    b.style.color = '#ff4455';
    b.style.display = 'block';
    document.body.classList.add('conn-banner-visible');
  }
});

window.addEventListener('online', () => {
  // Network came back — reconnect if needed
  if (state.socket && !state.socket.connected) {
    state.socket.connect();
  }
});

// Enter key for login
document.getElementById('username-input').focus();
