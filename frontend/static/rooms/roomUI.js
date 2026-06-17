/**
 * rooms/roomUI.js
 * 
 * Room UI rendering and interactions.
 * Handles room list, room modal, and room ID banner.
 */

import { chatState } from '../core/state/chatState.js';
import { eventBus } from '../core/eventBus.js';

export const roomUI = {
  /**
   * Render room list in sidebar
   * @param {Array} rooms - Room array
   * @param {Function} onRoomClick - Click callback
   */
  renderRoomList(rooms, onRoomClick) {
    // Remove stale room items
    document.querySelectorAll('.chat-item.room-item').forEach(el => el.remove());
    if (!rooms || !rooms.length) return;

    const list = document.getElementById('chat-list');
    if (!list) return;

    rooms.forEach(r => {
      const id = 'chat-item-room-' + r.room_id;
      if (document.getElementById(id)) return; // Already rendered

      const item = this._createRoomItem(r, onRoomClick);
      list.appendChild(item);
    });
  },

  /**
   * Create room list item
   * @private
   * @param {Object} room - Room data
   * @param {Function} onClick - Click callback
   * @returns {HTMLElement} Room item element
   */
  _createRoomItem(room, onClick) {
    const item = document.createElement('div');
    item.className = 'chat-item room-item';
    item.id = 'chat-item-room-' + room.room_id;
    item.onclick = () => onClick(room.room_id);

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.style.background = '#1a3a5c';
    avatar.style.fontSize = '18px';
    avatar.textContent = '👥';

    const info = document.createElement('div');
    info.className = 'chat-item-info';

    const nameEl = document.createElement('div');
    nameEl.className = 'chat-item-name';
    nameEl.textContent = room.name;

    const preview = document.createElement('div');
    preview.className = 'chat-item-preview';
    preview.textContent = `${room.members} member${room.members !== 1 ? 's' : ''}` +
      (room.is_frozen ? ' • ❄️ frozen' : '');

    info.appendChild(nameEl);
    info.appendChild(preview);
    item.appendChild(avatar);
    item.appendChild(info);

    return item;
  },

  /**
   * Show room modal
   * @param {string} mode - 'create' or 'join'
   */
  showRoomModal(mode) {
    console.log('[LAN Chat V2] [DEBUG] showRoomModal called with mode:', mode);
    const modal = document.getElementById('room-modal');
    if (!modal) {
      console.error('[LAN Chat V2] [DEBUG] room-modal element not found');
      return;
    }

    const createSection = document.getElementById('room-modal-create');
    const joinSection = document.getElementById('room-modal-join');
    if (!createSection || !joinSection) {
      console.error('[LAN Chat V2] [DEBUG] room-modal-create or room-modal-join not found');
      return;
    }

    createSection.style.display = mode === 'create' ? 'block' : 'none';
    joinSection.style.display = mode === 'join' ? 'block' : 'none';
    modal.style.display = 'flex';
    modal.style.zIndex = '99999';
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    console.log('[LAN Chat V2] [DEBUG] Modal display set to flex, z-index set to 99999, position fixed');

    // Reset fields
    if (mode === 'create') {
      const nameInput = document.getElementById('rm-name');
      const passwordInput = document.getElementById('rm-password');
      const ttlInput = document.getElementById('rm-ttl');
      if (nameInput) nameInput.value = '';
      if (passwordInput) passwordInput.value = '';
      if (ttlInput) ttlInput.value = 'session';
      this._setRoomVis('public');
      setTimeout(() => {
        if (nameInput) nameInput.focus();
      }, 50);
    } else {
      const idInput = document.getElementById('rm-join-id');
      const passwordInput = document.getElementById('rm-join-password');
      if (idInput) idInput.value = '';
      if (passwordInput) passwordInput.value = '';
      setTimeout(() => {
        if (idInput) idInput.focus();
      }, 50);
    }

    eventBus.emit('room:modal_opened', { mode });
  },

  /**
   * Hide room modal
   */
  hideRoomModal() {
    const modal = document.getElementById('room-modal');
    if (modal) modal.style.display = 'none';
    eventBus.emit('room:modal_closed');
  },

  /**
   * Set room visibility in modal
   * @private
   * @param {string} vis - 'public' or 'private'
   */
  _setRoomVis(vis) {
    const pubBtn = document.getElementById('rm-vis-public');
    const privBtn = document.getElementById('rm-vis-private');
    const pwWrap = document.getElementById('rm-password-wrap');

    if (vis === 'public') {
      pubBtn.style.border = '1.5px solid var(--accent)';
      pubBtn.style.background = 'rgba(0,255,136,0.15)';
      pubBtn.style.color = 'var(--accent)';
      privBtn.style.border = '1.5px solid var(--border)';
      privBtn.style.background = 'var(--bg-tertiary)';
      privBtn.style.color = 'var(--text-secondary)';
      pwWrap.style.display = 'none';
    } else {
      privBtn.style.border = '1.5px solid var(--accent)';
      privBtn.style.background = 'rgba(0,255,136,0.15)';
      privBtn.style.color = 'var(--accent)';
      pubBtn.style.border = '1.5px solid var(--border)';
      pubBtn.style.background = 'var(--bg-tertiary)';
      pubBtn.style.color = 'var(--text-secondary)';
      pwWrap.style.display = 'block';
    }
  },

  /**
   * Show room ID banner
   * @param {string} roomId - Room ID
   */
  showRoomIdBanner(roomId) {
    const banner = document.getElementById('room-id-banner');
    if (!banner) return;

    document.getElementById('room-id-display').textContent = roomId;
    document.getElementById('room-key-fingerprint').textContent = '🔐';
    banner.style.display = 'flex';

    eventBus.emit('room:banner_shown', { roomId });
  },

  /**
   * Hide room ID banner
   */
  hideRoomIdBanner() {
    const banner = document.getElementById('room-id-banner');
    if (banner) {
      banner.style.display = 'none';
      document.getElementById('room-id-display').textContent = '';
      document.getElementById('room-key-fingerprint').textContent = '🔐';
    }

    eventBus.emit('room:banner_hidden');
  },

  /**
   * Update room member count in header
   * @param {string} roomId - Room ID
   * @param {number} count - Member count
   */
  updateRoomMemberCount(roomId, count) {
    if (chatState.currentRoom !== roomId) return;

    const el = document.getElementById('header-status');
    if (el) el.textContent = `${count} member${count !== 1 ? 's' : ''}`;
  },

  /**
   * Get room creation form data
   * @returns {Object} Form data
   */
  getCreateRoomFormData() {
    return {
      name: document.getElementById('rm-name').value.trim(),
      password: document.getElementById('rm-password').value.trim(),
      ttl: document.getElementById('rm-ttl').value,
      visibility: document.querySelector('#rm-vis-public').style.border.includes('var(--accent)') ? 'public' : 'private',
      requireApproval: document.getElementById('rm-require-approval')?.checked || false,
    };
  },

  /**
   * Get room join form data
   * @returns {Object} Form data
   */
  getJoinRoomFormData() {
    return {
      roomId: document.getElementById('rm-join-id').value.trim().toUpperCase(),
      password: document.getElementById('rm-join-password').value.trim(),
    };
  },

  /**
   * Copy room ID to clipboard
   * @param {string} roomId - Room ID
   */
  async copyRoomId(roomId) {
    try {
      await navigator.clipboard.writeText(roomId);
      const btn = document.getElementById('copy-room-id-btn');
      if (btn) {
        btn.textContent = '✓ Copied!';
        btn.style.background = 'rgba(0,255,136,0.3)';
        setTimeout(() => {
          btn.textContent = '📋 Copy';
          btn.style.background = 'rgba(0,255,136,0.15)';
        }, 2000);
      }
    } catch {
      prompt('Copy this Room ID:', roomId);
    }

    eventBus.emit('room:id_copied', { roomId });
  },

  /**
   * Show create room modal (alias for showRoomModal with 'create' mode)
   */
  showCreateModal() {
    this.showRoomModal('create');
  },

  /**
   * Show join room modal (alias for showRoomModal with 'join' mode)
   */
  showJoinModal() {
    this.showRoomModal('join');
  }
};
