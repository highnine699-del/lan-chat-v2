/**
 * messages/messageHandler.js
 * 
 * Message receiving and processing.
 * Handles decryption, state updates, and triggers rendering.
 * V2: Subscribes to eventBus instead of direct socket.on
 */

import { decryption } from './decryption.js';
import { encryption } from '../core/encryption.js';
import { renderer } from './renderer.js';
import { chatState } from '../core/state/chatState.js';
import { cryptoState } from '../core/state/cryptoState.js';
import { eventBus } from '../core/eventBus.js';

export const messageHandler = {
  _initialized: false,
  _onRender: null,
  _onNotify: null,

  /**
   * Initialize message handler - subscribe to eventBus events
   * @param {Function} onRender - Render callback
   * @param {Function} onNotify - Notification callback
   */
  init(onRender, onNotify) {
    if (this._initialized) return;
    
    this._onRender = onRender;
    this._onNotify = onNotify;

    // Subscribe to socket events via eventBus
    eventBus.on('socket:message', (data) => {
      this.handleMessage(data, chatState.getDisplay(), onRender, onNotify);
    });

    eventBus.on('socket:message_history', (data) => {
      this.handleHistory(data, chatState.getDisplay(), onRender);
    });

    eventBus.on('socket:message_ack', (data) => {
      this.handleMessageAck(data, (tempId, status, msgId) => {
        if (onRender) onRender({ tempId, status, msgId });
      });
    });

    eventBus.on('socket:message_edited', (data) => {
      this.handleMessageEdit(data, onRender);
    });

    eventBus.on('socket:message_deleted', (data) => {
      this.handleMessageDelete(data, onRender);
    });

    eventBus.on('socket:message_seen', (data) => {
      this.handleMessageSeen(data);
    });

    this._initialized = true;
    console.log('[LAN Chat V2] [DEBUG] messageHandler initialized and subscribed to eventBus');
  },
  /**
   * Handle incoming message
   * @param {Object} msg - Message object
   * @param {string} myDisplay - My display name
   * @param {Function} onRender - Render callback
   * @param {Function} onNotify - Notification callback
   */
  async handleMessage(msg, myDisplay, onRender, onNotify) {
    console.log('[LAN Chat V2] [DEBUG] handleMessage called:', { from: msg.from, to: msg.to, hasText: !!msg.text });

    // Buffer if identity not confirmed
    if (!myDisplay) {
      console.log('[LAN Chat V2] [DEBUG] Buffering message - identity not confirmed');
      chatState.addToPreJoinQueue(msg);
      return;
    }

    // Decrypt if needed
    const decrypted = await decryption.decryptMessage(
      msg,
      chatState.currentRoom,
      cryptoState.roomKeys,
      myDisplay
    );

    // Buffer if room key not available
    if (decrypted.encrypted && !decryption.canDecrypt(decrypted, chatState.currentRoom, cryptoState.roomKeys)) {
      console.log('[LAN Chat V2] [DEBUG] Buffering message - room key not available');
      const placeholder = { ...decrypted, text: '🔒 waiting for encryption key...', _pending: true };
      chatState.addMessage(placeholder);
      cryptoState.addToPendingDecrypt(decrypted.to, decrypted);
      if (onRender) onRender(placeholder);
      return;
    }

    // Add to state
    chatState.addMessage(decrypted);

    // Determine whether this message belongs to the view the user currently has
    // open.  We evaluate BEFORE calling onRender so onNotify is not triggered
    // for conversations the user is actively looking at.
    const _cc  = chatState.currentChat;
    const _cr  = chatState.currentRoom;
    const isInCurrentView = (
      (decrypted.to === 'global' && _cc === 'global') ||
      (_cr && decrypted.to === _cr) ||
      (!_cr && _cc !== 'global' && (decrypted.from === _cc || decrypted.to === _cc))
    );

    // Render — the callback in init.js does its own view-guard so this is safe
    if (onRender) onRender(decrypted);

    // Notify only when the message is NOT already visible to the user
    if (decrypted.from !== myDisplay && !isInCurrentView && onNotify) {
      onNotify(decrypted.from, decrypted.text || decrypted.name || '[File]');
    }

    // Emit event
    eventBus.emit('message:received', decrypted);
    console.log('[LAN Chat V2] [DEBUG] Message processed and emitted:', { from: decrypted.from, to: decrypted.to });
  },

  /**
   * Handle message history
   * @param {Array} messages - Message array
   * @param {string} myDisplay - My display name
   * @param {Function} onRender - Render callback
   */
  async handleHistory(messages, myDisplay, onRender) {
    for (const msg of messages) {
      await this.handleMessage(msg, myDisplay, onRender, null);
    }
  },

  /**
   * Handle message ACK
   * @param {Object} data - ACK data { tempId, msg_id }
   * @param {Function} onStatusUpdate - Status update callback
   */
  handleMessageAck(data, onStatusUpdate) {
    const { tempId, msg_id } = data;
    if (!tempId || !msg_id) return;

    // Update message in state
    for (const arr of Object.values(chatState.messages)) {
      const idx = arr.findIndex(m => m.msg_id === tempId && m._local);
      if (idx !== -1) {
        arr[idx] = { ...arr[idx], msg_id, _local: false };
        break;
      }
    }

    // Update status
    if (onStatusUpdate) onStatusUpdate(tempId, 'delivered', msg_id);

    // Emit event
    eventBus.emit('message:ack', { tempId, msg_id });
  },

  /**
   * Handle message edit
   * @param {Object} data - Edit data
   * @param {Function} onRender - Render callback
   */
  async handleMessageEdit(data, onRender) {
    const { msg_id, text, encrypted, to } = data;

    // Update in state
    for (const arr of Object.values(chatState.messages)) {
      const m = arr.find(m => m.msg_id === msg_id);
      if (m) {
        if (encrypted) {
          let plain = text;
          if (to && cryptoState.getRoomKey(to)) {
            plain = await encryption.decryptRoom(encrypted, to) || '🔒 [decryption failed]';
          } else if (to && to !== 'global') {
            const peer = m.from === window.state?.display ? to : m.from;
            plain = await encryption.decrypt(encrypted, peer) || '🔒 [decryption failed]';
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
    if (onRender) onRender({ msg_id, text: data._plaintext || text, edited: true });

    eventBus.emit('message:edited', data);
  },

  /**
   * Handle message delete
   * @param {Object} data - Delete data
   * @param {Function} onRender - Render callback
   */
  handleMessageDelete(data, onRender) {
    const { msg_id } = data;

    // Soft-delete in state
    for (const arr of Object.values(chatState.messages)) {
      const m = arr.find(m => m.msg_id === msg_id);
      if (m) {
        m.deleted = true;
        m.text = '🗑️ This message was deleted';
        break;
      }
    }

    // Update DOM
    if (onRender) onRender({ msg_id, deleted: true });

    eventBus.emit('message:deleted', data);
  },

  /**
   * Handle message seen
   * @param {Object} data - Seen data
   * @param {Function} onStatusUpdate - Status update callback
   */
  handleMessageSeen(data, onStatusUpdate) {
    if (!Array.isArray(data.msg_ids)) return;

    data.msg_ids.forEach(id => {
      if (onStatusUpdate) onStatusUpdate(id, 'seen');
    });

    eventBus.emit('message:seen', data);
  },

  /**
   * Process pending decrypt queue when room key arrives
   * @param {string} roomId - Room ID
   * @param {Function} onRender - Render callback
   */
  async flushPendingDecrypt(roomId, onRender) {
    const pending = cryptoState.flushPendingDecrypt(roomId);
    if (!pending.length) return;

    // Remove placeholders from state
    const chatArr = chatState.getMessages(roomId);
    if (chatArr) {
      const toRemove = chatArr.filter(m => m._pending);
      toRemove.forEach(m => {
        if (m.msg_id) {
          const el = document.querySelector(`[data-msg-id="${m.msg_id}"]`);
          if (el) el.remove();
        }
      });
      chatState.messages[roomId] = chatArr.filter(m => !m._pending);
    }

    // Re-render buffered messages
    for (const msg of pending) {
      await this.handleMessage(msg, window.state?.display, onRender, null);
    }
  }
};
