/**
 * utils/time.js
 * 
 * Time utility functions.
 */

export const time = {
  /**
   * Format timestamp to time string
   * @param {number} ts - Timestamp
   * @returns {string} Formatted time
   */
  formatTime(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },

  /**
   * Format timestamp to date string
   * @param {number} ts - Timestamp
   * @returns {string} Formatted date
   */
  formatDate(ts) {
    const date = new Date(ts);
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    const dateStr = date.toDateString();
    
    if (dateStr === today) return 'Today';
    if (dateStr === yesterday) return 'Yesterday';
    return dateStr;
  },

  /**
   * Format timestamp to date and time
   * @param {number} ts - Timestamp
   * @returns {string} Formatted date and time
   */
  formatDateTime(ts) {
    const date = new Date(ts);
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  },

  /**
   * Get relative time string
   * @param {number} ts - Timestamp
   * @returns {string} Relative time (e.g., "5 minutes ago")
   */
  getRelativeTime(ts) {
    const now = Date.now();
    const diff = now - ts;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) return 'just now';
    if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`;
    return this.formatDate(ts);
  },

  /**
   * Format duration in seconds
   * @param {number} seconds - Duration in seconds
   * @returns {string} Formatted duration (mm:ss)
   */
  formatDuration(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  },

  /**
   * Get current timestamp
   * @returns {number} Current timestamp
   */
  now() {
    return Date.now();
  }
};
