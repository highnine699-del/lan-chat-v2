/**
 * static/init.js
 * 
 * Application entry point for V2 architecture.
 * Initializes all modules and sets up the application.
 */

// Import core modules
import { socketClient } from './core/socket.js';
import { encryption } from './core/encryption.js';
import { config } from './core/config.js';
import { eventBus } from './core/eventBus.js';
import { chatState, cryptoState, uiState, mediaState } from './core/state/index.js';
import { callState } from './call/state.js';

// Import subsystem modules
import { messageHandler, messageSender, messageRenderer, decryption } from './messages/index.js';
import { roomManager, roomUI, roomComponent } from './rooms/index.js';
import { controlPlane, healthEngine, lifecycle, callUI, moodEngine, signalEmit, iceManager, mediaValidator, statsEngine } from './call/index.js';

// Import feature modules
import { typing, presence, voiceMessages, files, reactions, admin } from './features/index.js';

// Import UI components
import { ChatPage, RoomPage, CallUI, LoginPage, AdminPage } from './ui/pages/index.js';
import { MessageItem, UserItem, InputBar, Modal } from './ui/components/index.js';

// Import utils
import { dom, time, validation, storage, analytics } from './utils/index.js';

// V2 state modules own the state
// window.state is now a legacy proxy for V1 compatibility
window.state = new Proxy({}, {
  get(target, prop) {
    // Forward to chatState
    if (['socket', 'username', 'display', 'uid', 'currentChat', 'currentRoom', 'currentRoomName', 'users', 'roomList', 'typingUsers', 'unread', 'mutedUsers', 'replyTo', 'offlineQueue', 'preJoinQueue'].includes(prop)) {
      return chatState[prop];
    }
    // Forward to cryptoState
    if (['roomKeys', 'pendingDecrypt'].includes(prop)) {
      return cryptoState[prop];
    }
    // Forward to uiState
    if (['soundMuted', '_editingMsg'].includes(prop)) {
      return uiState[prop === '_editingMsg' ? 'editingMsg' : prop];
    }
    // Forward to mediaState
    if (['localStream', 'mediaRecorder', 'audioChunks', 'recordSeconds', '_recordMime', '_stopWave'].includes(prop)) {
      return mediaState[prop];
    }
    // Forward to callState
    if (['callState', 'callTarget', 'callType', 'callSessionId', 'currentCallId', 'peerConnection', 'iceCandidateBuffer', 'callPhase', 'signalingPhase', 'transportPhase', 'mediaReady', 'muted', 'camOff', 'hasTURN'].includes(prop)) {
      return callState[prop];
    }
    // Legacy properties not yet migrated
    if (['tag', 'isServerAdmin', 'sessionToken', 'msgStatus', 'chatMessages', 'callTimeout', '_mediaTimeout', '_callEndedAt', '_pendingSignals', '_lastSignalAck', 'tempIdMap'].includes(prop)) {
      return target[prop];
    }
    return undefined;
  },
  set(target, prop, value) {
    // Forward to chatState
    if (['socket', 'username', 'display', 'uid', 'currentChat', 'currentRoom', 'currentRoomName', 'users', 'roomList', 'typingUsers', 'unread', 'mutedUsers', 'replyTo', 'offlineQueue', 'preJoinQueue'].includes(prop)) {
      chatState[prop] = value;
      return true;
    }
    // Forward to cryptoState
    if (['roomKeys', 'pendingDecrypt'].includes(prop)) {
      cryptoState[prop] = value;
      return true;
    }
    // Forward to uiState
    if (['soundMuted', '_editingMsg'].includes(prop)) {
      uiState[prop === '_editingMsg' ? 'editingMsg' : prop] = value;
      return true;
    }
    // Forward to mediaState
    if (['localStream', 'mediaRecorder', 'audioChunks', 'recordSeconds', '_recordMime', '_stopWave'].includes(prop)) {
      mediaState[prop] = value;
      return true;
    }
    // Forward to callState
    if (['callState', 'callTarget', 'callType', 'callSessionId', 'currentCallId', 'peerConnection', 'iceCandidateBuffer', 'callPhase', 'signalingPhase', 'transportPhase', 'mediaReady', 'muted', 'camOff', 'hasTURN'].includes(prop)) {
      callState[prop] = value;
      return true;
    }
    // Legacy properties not yet migrated
    target[prop] = value;
    return true;
  }
});

// Save the EventTarget created by call/callUI.js (and the listener it attached).
// The call modules use dispatchEvent/addEventListener — NOT the V2 eventBus API.
// If we overwrite LANCHAT.events with eventBus the calls to dispatchEvent() will throw.
const _callEventsTarget = (window.LANCHAT && window.LANCHAT.events instanceof EventTarget)
  ? window.LANCHAT.events
  : null;

// V2 module namespace
window.LANCHAT = {
  socket: socketClient,
  encryption,
  config,
  eventBus,
  state: {
    chat: chatState,
    crypto: cryptoState,
    ui: uiState,
    media: mediaState,
  },
  messages: {
    handler: messageHandler,
    sender: messageSender,
    renderer: messageRenderer,
    decryption,
  },
  rooms: {
    manager: roomManager,
    ui: roomUI,
    component: roomComponent,
  },
  call: {
    controlPlane,
    healthEngine,
    lifecycle,
    callUI,
    moodEngine,
    signalEmit,
    iceManager,
    mediaValidator,
    statsEngine,
    state: callState,
  },
  lifecycle,
  features: {
    typing,
    presence,
    voiceMessages,
    files,
    reactions,
    admin,
  },
  ui: {
    pages: {
      ChatPage,
      LoginPage,
      AdminPage,
    },
    components: {
      MessageItem,
      UserItem,
      InputBar,
      Modal,
    },
  },
  utils: {
    dom,
    time,
    validation,
    storage,
    analytics,
  },
};

// Legacy call module bindings - the call modules (controlPlane.js, lifecycle.js, etc.)
// reference LANCHAT.state, LANCHAT.lifecycle, LANCHAT.ui, LANCHAT.mood directly
// But init.js overwrites window.LANCHAT, so we need to restore these references
// for compatibility with the legacy call module architecture
// callState is available via LANCHAT.call.state — do NOT overwrite LANCHAT.state
window.LANCHAT.lifecycle = lifecycle;
window.LANCHAT.ui = callUI;
window.LANCHAT.mood = moodEngine;
window.LANCHAT.controlPlane = controlPlane;
window.LANCHAT.health = healthEngine;
window.LANCHAT.media = mediaValidator;
window.LANCHAT.stats = statsEngine;
window.LANCHAT.ice = iceManager;
window.LANCHAT.signal = signalEmit;
// Restore the EventTarget for the legacy call modules (callUI.js, moodEngine.js,
// controlPlane.js all call LANCHAT.events.dispatchEvent / addEventListener).
// The V2 eventBus is available via ES module import; no need to put it on LANCHAT.
window.LANCHAT.events = _callEventsTarget || new EventTarget();

/**
 * Initialize the application
 */
async function init() {
  console.log('[LAN Chat V2] Initializing...');

  // Set --app-height CSS variable for accurate mobile viewport (accounts for browser chrome/keyboard)
  function setAppHeight() {
    document.documentElement.style.setProperty('--app-height', window.innerHeight + 'px');
  }
  setAppHeight();
  window.addEventListener('resize', setAppHeight);
  // Re-run on orientation change
  window.addEventListener('orientationchange', () => setTimeout(setAppHeight, 300));

  // Track initialization
  analytics.trackPageView('init');

  // Generate encryption keys
  try {
    const publicKey = await encryption.generateKeys();
    console.log('[LAN Chat V2] Encryption keys generated');
  } catch (err) {
    console.error('[LAN Chat V2] Failed to generate keys:', err);
    analytics.trackError(err, { context: 'key_generation' });
  }

  // Load saved settings
  const savedMuted = storage.getWithDefault('soundMuted', false);
  uiState.setSoundMuted(savedMuted);

  // Initialize socket
  const socket = socketClient.init();
  chatState.setSocket(socket);
  window.LANCHAT.socket = socketClient;

  // Initialize V2 modules - subscribe to eventBus
  messageHandler.init(
    (msg) => {
      // renderer.createMessageElement builds the DOM node; we insert it into #messages
      const container = document.getElementById('messages');
      if (!container) return;
      const display = chatState.getDisplay();
      const isOwn = msg.from === display;
      const el = messageRenderer.createMessageElement(msg, { isOwn });
      if (el) {
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
      }
    },
    (from, text) => console.log('[LAN Chat V2] [DEBUG] Notification from:', from, text)
  );
  roomManager.init();
  typing.init();
  presence.init();
  reactions.init();

  // Initialize V2 page components - attach event listeners to DOM
  const chatPage = new ChatPage({
    onSend: () => {
      const input = document.getElementById('msg-input');
      if (input && window.LANCHAT && window.LANCHAT.messages && window.LANCHAT.messages.sender) {
        window.LANCHAT.messages.sender.sendTextMessage(input.value, chatState.getSocket());
        input.value = '';
      }
    },
    onTyping: (value) => {
      if (window.LANCHAT && window.LANCHAT.features && window.LANCHAT.features.typing) {
        window.LANCHAT.features.typing.sendTyping(chatState.getSocket(), chatState.currentChat);
      }
    },
    onStopTyping: () => {
      if (window.LANCHAT && window.LANCHAT.features && window.LANCHAT.features.typing) {
        window.LANCHAT.features.typing.sendStopTyping(chatState.getSocket(), chatState.currentChat);
      }
    },
    onFileUpload: (file) => {
      if (window.LANCHAT && window.LANCHAT.features && window.LANCHAT.features.files) {
        window.LANCHAT.features.files.upload(file, (data, error) => {
          if (error) {
            console.error('[LAN Chat V2] File upload error:', error);
            alert(error);
          } else if (data && data.url) {
            const socket = chatState.getSocket();
            if (socket) {
              socket.emit('message', {
                type: 'file',
                url: data.url,
                name: file.name,
                size: file.size,
                room: chatState.currentRoom || 'global'
              });
            }
          }
        });
      }
    },
    onVoiceRecord: () => {
      if (window.LANCHAT && window.LANCHAT.features && window.LANCHAT.features.voiceMessages) {
        window.LANCHAT.features.voiceMessages.toggle(
          null, // onWaveformUpdate - can be null for basic toggle
          (data) => {
            // onUpload - send the uploaded voice message
            if (data && data.url) {
              const socket = chatState.getSocket();
              if (socket) {
                socket.emit('message', {
                  type: 'voice',
                  url: data.url,
                  duration: window.LANCHAT.features.voiceMessages.getDuration(),
                  room: chatState.currentRoom || 'global'
                });
              }
            }
          },
          (error) => {
            console.error('[LAN Chat V2] Voice recording error:', error);
            alert(error);
          }
        );
      }
    },
    onEmojiToggle: () => {
      console.log('[LAN Chat V2] [DEBUG] Emoji toggle - implement');
    },
  });
  chatPage.init();

  const roomPage = new RoomPage({
    onCreateRoom: (data) => {
      if (window.LANCHAT && window.LANCHAT.rooms && window.LANCHAT.rooms.manager) {
        window.LANCHAT.rooms.manager.createRoom(data, chatState.getSocket());
      }
    },
    onJoinRoom: (data) => {
      if (window.LANCHAT && window.LANCHAT.rooms && window.LANCHAT.rooms.manager) {
        window.LANCHAT.rooms.manager.joinPrivateRoom(data.roomId, data.password, chatState.getSocket());
      }
    },
    onLeaveRoom: () => {
      if (window.LANCHAT && window.LANCHAT.rooms && window.LANCHAT.rooms.manager) {
        window.LANCHAT.rooms.manager.leaveRoom(chatState.getSocket());
      }
    },
    onRotateKey: () => {
      if (window.LANCHAT && window.LANCHAT.rooms && window.LANCHAT.rooms.manager) {
        window.LANCHAT.rooms.manager.rotateRoomKey(chatState.currentRoom, chatState.getSocket());
      }
    },
    onCopyRoomId: () => {
      const roomId = chatState.currentRoom;
      if (roomId) {
        navigator.clipboard.writeText(roomId);
        const btn = document.getElementById('copy-room-id-btn');
        if (btn) {
          btn.textContent = '✓ Copied!';
          setTimeout(() => btn.textContent = '📋 Copy', 2000);
        }
      }
    },
  });
  roomPage.init();

  // ── Expose room-modal functions on window for inline HTML onclick handlers ──
  // The HTML uses onclick="closeRoomModal()" etc. which need global functions.
  // Since init.js is type="module" nothing is global by default, so we assign
  // them explicitly. They close over the local roomPage instance.
  window.closeRoomModal        = () => roomPage.hideRoomModal();
  window.submitCreateRoom      = () => roomPage.submitCreateRoom();
  window.setRoomVis            = (vis) => roomPage.setRoomVis(vis);
  window.submitJoinPrivateRoom = () => roomPage.submitJoinRoom();

  const callUI = new CallUI({
    onStartCall: (type) => {
      if (window.LANCHAT && window.LANCHAT.call && window.LANCHAT.call.controlPlane) {
        window.LANCHAT.call.controlPlane.startCall(type);
      } else {
        console.error('[LAN Chat V2] Call control plane not available');
      }
    },
    onEndCall: (reason) => {
      if (window.LANCHAT && window.LANCHAT.lifecycle) {
        window.LANCHAT.lifecycle.endCall(reason);
      }
    },
    onToggleMute: () => {
      console.log('[LAN Chat V2] [DEBUG] Toggle mute - implement');
    },
    onToggleCamera: () => {
      console.log('[LAN Chat V2] [DEBUG] Toggle camera - implement');
    },
  });
  callUI.init();

  console.log('[LAN Chat V2] [INIT COMPLETE] - All modules loaded and initialized');

  // Attach event listeners for UI elements
  attachUIListeners();
}

/**
 * Attach event listeners to UI elements
 */
function attachUIListeners() {
  console.log('[LAN Chat V2] [DEBUG] Attaching UI listeners...');

  // Login button
  const loginBtn = document.getElementById('login-btn');
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      const usernameInput = document.getElementById('username-input');
      const passwordInput = document.getElementById('password-input');
      const adminPasswordInput = document.getElementById('admin-password-input');
      
      if (usernameInput && window.LANCHAT && window.LANCHAT.login) {
        window.LANCHAT.login(
          usernameInput.value,
          passwordInput?.value,
          adminPasswordInput?.value
        );
      } else {
        console.error('[LAN Chat V2] [DEBUG] Cannot login - missing elements or LANCHAT');
      }
    });
    console.log('[LAN Chat V2] [DEBUG] Login button listener attached');
  }

  // Message input
  const msgInput = document.getElementById('msg-input');
  if (msgInput) {
    msgInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (window.LANCHAT && window.LANCHAT.messages && window.LANCHAT.messages.sender) {
          window.LANCHAT.messages.sender.sendTextMessage(msgInput.value, chatState.getSocket());
          msgInput.value = '';
        }
      }
    });
    console.log('[LAN Chat V2] [DEBUG] Message input listener attached');
  }

  // Typing indicator
  if (msgInput) {
    msgInput.addEventListener('input', (e) => {
      if (window.LANCHAT && window.LANCHAT.features && window.LANCHAT.features.typing) {
        window.LANCHAT.features.typing.sendTyping(chatState.getSocket(), chatState.currentChat);
      }
    });
  }

  // Send button
  const sendBtn = document.querySelector('.send-btn');
  if (sendBtn) {
    sendBtn.addEventListener('click', () => {
      if (msgInput && window.LANCHAT && window.LANCHAT.messages && window.LANCHAT.messages.sender) {
        window.LANCHAT.messages.sender.sendTextMessage(msgInput.value, chatState.getSocket());
        msgInput.value = '';
      }
    });
    console.log('[LAN Chat V2] [DEBUG] Send button listener attached');
  }

  // Also allow Enter key to send
  if (msgInput) {
    msgInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (window.LANCHAT && window.LANCHAT.messages && window.LANCHAT.messages.sender) {
          window.LANCHAT.messages.sender.sendTextMessage(msgInput.value, chatState.getSocket());
          msgInput.value = '';
        }
      }
    });
  }

  // Random alias generator button
  const aliasBtn = document.querySelector('.alias-gen-btn');
  const usernameInput = document.getElementById('username-input');
  if (aliasBtn && usernameInput) {
    aliasBtn.addEventListener('click', () => {
      const adjectives = ['swift','dark','neon','void','iron','echo','nova','flux','zero','apex','ghost','solar','lunar','storm','frost'];
      const nouns = ['wolf','hawk','byte','node','core','grid','pulse','wave','cipher','nexus','forge','blade','vault','spark','drift'];
      const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
      const noun = nouns[Math.floor(Math.random() * nouns.length)];
      const num = Math.floor(Math.random() * 99) + 1;
      usernameInput.value = `${adj}${noun}${num}`;
      usernameInput.focus();
    });
  }


  // ── Handle being kicked by an admin ──────────────────────────────────────
  eventBus.on('socket:admin_kicked', (data) => {
    const reason = data?.reason || 'You were removed by an admin.';
    alert(reason);
    // Reload to reset state cleanly
    window.location.reload();
  });

  console.log('[LAN Chat V2] [DEBUG] All UI listeners attached');

  // ── Feature buttons ────────────────────────────────────────────────────────

  // Emoji picker toggle
  const emojiBtn = document.getElementById('emoji-btn');
  const emojiContainer = document.getElementById('emoji-container');
  if (emojiBtn && emojiContainer) {
    emojiBtn.addEventListener('click', () => {
      const visible = emojiContainer.style.display !== 'none';
      emojiContainer.style.display = visible ? 'none' : 'block';
    });
  }

  // Attachment button → triggers file input
  const attachBtn = document.getElementById('attach-btn');
  const fileInput = document.getElementById('file-input');
  if (attachBtn && fileInput) {
    attachBtn.addEventListener('click', () => fileInput.click());
  }

  // Voice record button
  const micBtn = document.getElementById('mic-btn');
  if (micBtn) {
    micBtn.addEventListener('click', () => {
      console.log('[LAN Chat V2] [DEBUG] Mic button clicked');
      if (window.LANCHAT && window.LANCHAT.features && window.LANCHAT.features.voiceMessages) {
        console.log('[LAN Chat V2] [DEBUG] Calling voiceMessages.toggle');
        window.LANCHAT.features.voiceMessages.toggle(
          null, // onWaveformUpdate - can be null for basic toggle
          (data) => {
            // onUpload - send the uploaded voice message
            if (data && data.url) {
              const socket = chatState.getSocket();
              if (socket) {
                socket.emit('message', {
                  type: 'voice',
                  url: data.url,
                  duration: window.LANCHAT.features.voiceMessages.getDuration(),
                  room: chatState.currentRoom || 'global'
                });
              }
            }
          },
          (error) => {
            console.error('[LAN Chat V2] Voice recording error:', error);
            alert(error);
          }
        );
      } else {
        console.error('[LAN Chat V2] [DEBUG] Voice messages feature not available', {
          hasLANCHAT: !!window.LANCHAT,
          hasFeatures: !!(window.LANCHAT && window.LANCHAT.features),
          hasVoice: !!(window.LANCHAT && window.LANCHAT.features && window.LANCHAT.features.voiceMessages)
        });
      }
    });
    console.log('[LAN Chat V2] [DEBUG] Mic button listener attached');
  } else {
    console.error('[LAN Chat V2] [DEBUG] mic-btn not found');
  }

  // Mobile sidebar close
  const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  const sidebar = document.getElementById('sidebar');
  if (sidebarCloseBtn) {
    sidebarCloseBtn.addEventListener('click', () => {
      sidebar?.classList.remove('mobile-open');
      if (sidebarOverlay) sidebarOverlay.classList.remove('active');
    });
  }
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => {
      sidebar?.classList.remove('mobile-open');
      sidebarOverlay.classList.remove('active');
    });
  }

  // Mobile sidebar open
  const sidebarOpenBtn = document.getElementById('sidebar-open-btn');
  if (sidebarOpenBtn) {
    sidebarOpenBtn.addEventListener('click', () => {
      sidebar?.classList.add('mobile-open');
      if (sidebarOverlay) sidebarOverlay.classList.add('active');
    });
  }

  // New group button → show room creation modal
  const newGroupBtn = document.getElementById('new-group-btn');
  if (newGroupBtn) {
    newGroupBtn.addEventListener('click', () => {
      console.log('[LAN Chat V2] [DEBUG] New group button clicked');
      if (window.LANCHAT && window.LANCHAT.rooms && window.LANCHAT.rooms.ui) {
        console.log('[LAN Chat V2] [DEBUG] Calling showCreateModal');
        window.LANCHAT.rooms.ui.showCreateModal?.();
      } else {
        console.error('[LAN Chat V2] [DEBUG] LANCHAT.rooms.ui not available', {
          hasLANCHAT: !!window.LANCHAT,
          hasRooms: !!(window.LANCHAT && window.LANCHAT.rooms),
          hasUI: !!(window.LANCHAT && window.LANCHAT.rooms && window.LANCHAT.rooms.ui)
        });
      }
    });
    console.log('[LAN Chat V2] [DEBUG] New group button listener attached');
  } else {
    console.error('[LAN Chat V2] [DEBUG] new-group-btn not found');
  }

  // Join room by ID button → show join modal
  const joinRoomBtn = document.getElementById('join-room-btn');
  if (joinRoomBtn) {
    joinRoomBtn.addEventListener('click', () => {
      console.log('[LAN Chat V2] [DEBUG] Join room button clicked');
      if (window.LANCHAT && window.LANCHAT.rooms && window.LANCHAT.rooms.ui) {
        console.log('[LAN Chat V2] [DEBUG] Calling showJoinModal');
        window.LANCHAT.rooms.ui.showJoinModal?.();
      } else {
        console.error('[LAN Chat V2] [DEBUG] LANCHAT.rooms.ui not available');
      }
    });
    console.log('[LAN Chat V2] [DEBUG] Join room button listener attached');
  } else {
    console.error('[LAN Chat V2] [DEBUG] join-room-btn not found');
  }

  // Settings panel open/close
  const settingsBtn = document.getElementById('settings-btn');
  const settingsPanel = document.getElementById('settings-panel');
  const settingsOverlay = document.getElementById('settings-overlay');
  const settingsCloseBtn = document.getElementById('settings-close-btn');
  if (settingsBtn && settingsPanel) {
    settingsBtn.addEventListener('click', () => {
      console.log('[LAN Chat V2] [DEBUG] Settings button clicked');
      console.log('[LAN Chat V2] [DEBUG] Settings panel current display:', settingsPanel.style.display);
      console.log('[LAN Chat V2] [DEBUG] Settings panel current transform:', settingsPanel.style.transform);
      settingsPanel.style.display = 'flex';
      settingsPanel.style.transform = 'translateX(0)';
      settingsPanel.classList.add('open');
      if (settingsOverlay) settingsOverlay.style.display = 'block';
      console.log('[LAN Chat V2] [DEBUG] Settings panel after - display:', settingsPanel.style.display);
      console.log('[LAN Chat V2] [DEBUG] Settings panel after - transform:', settingsPanel.style.transform);
    });
    console.log('[LAN Chat V2] [DEBUG] Settings button listener attached');
  } else {
    console.error('[LAN Chat V2] [DEBUG] Settings button or panel not found', {
      hasBtn: !!settingsBtn,
      hasPanel: !!settingsPanel
    });
  }
  if (settingsCloseBtn) {
    settingsCloseBtn.addEventListener('click', () => {
      console.log('[LAN Chat V2] [DEBUG] Settings close button clicked');
      if (settingsPanel) {
        settingsPanel.style.transform = 'translateX(100%)';
        settingsPanel.classList.remove('open');
        setTimeout(() => settingsPanel.style.display = 'none', 300);
      }
      if (settingsOverlay) settingsOverlay.style.display = 'none';
    });
  }
  if (settingsOverlay) {
    settingsOverlay.addEventListener('click', () => {
      if (settingsPanel) {
        settingsPanel.style.transform = 'translateX(100%)';
        settingsPanel.classList.remove('open');
        setTimeout(() => settingsPanel.style.display = 'none', 300);
      }
      settingsOverlay.style.display = 'none';
    });
  }

  // ── Handle server join confirmation — transition login → chat ─────────────
  eventBus.on('socket:joined', (data) => {
    console.log('[LAN Chat V2] [DEBUG] Joined confirmed, transitioning UI:', data.display);

    // Store session data
    chatState.setDisplay(data.display);
    chatState.setUsername(data.username);
    if (data.uid) storage.set('uid', data.uid);
    if (data.session_token) storage.set('session_token', data.session_token);

    // Set default chat target so messages have somewhere to go
    if (!chatState.currentChat) {
      chatState.currentChat = 'global';
    }

    // Flip the screens
    const loginScreen = document.getElementById('login-screen');
    const app = document.getElementById('app');
    if (loginScreen) loginScreen.style.display = 'none';
    if (app) app.style.display = 'flex';

    // Show global chat, hide placeholder
    const placeholder = document.getElementById('chat-placeholder');
    const activeChat = document.getElementById('active-chat');
    if (placeholder) placeholder.style.display = 'none';
    if (activeChat) activeChat.style.display = 'flex';

    // Mark global chat as selected in sidebar
    document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
    const globalItem = document.getElementById('chat-item-global');
    if (globalItem) globalItem.classList.add('active');

    // Attach sidebar collapse listener after app is visible
    const sidebarCollapseBtn = document.getElementById('sidebar-collapse-btn');
    const sidebar = document.getElementById('sidebar');
    if (sidebarCollapseBtn && sidebar) {
      sidebarCollapseBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
      });
      console.log('[LAN Chat V2] [DEBUG] Sidebar collapse listener attached');
    }
  });

  // ── Handle server errors on login ─────────────────────────────────────────
  eventBus.on('socket:error', (data) => {
    const loginScreen = document.getElementById('login-screen');
    if (loginScreen && loginScreen.style.display !== 'none') {
      // Still on login screen — show the error there
      const errEl = loginScreen.querySelector('.login-error') || loginScreen.querySelector('[class*="error"]');
      if (errEl) {
        errEl.textContent = data.message || 'Connection error';
        errEl.style.display = 'block';
      } else {
        alert(data.message || 'Login error');
      }
    }
  });
}

/**
 * Login to the chat
 * @param {string} username - Username
 * @param {string} password - Server password (optional)
 * @param {string} adminPassword - Admin password (optional)
 */
async function login(username, password, adminPassword) {
  console.log('[LAN Chat V2] [DEBUG] Logging in as:', username);

  // Validate username
  const result = validation.validateUsername(username);
  if (!result.valid) {
    console.error('[LAN Chat V2] [DEBUG] Invalid username:', result.error);
    return;
  }

  // Store username
  chatState.setUsername(username);
  chatState.setDisplay(username);

  console.log('[LAN Chat V2] [DEBUG] Emitting join event with:', { username, hasPublicKey: !!encryption.myPublicKeyJwk, hasPassword: !!password, hasAdminPassword: !!adminPassword });

  // Emit join event
  chatState.getSocket().emit('join', {
    username,
    password: password || '',
    admin_password: adminPassword || '',
    publicKey: encryption.myPublicKeyJwk,
    uid: storage.get('uid') || '',
    session_token: storage.get('session_token') || '',
  });

  analytics.trackAction('login', { username });
}

/**
 * Logout from the chat
 */
function logout() {
  console.log('[LAN Chat V2] Logging out...');

  const socket = chatState.getSocket();
  if (socket) {
    socket.disconnect();
  }

  // Clear state
  chatState.setDisplay(null);
  chatState.setUsername(null);

  analytics.trackAction('logout');

  // Reload page
  window.location.reload();
}

/**
 * Export public API
 */
window.LANCHAT.init = init;
window.LANCHAT.login = login;
window.LANCHAT.logout = logout;

// Auto-initialize on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
