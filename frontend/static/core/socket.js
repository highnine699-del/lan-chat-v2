/**
 * core/socket.js
 *
 * Socket.IO client — single source of truth for all server events.
 * Every server emission is received here and re-emitted on the eventBus
 * so the rest of the app never has to touch the raw socket directly.
 */

import { eventBus } from './eventBus.js';

export const socketClient = {
  socket: null,

  init() {
    console.log('[LAN Chat V2] Initializing socket client...');

    // When running over ngrok skip polling — ngrok intercepts HTTP polling
    // with a browser warning page (returns 400).  WebSocket-only avoids that.
    const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';

    this.socket = io({
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 500,
      reconnectionDelayMax: 5000,
      transports: isLocal ? ['polling', 'websocket'] : ['websocket'],
      extraHeaders: isLocal ? {} : { 'ngrok-skip-browser-warning': 'true' },
    });

    // ── Connection lifecycle ──────────────────────────────────────────────────
    this.socket.on('connect', () => {
      console.log('[LAN Chat V2] Socket connected');
      eventBus.emit('socket:connected');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('[LAN Chat V2] Socket disconnected:', reason);
      eventBus.emit('socket:disconnected', { reason });
    });

    this.socket.on('reconnect', (n) => {
      console.log('[LAN Chat V2] Socket reconnected after', n, 'attempts');
      eventBus.emit('socket:reconnected', { attemptNumber: n });
    });

    this.socket.on('reconnect_attempt', (n) => {
      eventBus.emit('socket:reconnect_attempt', { attemptNumber: n });
    });

    this.socket.on('reconnect_error', (error) => {
      eventBus.emit('socket:reconnect_error', { error });
    });

    this.socket.on('reconnect_failed', () => {
      eventBus.emit('socket:reconnect_failed');
    });

    // ── Auth / presence ───────────────────────────────────────────────────────
    this.socket.on('joined', (data) => {
      eventBus.emit('socket:joined', data);
    });

    this.socket.on('user_list', (data) => {
      eventBus.emit('socket:user_list', data);
    });

    this.socket.on('system_message', (data) => {
      eventBus.emit('socket:system_message', data);
    });

    this.socket.on('error', (data) => {
      eventBus.emit('socket:error', data);
    });

    this.socket.on('cooldown', (data) => {
      eventBus.emit('socket:cooldown', data);
    });

    this.socket.on('sync_reply', (data) => {
      eventBus.emit('socket:sync_reply', data);
    });

    this.socket.on('user:presence', (data) => {
      eventBus.emit('socket:user_presence', data);
    });

    this.socket.on('persona_switched', (data) => {
      eventBus.emit('socket:persona_switched', data);
    });

    // ── Messages ──────────────────────────────────────────────────────────────
    this.socket.on('new_message', (data) => {
      eventBus.emit('socket:message', data);
    });

    this.socket.on('message_history', (data) => {
      eventBus.emit('socket:message_history', data);
    });

    this.socket.on('message_ack', (data) => {
      eventBus.emit('socket:message_ack', data);
    });

    // These were missing — backend emits message:edited, message:deleted, message:seen
    this.socket.on('message:edited', (data) => {
      eventBus.emit('socket:message_edited', data);
    });

    this.socket.on('message:deleted', (data) => {
      eventBus.emit('socket:message_deleted', data);
    });

    this.socket.on('message:seen', (data) => {
      eventBus.emit('socket:message_seen', data);
    });

    this.socket.on('hide_message', (data) => {
      eventBus.emit('socket:hide_message', data);
    });

    this.socket.on('vote_count', (data) => {
      eventBus.emit('socket:vote_count', data);
    });

    // ── Typing ────────────────────────────────────────────────────────────────
    this.socket.on('typing', (data) => {
      eventBus.emit('socket:typing', data);
    });

    this.socket.on('stop_typing', (data) => {
      eventBus.emit('socket:stop_typing', data);
    });

    // ── Rooms ─────────────────────────────────────────────────────────────────
    this.socket.on('room:created', (data) => {
      eventBus.emit('socket:room_created', data);
    });

    // room:joined was missing — roomManager subscribes to this
    this.socket.on('room:joined', (data) => {
      eventBus.emit('socket:room_joined', data);
    });

    this.socket.on('room:left', (data) => {
      eventBus.emit('socket:room_left', data);
    });

    this.socket.on('room:list', (data) => {
      eventBus.emit('socket:room_list', data);
    });

    this.socket.on('room:key', (data) => {
      eventBus.emit('socket:room_key', data);
    });

    this.socket.on('room:members', (data) => {
      eventBus.emit('socket:room_members', data);
    });

    this.socket.on('room:frozen', (data) => {
      eventBus.emit('socket:room_frozen', data);
    });

    this.socket.on('room:deleted', (data) => {
      eventBus.emit('socket:room_deleted', data);
    });

    this.socket.on('room:knock', (data) => {
      eventBus.emit('socket:room_knock', data);
    });

    this.socket.on('room:knock_pending', (data) => {
      eventBus.emit('socket:room_knock_pending', data);
    });

    this.socket.on('room:join_approved', (data) => {
      eventBus.emit('socket:room_join_approved', data);
    });

    this.socket.on('room:knock_denied', (data) => {
      eventBus.emit('socket:room_knock_denied', data);
    });

    this.socket.on('room:incoming_call', (data) => {
      eventBus.emit('socket:room_incoming_call', data);
    });

    // ── Encryption key exchange ───────────────────────────────────────────────
    this.socket.on('all_keys', (data) => {
      eventBus.emit('socket:all_keys', data);
    });

    this.socket.on('peer_key', (data) => {
      eventBus.emit('socket:peer_key', data);
    });

    // ── Admin ─────────────────────────────────────────────────────────────────
    this.socket.on('admin:kicked', (data) => {
      eventBus.emit('socket:admin_kicked', data);
    });

    // ── WebRTC / calls ────────────────────────────────────────────────────────
    this.socket.on('webrtc_signal', (data) => {
      eventBus.emit('socket:webrtc_signal', data);
    });

    this.socket.on('call_signal', (data) => {
      eventBus.emit('socket:call_signal', data);
    });

    this.socket.on('call:phase_reply', (data) => {
      eventBus.emit('socket:call_phase_reply', data);
    });

    this.socket.on('incoming-call', (data) => {
      eventBus.emit('socket:incoming_call', data);
    });

    this.socket.on('call-started', (data) => {
      eventBus.emit('socket:call_started', data);
    });

    this.socket.on('call-ended', (data) => {
      eventBus.emit('socket:call_ended', data);
    });

    console.log('[LAN Chat V2] Socket client initialized');
    return this.socket;
  },

  getSocket() {
    return this.socket;
  },

  isConnected() {
    return !!(this.socket && this.socket.connected);
  },

  disconnect() {
    if (this.socket) this.socket.disconnect();
  },

  reconnect() {
    if (this.socket) this.socket.connect();
  },
};
