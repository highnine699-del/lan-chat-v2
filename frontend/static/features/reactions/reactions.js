/**
 * features/reactions/reactions.js
 * 
 * Message reactions feature.
 * Handles adding/removing reactions to messages.
 * V2: Subscribes to eventBus instead of direct socket.on
 */

import { eventBus } from '../../core/eventBus.js';

export const reactions = {
  _initialized: false,
  // Available reactions
  availableReactions: ['👍', '❤️', '😂', '😮', '😢', '🔥'],

  /**
   * Initialize reactions feature - subscribe to eventBus events
   */
  init() {
    if (this._initialized) return;

    // Subscribe to socket events via eventBus
    eventBus.on('socket:reaction', (data) => {
      this.handleReaction(data);
    });

    eventBus.on('socket:unreact', (data) => {
      this.handleUnreact(data);
    });

    this._initialized = true;
    console.log('[LAN Chat V2] [DEBUG] reactions initialized and subscribed to eventBus');
  },

  /**
   * Add a reaction to a message
   * @param {string} msgId - Message ID
   * @param {string} emoji - Reaction emoji
   * @param {Object} socket - Socket instance
   */
  addReaction(msgId, emoji, socket) {
    socket.emit('message:react', { msg_id: msgId, emoji });
    eventBus.emit('reaction:added', { msgId, emoji });
  },

  /**
   * Remove a reaction from a message
   * @param {string} msgId - Message ID
   * @param {string} emoji - Reaction emoji
   * @param {Object} socket - Socket instance
   */
  removeReaction(msgId, emoji, socket) {
    socket.emit('message:unreact', { msg_id: msgId, emoji });
    eventBus.emit('reaction:removed', { msgId, emoji });
  },

  /**
   * Handle reaction event
   * @param {Object} data - Reaction data { msg_id, emoji, from }
   */
  handleReaction(data) {
    eventBus.emit('reaction:received', data);
  },

  /**
   * Handle unreact event
   * @param {Object} data - Unreact data { msg_id, emoji, from }
   */
  handleUnreact(data) {
    eventBus.emit('reaction:removed_received', data);
  },

  /**
   * Get available reactions
   * @returns {Array} Available reactions
   */
  getAvailableReactions() {
    return this.availableReactions;
  },

  /**
   * Create reaction picker element
   * @param {string} msgId - Message ID
   * @param {Function} onSelect - Selection callback
   * @returns {HTMLElement} Reaction picker element
   */
  createReactionPicker(msgId, onSelect) {
    const picker = document.createElement('div');
    picker.className = 'reaction-picker';

    this.availableReactions.forEach(emoji => {
      const btn = document.createElement('button');
      btn.className = 'reaction-btn';
      btn.textContent = emoji;
      btn.onclick = () => onSelect(msgId, emoji);
      picker.appendChild(btn);
    });

    return picker;
  }
};
