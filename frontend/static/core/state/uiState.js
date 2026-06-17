/**
 * core/state/uiState.js
 * 
 * UI state - active elements, modals, sound settings.
 * Pure functions only, no side effects.
 */

export const uiState = {
  soundMuted: false,
  editingMsg: null,
  modalsOpen: new Set(),
  sidebarOpen: false,

  /**
   * Toggle sound mute
   */
  toggleSoundMute() {
    this.soundMuted = !this.soundMuted;
  },

  /**
   * Set sound mute state
   * @param {boolean} muted - Muted state
   */
  setSoundMuted(muted) {
    this.soundMuted = muted;
  },

  /**
   * Get sound mute state
   * @returns {boolean} Muted state
   */
  isSoundMuted() {
    return this.soundMuted;
  },

  /**
   * Set message being edited
   * @param {Object} msg - Message object
   */
  setEditingMsg(msg) {
    this.editingMsg = msg;
  },

  /**
   * Clear editing message
   */
  clearEditingMsg() {
    this.editingMsg = null;
  },

  /**
   * Get editing message
   * @returns {Object|null} Message object or null
   */
  getEditingMsg() {
    return this.editingMsg;
  },

  /**
   * Open a modal
   * @param {string} modalId - Modal identifier
   */
  openModal(modalId) {
    this.modalsOpen.add(modalId);
  },

  /**
   * Close a modal
   * @param {string} modalId - Modal identifier
   */
  closeModal(modalId) {
    this.modalsOpen.delete(modalId);
  },

  /**
   * Check if modal is open
   * @param {string} modalId - Modal identifier
   * @returns {boolean} True if modal is open
   */
  isModalOpen(modalId) {
    return this.modalsOpen.has(modalId);
  },

  /**
   * Close all modals
   */
  closeAllModals() {
    this.modalsOpen.clear();
  },

  /**
   * Set sidebar open state
   * @param {boolean} open - Open state
   */
  setSidebarOpen(open) {
    this.sidebarOpen = open;
  },

  /**
   * Get sidebar open state
   * @returns {boolean} Open state
   */
  isSidebarOpen() {
    return this.sidebarOpen;
  }
};
