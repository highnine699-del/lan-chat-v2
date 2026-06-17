/**
 * features/admin/admin.js
 * 
 * Admin controls feature.
 * Handles admin operations like kick, ban, mute, and room management.
 */

import { eventBus } from '../../core/eventBus.js';

export const admin = {
  /**
   * Kick a user from a room
   * @param {string} username - Username to kick
   * @param {string} roomId - Room ID
   * @param {Object} socket - Socket instance
   */
  kickUser(username, roomId, socket) {
    socket.emit('admin:kick', { username, room_id: roomId });
    eventBus.emit('admin:user_kicked', { username, roomId });
  },

  /**
   * Ban a user from the server
   * @param {string} username - Username to ban
   * @param {Object} socket - Socket instance
   */
  banUser(username, socket) {
    socket.emit('admin:ban', { username });
    eventBus.emit('admin:user_banned', { username });
  },

  /**
   * Mute a user globally
   * @param {string} username - Username to mute
   * @param {number} duration - Duration in seconds
   * @param {Object} socket - Socket instance
   */
  muteUser(username, duration, socket) {
    socket.emit('admin:mute', { username, duration });
    eventBus.emit('admin:user_muted', { username, duration });
  },

  /**
   * Unmute a user
   * @param {string} username - Username to unmute
   * @param {Object} socket - Socket instance
   */
  unmuteUser(username, socket) {
    socket.emit('admin:unmute', { username });
    eventBus.emit('admin:user_unmuted', { username });
  },

  /**
   * Freeze a room
   * @param {string} roomId - Room ID
   * @param {Object} socket - Socket instance
   */
  freezeRoom(roomId, socket) {
    socket.emit('admin:freeze_room', { room_id: roomId });
    eventBus.emit('admin:room_frozen', { roomId });
  },

  /**
   * Unfreeze a room
   * @param {string} roomId - Room ID
   * @param {Object} socket - Socket instance
   */
  unfreezeRoom(roomId, socket) {
    socket.emit('admin:unfreeze_room', { room_id: roomId });
    eventBus.emit('admin:room_unfrozen', { roomId });
  },

  /**
   * Delete a room
   * @param {string} roomId - Room ID
   * @param {Object} socket - Socket instance
   */
  deleteRoom(roomId, socket) {
    if (confirm('Are you sure you want to delete this room?')) {
      socket.emit('admin:delete_room', { room_id: roomId });
      eventBus.emit('admin:room_deleted', { roomId });
    }
  },

  /**
   * Handle admin kick event
   * @param {Object} data - Kick data
   */
  handleKicked(data) {
    eventBus.emit('admin:kicked', data);
  },

  /**
   * Handle admin ban event
   * @param {Object} data - Ban data
   */
  handleBanned(data) {
    eventBus.emit('admin:banned', data);
  },

  /**
   * Handle admin mute event
   * @param {Object} data - Mute data
   */
  handleMuted(data) {
    eventBus.emit('admin:muted', data);
  },

  /**
   * Check if current user is admin
   * @param {Object} state - App state
   * @returns {boolean} True if admin
   */
  isAdmin(state) {
    return state.isServerAdmin || false;
  },

  /**
   * Check if user is room admin
   * @param {string} roomId - Room ID
   * @param {Object} state - App state
   * @returns {boolean} True if room admin
   */
  isRoomAdmin(roomId, state) {
    // This would need to be implemented based on room membership data
    // For now, return false
    return false;
  }
};
