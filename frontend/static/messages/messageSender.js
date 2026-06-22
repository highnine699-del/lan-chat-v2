/**
 * messages/messageSender.js
 * 
 * Message sending with encryption, optimistic rendering, and offline queue.
 */

import { encryption } from '../core/encryption.js';
import { chatState } from '../core/state/chatState.js';
import { cryptoState } from '../core/state/cryptoState.js';
import { eventBus } from '../core/eventBus.js';

export const messageSender = {
  /**
   * Send a text message
   * @param {string} text - Message text
   * @param {Object} socket - Socket instance
   * @param {Function} onOptimisticRender - Callback for optimistic render
   * @param {Function} onStatusUpdate - Callback for status updates
   */
  async sendTextMessage(text, socket, onOptimisticRender, onStatusUpdate) {
    if (!text.trim()) return;

    const currentChat = chatState.currentChat;
    const currentRoom = chatState.currentRoom;
    const replyTo = chatState.replyTo;
    const display = this._getDisplay();

    // Clear reply-to
    chatState.clearReplyTo();

    // Generate temp ID for delivery tracking
    const tempId = 'tmp_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);

    // Optimistic message
    const localMsg = {
      type: 'text',
      from: display,
      color: '',
      text,
      time: Date.now(),
      to: currentChat,
      msg_id: tempId,
      _local: true,
      _origText: text,
      reply_to: replyTo,
    };

    // Add to state and render optimistically
    chatState.addMessage(localMsg);
    if (onOptimisticRender) onOptimisticRender(localMsg);

    // Build payload with encryption
    let payload = { to: currentChat, text, _tempId: tempId, reply_to: replyTo };

    // Encrypt private DMs
    if (currentChat !== 'global' && !currentRoom) {
      const ct = await encryption.encrypt(text, currentChat);
      if (ct) { payload.encrypted = ct; payload.text = '🔒'; }
    }

    // Encrypt room messages
    if (currentRoom && cryptoState.getRoomKey(currentRoom)) {
      const ct = await encryption.encryptRoom(text, currentRoom);
      if (ct) { payload.encrypted = ct; payload.text = '🔒'; }
    }

    // Send or queue
    if (!socket || !socket.connected) {
      chatState.addToOfflineQueue(payload);
      if (onStatusUpdate) onStatusUpdate(tempId, 'failed');
    } else {
      socket.emit('send_message', payload);
      socket.emit('stop_typing', { to: currentChat });

      // Delivery timeout
      const deliveryTimer = setTimeout(() => {
        if (onStatusUpdate) onStatusUpdate(tempId, 'failed', null, payload);
      }, 8000);

      // Store timer for cancellation
      if (onStatusUpdate) onStatusUpdate(tempId, 'sending', null, null, deliveryTimer);
    }
  },

  /**
   * Retry a failed message
   * @param {string} tempId - Temporary message ID
   * @param {Object} payload - Message payload
   * @param {Object} socket - Socket instance
   * @param {Function} onStatusUpdate - Callback for status updates
   */
  retryMessage(tempId, payload, socket, onStatusUpdate) {
    if (!socket || !socket.connected) return;

    socket.emit('send_message', payload);
    if (onStatusUpdate) onStatusUpdate(tempId, 'sending');

    // Reset delivery timeout
    const timer = setTimeout(() => {
      if (onStatusUpdate) onStatusUpdate(tempId, 'failed', null, payload);
    }, 8000);

    if (onStatusUpdate) onStatusUpdate(tempId, 'sending', null, null, timer);
  },

  /**
   * Send a voice message (uploaded audio file)
   * @param {Object} data - Upload response { url }
   * @param {number} duration - Duration in seconds
   * @param {Object} socket - Socket instance
   * @param {Function} onError - Error callback
   */
  async sendVoice(data, duration, socket, onError) {
    if (!data?.url || !socket) {
      if (onError) onError('Upload failed');
      return;
    }

    socket.emit('send_file', {
      to: chatState.currentChat,
      url: data.url,
      name: `voice_${Date.now()}.webm`,
      file_type: 'audio/webm',
      duration,
    });
  },

  /**
   * Send a file
   * @param {File} file - File to send
   * @param {Object} socket - Socket instance
   * @param {Function} onUploadProgress - Progress callback
   * @param {Function} onError - Error callback
   */
  async sendFile(file, socket, onUploadProgress, onError) {
    const formData = new FormData();
    formData.append('file', file);

    eventBus.emit('file:uploading', file);

    try {
      const res = await fetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok) {
        eventBus.emit('file:upload_failed', data.error || `Server error ${res.status}`);
        if (onError) onError('Upload failed: ' + (data.error || `Server error ${res.status}`));
        return;
      }

      eventBus.emit('file:uploaded', data);

      socket.emit('send_file', {
        to: chatState.currentChat,
        url: data.url,
        name: data.name || file.name,
        file_type: file.type
      });
    } catch (err) {
      eventBus.emit('file:upload_error', err.message);
      if (onError) onError('Upload failed: ' + err.message);
    }
  },

  /**
   * Flush offline queue
   * @param {Object} socket - Socket instance
   * @param {Function} onStatusUpdate - Status update callback
   */
  flushOfflineQueue(socket, onStatusUpdate) {
    const queued = chatState.flushOfflineQueue();
    queued.forEach(payload => {
      socket.emit('send_message', payload);
    });
  },

  /**
   * Get display name
   * @private
   * @returns {string} Display name
   */
  _getDisplay() {
    // This should come from identity state
    return window.state?.display || 'Anonymous';
  }
};
