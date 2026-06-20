/**
 * rooms/roomManager.js
 * 
 * Room management - CRUD operations, join/leave, key rotation.
 * V2: Subscribes to eventBus instead of direct socket.on
 */

import { encryption } from '../core/encryption.js';
import { chatState } from '../core/state/chatState.js';
import { cryptoState } from '../core/state/cryptoState.js';
import { eventBus } from '../core/eventBus.js';

export const roomManager = {
  _initialized: false,

  /**
   * Initialize room manager - subscribe to eventBus events
   */
  init() {
    if (this._initialized) return;

    // Subscribe to socket events via eventBus
    eventBus.on('socket:room_created', (data) => {
      this.handleRoomCreated(data);
    });

    eventBus.on('socket:room_joined', (data) => {
      this.handleRoomJoined(data);
    });

    eventBus.on('socket:room_left', (data) => {
      this.handleRoomLeft(data);
    });

    eventBus.on('socket:room_list', (data) => {
      this.handleRoomList(data);
    });

    eventBus.on('socket:room_key', (data) => {
      this.handleRoomKey(data);
    });

    eventBus.on('socket:room_members', (data) => {
      this.handleRoomMembers(data);
    });

    eventBus.on('socket:room_frozen', (data) => {
      this.handleRoomFrozen(data);
    });

    eventBus.on('socket:room_deleted', (data) => {
      this.handleRoomDeleted(data);
    });

    this._initialized = true;
    console.log('[LAN Chat V2] [DEBUG] roomManager initialized and subscribed to eventBus');
  },
  /**
   * Create a new room
   * @param {Object} options - Room options { name, visibility, password, ttl, requireApproval }
   * @param {Object} socket - Socket instance
   * @param {Function} onCreated - Callback when room is created
   */
  async createRoom(options, socket, onCreated) {
    const { name, visibility, password, ttl, requireApproval } = options;

    // Hash password before sending
    const hashed = await this._hashPassword(visibility === 'private' ? password : '');

    socket.emit('room:create', {
      name,
      visibility,
      password: hashed,
      ttl,
      require_approval: requireApproval,
    });

    eventBus.emit('room:creating', options);
  },

  /**
   * Join a public room
   * @param {string} roomId - Room ID
   * @param {Object} socket - Socket instance
   */
  joinPublicRoom(roomId, socket) {
    socket.emit('room:join', { room_id: roomId });
    eventBus.emit('room:joining', { roomId, type: 'public' });
  },

  /**
   * Join a private room
   * @param {string} roomId - Room ID
   * @param {string} password - Room password
   * @param {Object} socket - Socket instance
   */
  async joinPrivateRoom(roomId, password, socket) {
    const hashed = await this._hashPassword(password);
    socket.emit('room:join_private', { room_id: roomId, password: hashed });
    eventBus.emit('room:joining', { roomId, type: 'private' });
  },

  /**
   * Leave current room
   * @param {Object} socket - Socket instance
   */
  leaveRoom(socket) {
    if (chatState.currentRoom) {
      socket.emit('room:leave', { room_id: chatState.currentRoom });
      eventBus.emit('room:leaving', { roomId: chatState.currentRoom });
    }
  },

  /**
   * Rotate room key
   * @param {string} roomId - Room ID
   * @param {Object} socket - Socket instance
   */
  async rotateRoomKey(roomId, socket) {
    try {
      await encryption.generateRoomKey(roomId);
      const jwk = await encryption.exportRoomKey(roomId);
      socket.emit('room:key', { room_id: roomId, key: jwk });
      eventBus.emit('room:key_rotated', { roomId });
    } catch (err) {
      console.error('[RoomManager] Key rotation failed:', err);
      eventBus.emit('room:key_rotation_failed', { roomId, error: err.message });
    }
  },

  /**
   * Knock on a private room
   * @param {string} roomId - Room ID
   * @param {Object} socket - Socket instance
   */
  knockRoom(roomId, socket) {
    socket.emit('room:knock', { room_id: roomId });
    eventBus.emit('room:knocking', { roomId });
  },

  /**
   * Handle room created event
   * @param {Object} data - Room data
   */
  async handleRoomCreated(data) {
    const { room_id, name, visibility, key } = data;

    // Store room key if provided
    if (key) {
      await encryption.importRoomKey(room_id, key);
    }

    // Update state
    chatState.setCurrentRoom(room_id, name);
    if (!chatState.messages[room_id]) chatState.messages[room_id] = [];

    // Creator generates the room key and sends it to the server
    // so it can be redistributed to members who join later
    try {
      const socket = chatState.getSocket();
      if (socket) {
        await this.rotateRoomKey(room_id, socket);
      }
    } catch (err) {
      console.error('[RoomManager] Failed to generate initial room key:', err);
    }

    eventBus.emit('room:created', data);
  },

  /**
   * Handle room joined event
   * @param {Object} data - Room data
   */
  async handleRoomJoined(data) {
    // server sends 'session_key' (not 'key') in room:joined
    const { room_id, name, members, session_key, key } = data;
    const roomKey = session_key || key;  // accept either field name

    // Store room key so messages can be encrypted/decrypted
    if (roomKey) {
      await encryption.importRoomKey(room_id, roomKey);
    }

    // Update state
    chatState.setCurrentRoom(room_id, name);
    if (!chatState.messages[room_id]) chatState.messages[room_id] = [];

    eventBus.emit('room:joined', data);
  },

  /**
   * Handle room left event
   * @param {Object} data - Room data
   */
  handleRoomLeft(data) {
    const { room_id } = data;

    // Update state
    chatState.setCurrentRoom(null, '');
    chatState.setCurrentChat('global');

    eventBus.emit('room:left', data);
  },

  /**
   * Handle room key event
   * @param {Object} data - Key data
   */
  async handleRoomKey(data) {
    const { room_id, key, rotated_by } = data;

    // Import room key
    await encryption.importRoomKey(room_id, key);

    // Process pending messages
    const pending = cryptoState.flushPendingDecrypt(room_id);
    if (pending.length) {
      eventBus.emit('room:pending_decrypt', { roomId: room_id, messages: pending });
    }

    eventBus.emit('room:key_received', data);
  },

  /**
   * Handle room list event
   * @param {Array} rooms - Room list
   */
  handleRoomList(rooms) {
    chatState.setRoomList(rooms);
    eventBus.emit('room:list', rooms);
  },

  /**
   * Handle room members event
   * @param {Object} data - Members data
   */
  handleRoomMembers(data) {
    const { room_id, members } = data;
    if (chatState.currentRoom === room_id) {
      eventBus.emit('room:members', data);
    }
  },

  /**
   * Handle room frozen event
   * @param {Object} data - Frozen data
   */
  handleRoomFrozen(data) {
    eventBus.emit('room:frozen', data);
  },

  /**
   * Handle room deleted event
   * @param {Object} data - Deleted data
   */
  handleRoomDeleted(data) {
    const { room_id } = data;

    // Clean up state
    delete chatState.messages[room_id];
    cryptoState.deleteRoomKey(room_id);

    if (chatState.currentRoom === room_id) {
      chatState.setCurrentRoom(null, '');
      chatState.setCurrentChat('global');
    }

    eventBus.emit('room:deleted', data);
  },

  /**
   * Hash password
   * @private
   * @param {string} password - Password to hash
   * @returns {Promise<string>} Hashed password
   */
  async _hashPassword(password) {
    if (!password) return '';
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(password));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }
};
