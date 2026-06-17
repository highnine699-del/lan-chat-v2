/**
 * ui/pages/RoomPage.js
 * 
 * Room page component - room management interface.
 * Handles room creation, joining, leaving, and key rotation.
 * V2: Attaches event listeners to DOM elements, replacing inline HTML handlers.
 */

import { chatState } from '../../core/state/chatState.js';
import { eventBus } from '../../core/eventBus.js';

export class RoomPage {
  constructor(options = {}) {
    this.onCreateRoom = options.onCreateRoom || (() => {});
    this.onJoinRoom = options.onJoinRoom || (() => {});
    this.onLeaveRoom = options.onLeaveRoom || (() => {});
    this.onRotateKey = options.onRotateKey || (() => {});
    this.onCopyRoomId = options.onCopyRoomId || (() => {});
    this._listenersAttached = false;
  }

  /**
   * Initialize room page - attach event listeners to DOM elements
   * This replaces inline HTML handlers with addEventListener
   */
  init() {
    if (this._listenersAttached) return;

    // Attach listeners to existing DOM elements
    this._attachRoomModalListeners();
    this._attachCreateRoomListeners();
    this._attachJoinRoomListeners();
    this._attachRoomActionListeners();

    this._listenersAttached = true;
    console.log('[LAN Chat V2] [DEBUG] RoomPage event listeners attached');
  }

  /**
   * Attach listeners to room modal
   * @private
   */
  _attachRoomModalListeners() {
    const modal = document.getElementById('room-modal');
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          this.hideRoomModal();
        }
      });
    }

    const closeBtn = document.getElementById('close-room-modal');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        this.hideRoomModal();
      });
    }
  }

  /**
   * Attach listeners to create room form
   * @private
   */
  _attachCreateRoomListeners() {
    const createBtn = document.getElementById('rm-create-btn');
    if (createBtn) {
      createBtn.addEventListener('click', () => {
        this.submitCreateRoom();
      });
    }

    const createInput = document.getElementById('rm-name');
    if (createInput) {
      createInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          this.submitCreateRoom();
        }
      });
    }

    // Visibility toggles
    const pubBtn = document.getElementById('rm-vis-public');
    const privBtn = document.getElementById('rm-vis-private');
    if (pubBtn) {
      pubBtn.addEventListener('click', () => {
        this.setRoomVis('public');
      });
    }
    if (privBtn) {
      privBtn.addEventListener('click', () => {
        this.setRoomVis('private');
      });
    }
  }

  /**
   * Attach listeners to join room form
   * @private
   */
  _attachJoinRoomListeners() {
    const joinBtn = document.getElementById('rm-join-btn');
    if (joinBtn) {
      joinBtn.addEventListener('click', () => {
        this.submitJoinRoom();
      });
    }

    const roomIdInput = document.getElementById('rm-join-id');
    if (roomIdInput) {
      roomIdInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          document.getElementById('rm-join-password')?.focus();
        }
      });
    }

    const passwordInput = document.getElementById('rm-join-password');
    if (passwordInput) {
      passwordInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          this.submitJoinRoom();
        }
      });
    }
  }

  /**
   * Attach listeners to room action buttons
   * @private
   */
  _attachRoomActionListeners() {
    const leaveBtn = document.getElementById('leave-room-btn');
    if (leaveBtn) {
      leaveBtn.addEventListener('click', () => {
        this.onLeaveRoom();
      });
    }

    const rotateKeyBtn = document.getElementById('rotate-key-btn');
    if (rotateKeyBtn) {
      rotateKeyBtn.addEventListener('click', () => {
        this.onRotateKey();
      });
    }

    const copyIdBtn = document.getElementById('copy-room-id-btn');
    if (copyIdBtn) {
      copyIdBtn.addEventListener('click', () => {
        this.onCopyRoomId();
      });
    }
  }

  /**
   * Show room modal
   * @param {string} mode - 'create' or 'join'
   */
  showRoomModal(mode) {
    const modal = document.getElementById('room-modal');
    if (modal) {
      modal.style.display = 'flex';
      if (mode === 'create') {
        document.getElementById('room-modal-create').style.display = 'block';
        document.getElementById('room-modal-join').style.display = 'none';
      } else {
        document.getElementById('room-modal-create').style.display = 'none';
        document.getElementById('room-modal-join').style.display = 'block';
      }
    }
  }

  /**
   * Hide room modal
   */
  hideRoomModal() {
    const modal = document.getElementById('room-modal');
    if (modal) {
      modal.style.display = 'none';
    }
  }

  /**
   * Set room visibility
   * @param {string} vis - 'public' or 'private'
   */
  setRoomVis(vis) {
    const pubBtn = document.getElementById('rm-vis-public');
    const privBtn = document.getElementById('rm-vis-private');
    const pwWrap = document.getElementById('rm-password-wrap');
    if (vis === 'public') {
      pubBtn.style.border = '1.5px solid var(--accent)';
      privBtn.style.border = '1px solid var(--border)';
      pwWrap.style.display = 'none';
    } else {
      pubBtn.style.border = '1px solid var(--border)';
      privBtn.style.border = '1.5px solid var(--accent)';
      pwWrap.style.display = 'block';
    }
  }

  /**
   * Submit create room form
   */
  submitCreateRoom() {
    const name = document.getElementById('rm-name')?.value;
    const visibility = document.getElementById('rm-vis-public').style.border.includes('1.5px') ? 'public' : 'private';
    const password = document.getElementById('rm-password')?.value;
    const ttl = document.getElementById('rm-ttl')?.value;
    const requireApproval = document.getElementById('rm-approval')?.checked;

    if (!name) {
      console.warn('[RoomPage] Room name required');
      return;
    }

    this.onCreateRoom({ name, visibility, password, ttl, requireApproval });
    this.hideRoomModal();
  }

  /**
   * Submit join room form
   */
  submitJoinRoom() {
    const roomId = document.getElementById('rm-join-id')?.value;
    const password = document.getElementById('rm-join-password')?.value;

    if (!roomId) {
      console.warn('[RoomPage] Room ID required');
      return;
    }

    this.onJoinRoom({ roomId, password });
    this.hideRoomModal();
  }

  /**
   * Get create room form data
   * @returns {Object} Form data
   */
  getCreateRoomFormData() {
    const visibility = document.getElementById('rm-vis-public').style.border.includes('1.5px') ? 'public' : 'private';
    return {
      name: document.getElementById('rm-name')?.value,
      visibility,
      password: document.getElementById('rm-password')?.value,
      ttl: document.getElementById('rm-ttl')?.value,
      requireApproval: document.getElementById('rm-approval')?.checked,
    };
  }

  /**
   * Get join room form data
   * @returns {Object} Form data
   */
  getJoinRoomFormData() {
    return {
      roomId: document.getElementById('rm-join-id')?.value,
      password: document.getElementById('rm-join-password')?.value,
    };
  }
}
