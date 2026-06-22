/**
 * features/presence/presence.js
 * 
 * User presence feature.
 * Handles user online/offline status and user list updates.
 * V2: Subscribes to eventBus instead of direct socket.on
 */

import { chatState } from '../../core/state/chatState.js';
import { eventBus } from '../../core/eventBus.js';

export const presence = {
  _initialized: false,

  /**
   * Initialize presence feature - subscribe to eventBus events
   */
  init() {
    if (this._initialized) return;

    // Subscribe to socket events via eventBus
    eventBus.on('socket:user_list', (data) => {
      this.handleUserList(data);
    });

    eventBus.on('socket:user_presence', (data) => {
      this.handleUserPresence(data, chatState.getDisplay());
    });

    this._initialized = true;
    console.log('[LAN Chat V2] [DEBUG] presence initialized and subscribed to eventBus');
  },
  /**
   * Handle user presence event
   * @param {Object} data - Presence data { display, presence }
   * @param {string} myDisplay - My display name
   */
  handleUserPresence(data, myDisplay) {
    if (data.display === myDisplay) return;
    
    const users = chatState.users;
    const user = users.find(u => u.display === data.display);
    if (user) {
      user.presence = data.presence;
      user.online = data.presence === 'active';
      chatState.setUsers(users);
      eventBus.emit('presence:updated', user);
    }
  },

  /**
   * Handle user list event
   * @param {Array} users - User list
   */
  handleUserList(users) {
    const enriched = (users || []).map(u => ({
      ...u,
      online: u.presence !== 'away' && u.presence !== 'offline',
    }));
    chatState.setUsers(enriched);
    eventBus.emit('presence:user_list', enriched);
  },

  /**
   * Get online users
   * @returns {Array} Online users
   */
  getOnlineUsers() {
    return chatState.users.filter(u => u.online);
  },

  /**
   * Get user by display name
   * @param {string} display - Display name
   * @returns {Object|null} User object or null
   */
  getUser(display) {
    return chatState.users.find(u => u.display === display) || null;
  },

  /**
   * Check if user is online
   * @param {string} display - Display name
   * @returns {boolean} True if online
   */
  isUserOnline(display) {
    const user = this.getUser(display);
    return user ? user.online : false;
  }
};
