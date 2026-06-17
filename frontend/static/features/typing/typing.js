/**
 * features/typing/typing.js
 * 
 * Typing indicator feature.
 * Handles sending and receiving typing indicators.
 * V2: Subscribes to eventBus instead of direct socket.on
 */

import { chatState } from '../../core/state/chatState.js';
import { eventBus } from '../../core/eventBus.js';

export const typing = {
  _initialized: false,
  typingTimeout: null,

  /**
   * Initialize typing feature - subscribe to eventBus events
   */
  init() {
    if (this._initialized) return;

    // Subscribe to socket events via eventBus
    eventBus.on('socket:typing', (data) => {
      this.handleTyping(data, chatState.getDisplay());
    });

    eventBus.on('socket:stop_typing', (data) => {
      this.handleStopTyping(data, chatState.getDisplay());
    });

    this._initialized = true;
    console.log('[LAN Chat V2] [DEBUG] typing initialized and subscribed to eventBus');
  },

  /**
   * Send typing indicator
   * @param {Object} socket - Socket instance
   * @param {string} chatId - Chat ID
   */
  sendTyping(socket, chatId) {
    socket.emit('typing', { to: chatId });
    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.sendStopTyping(socket, chatId);
    }, 1500);
  },

  /**
   * Send stop typing indicator
   * @param {Object} socket - Socket instance
   * @param {string} chatId - Chat ID
   */
  sendStopTyping(socket, chatId) {
    socket.emit('stop_typing', { to: chatId });
  },

  /**
   * Handle typing event
   * @param {Object} data - Typing data { username, to }
   * @param {string} myDisplay - My display name
   */
  handleTyping(data, myDisplay) {
    if (data.username === myDisplay) return;
    const chatId = data.to === 'global' ? 'global' : data.username;
    chatState.addTypingUser(chatId, data.username);
    eventBus.emit('typing:started', { chatId, username: data.username });
  },

  /**
   * Handle stop typing event
   * @param {Object} data - Stop typing data { username, to }
   * @param {string} myDisplay - My display name
   */
  handleStopTyping(data, myDisplay) {
    const chatId = data.to === 'global' ? 'global' : data.username;
    chatState.removeTypingUser(chatId, data.username);
    eventBus.emit('typing:stopped', { chatId, username: data.username });
  },

  /**
   * Get typing users for a chat
   * @param {string} chatId - Chat ID
   * @returns {Set} Set of typing usernames
   */
  getTypingUsers(chatId) {
    return chatState.getTypingUsers(chatId);
  },

  /**
   * Render typing indicator
   * @param {string} chatId - Chat ID
   * @returns {string} HTML string for typing indicator
   */
  renderTypingIndicator(chatId) {
    const users = this.getTypingUsers(chatId);
    if (!users || users.size === 0) return '';
    const names = [...users];
    const label = names.length === 1
      ? `${names[0]} is typing`
      : `${names.slice(0, 2).join(', ')} are typing`;
    return `${label}<span class="typing-dots"><span></span><span></span><span></span></span>`;
  }
};
