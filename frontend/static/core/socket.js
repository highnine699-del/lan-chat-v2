/**
 * core/socket.js
 * 
 * Socket.IO client initialization.
 * Handles connection setup with proper transport configuration for ngrok compatibility.
 * V2 socket ownership - single socket.on handlers that emit to eventBus.
 */

import { eventBus } from './eventBus.js';

export const socketClient = {
  socket: null,

  /**
   * Initialize Socket.IO connection
   * @returns {Object} Socket.IO instance
   */
  init() {
    console.log('[LAN Chat V2] [DEBUG] Initializing socket client...');

    // When running over ngrok (or any non-localhost origin), skip the polling
    // transport entirely. ngrok intercepts polling HTTP requests with a browser
    // warning page (returns 400), which breaks the Socket.IO handshake.
    // WebSocket-only avoids that path and connects cleanly.
    const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    
    this.socket = io({
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 500,
      reconnectionDelayMax: 5000,
      transports: isLocal ? ['polling', 'websocket'] : ['websocket'],
      extraHeaders: isLocal ? {} : { 'ngrok-skip-browser-warning': 'true' },
    });

    // V2 socket lifecycle events - emit to eventBus
    this.socket.on('connect', () => {
      console.log('[LAN Chat V2] [DEBUG] Socket connected');
      eventBus.emit('socket:connected');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('[LAN Chat V2] [DEBUG] Socket disconnected:', reason);
      eventBus.emit('socket:disconnected', { reason });
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('[LAN Chat V2] [DEBUG] Socket reconnected after', attemptNumber, 'attempts');
      eventBus.emit('socket:reconnected', { attemptNumber });
    });

    this.socket.on('reconnect_attempt', (attemptNumber) => {
      console.log('[LAN Chat V2] [DEBUG] Socket reconnect attempt:', attemptNumber);
      eventBus.emit('socket:reconnect_attempt', { attemptNumber });
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('[LAN Chat V2] [DEBUG] Socket reconnect error:', error);
      eventBus.emit('socket:reconnect_error', { error });
    });

    this.socket.on('reconnect_failed', () => {
      console.error('[LAN Chat V2] [DEBUG] Socket reconnect failed');
      eventBus.emit('socket:reconnect_failed');
    });

    // V2 application-level socket events - emit to eventBus
    // These replace V1 socket handlers
    // Event names match backend Socket.IO handlers
    this.socket.on('new_message', (data) => {
      eventBus.emit('socket:message', data);
    });

    this.socket.on('joined', (data) => {
      eventBus.emit('socket:joined', data);
    });

    this.socket.on('user_list', (data) => {
      eventBus.emit('socket:user_list', data);
    });

    this.socket.on('system_message', (data) => {
      eventBus.emit('socket:system_message', data);
    });

    this.socket.on('typing', (data) => {
      eventBus.emit('socket:typing', data);
    });

    this.socket.on('stop_typing', (data) => {
      eventBus.emit('socket:stop_typing', data);
    });

    this.socket.on('room:created', (data) => {
      eventBus.emit('socket:room_created', data);
    });

    this.socket.on('room:list', (data) => {
      eventBus.emit('socket:room_list', data);
    });

    this.socket.on('room:key', (data) => {
      eventBus.emit('socket:room_key', data);
    });

    this.socket.on('room:left', (data) => {
      eventBus.emit('socket:room_left', data);
    });

    this.socket.on('room:members', (data) => {
      eventBus.emit('socket:room_members', data);
    });

    this.socket.on('room:frozen', (data) => {
      eventBus.emit('socket:room_frozen', data);
    });

    this.socket.on('message_ack', (data) => {
      eventBus.emit('socket:message_ack', data);
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

    this.socket.on('all_keys', (data) => {
      eventBus.emit('socket:all_keys', data);
    });

    this.socket.on('peer_key', (data) => {
      eventBus.emit('socket:peer_key', data);
    });

    this.socket.on('message_history', (data) => {
      eventBus.emit('socket:message_history', data);
    });

    this.socket.on('error', (data) => {
      eventBus.emit('socket:error', data);
    });

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

    console.log('[LAN Chat V2] [DEBUG] Socket client initialized, transports:', isLocal ? 'polling,websocket' : 'websocket');

    return this.socket;
  },

  /**
   * Get the socket instance
   * @returns {Object|null} Socket.IO instance or null
   */
  getSocket() {
    return this.socket;
  },

  /**
   * Check if socket is connected
   * @returns {boolean} True if connected
   */
  isConnected() {
    return !!(this.socket && this.socket.connected);
  },

  /**
   * Disconnect the socket
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  },

  /**
   * Reconnect the socket
   */
  reconnect() {
    if (this.socket) {
      this.socket.connect();
    }
  }
};
