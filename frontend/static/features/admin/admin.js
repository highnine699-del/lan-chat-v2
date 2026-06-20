/**
 * features/admin/admin.js
 *
 * Admin controls.
 * Event names match the backend socket_admin.py handlers exactly.
 */

import { eventBus } from '../../core/eventBus.js';

export const admin = {
  /**
   * Kick a user from a room (room-admin action).
   * Backend: admin:kick  { target, room_id }
   */
  kickUser(username, roomId, socket) {
    socket.emit('admin:kick', { target: username, room_id: roomId });
    eventBus.emit('admin:user_kicked', { username, roomId });
  },

  /**
   * Server-kick a user (server-admin action).
   * Backend: admin:server_kick / admin:ban  { target }
   */
  banUser(username, socket) {
    socket.emit('admin:server_kick', { target: username });
    eventBus.emit('admin:user_banned', { username });
  },

  /**
   * Shadow-mute a user globally (server-admin action).
   * Backend: admin:mute / admin:server_shadow_mute  { target, duration }
   */
  muteUser(username, duration, socket) {
    socket.emit('admin:mute', { target: username, duration });
    eventBus.emit('admin:user_muted', { username, duration });
  },

  /**
   * Unmute a user (server-admin action).
   * Backend: admin:unmute  { target }
   */
  unmuteUser(username, socket) {
    socket.emit('admin:unmute', { target: username });
    eventBus.emit('admin:user_unmuted', { username });
  },

  /**
   * Freeze a room (room-admin action).
   * Backend: admin:freeze  { room_id, freeze: true }
   */
  freezeRoom(roomId, socket) {
    socket.emit('admin:freeze', { room_id: roomId, freeze: true });
    eventBus.emit('admin:room_frozen', { roomId });
  },

  /**
   * Unfreeze a room (room-admin action).
   * Backend: admin:freeze  { room_id, freeze: false }
   */
  unfreezeRoom(roomId, socket) {
    socket.emit('admin:freeze', { room_id: roomId, freeze: false });
    eventBus.emit('admin:room_unfrozen', { roomId });
  },

  /**
   * Delete a room (server-admin or room-admin action).
   * Backend: admin:delete_room  { room_id }
   */
  deleteRoom(roomId, socket) {
    if (confirm('Are you sure you want to delete this room?')) {
      socket.emit('admin:delete_room', { room_id: roomId });
      eventBus.emit('admin:room_deleted', { roomId });
    }
  },

  /**
   * Grant or revoke room-mod status.
   * Backend: admin:mod  { target, room_id, grant }
   */
  setMod(username, roomId, grant, socket) {
    socket.emit('admin:mod', { target: username, room_id: roomId, grant });
    eventBus.emit('admin:mod_changed', { username, roomId, grant });
  },

  handleKicked(data) {
    eventBus.emit('admin:kicked', data);
  },

  isAdmin(state) {
    return state?.isServerAdmin || false;
  },

  isRoomAdmin(roomId, myDisplay, roomMembers) {
    // roomMembers array from room:members event — check is_admin flag
    if (!roomMembers) return false;
    const me = roomMembers.find(m => m.display === myDisplay);
    return me ? !!me.is_admin : false;
  },
};
