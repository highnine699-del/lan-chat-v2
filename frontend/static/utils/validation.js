/**
 * utils/validation.js
 * 
 * Validation utility functions.
 */

export const validation = {
  /**
   * Validate username
   * @param {string} username - Username to validate
   * @returns {Object} Validation result { valid, error }
   */
  validateUsername(username) {
    if (!username || typeof username !== 'string') {
      return { valid: false, error: 'Username is required' };
    }
    
    const trimmed = username.trim();
    if (trimmed.length < 3) {
      return { valid: false, error: 'Username must be at least 3 characters' };
    }
    
    if (trimmed.length > 20) {
      return { valid: false, error: 'Username must be at most 20 characters' };
    }
    
    if (!/^[a-zA-Z0-9_]+$/.test(trimmed)) {
      return { valid: false, error: 'Username can only contain letters, numbers, and underscores' };
    }
    
    return { valid: true };
  },

  /**
   * Validate room ID
   * @param {string} roomId - Room ID to validate
   * @returns {Object} Validation result { valid, error }
   */
  validateRoomId(roomId) {
    if (!roomId || typeof roomId !== 'string') {
      return { valid: false, error: 'Room ID is required' };
    }
    
    const trimmed = roomId.trim().toUpperCase();
    if (!/^[0-9A-F]{8}$/.test(trimmed)) {
      return { valid: false, error: 'Room ID must be 8 hexadecimal characters' };
    }
    
    return { valid: true };
  },

  /**
   * Validate message text
   * @param {string} text - Message text to validate
   * @returns {Object} Validation result { valid, error }
   */
  validateMessage(text) {
    if (!text || typeof text !== 'string') {
      return { valid: false, error: 'Message is required' };
    }
    
    const trimmed = text.trim();
    if (trimmed.length === 0) {
      return { valid: false, error: 'Message cannot be empty' };
    }
    
    if (trimmed.length > 4000) {
      return { valid: false, error: 'Message is too long (max 4000 characters)' };
    }
    
    return { valid: true };
  },

  /**
   * Validate room name
   * @param {string} name - Room name to validate
   * @returns {Object} Validation result { valid, error }
   */
  validateRoomName(name) {
    if (!name || typeof name !== 'string') {
      return { valid: false, error: 'Room name is required' };
    }
    
    const trimmed = name.trim();
    if (trimmed.length < 3) {
      return { valid: false, error: 'Room name must be at least 3 characters' };
    }
    
    if (trimmed.length > 50) {
      return { valid: false, error: 'Room name must be at most 50 characters' };
    }
    
    return { valid: true };
  },

  /**
   * Validate password
   * @param {string} password - Password to validate
   * @returns {Object} Validation result { valid, error }
   */
  validatePassword(password) {
    if (!password || typeof password !== 'string') {
      return { valid: false, error: 'Password is required' };
    }
    
    if (password.length < 4) {
      return { valid: false, error: 'Password must be at least 4 characters' };
    }
    
    return { valid: true };
  },

  /**
   * Validate file
   * @param {File} file - File to validate
   * @param {number} maxSize - Max size in bytes (default 10MB)
   * @returns {Object} Validation result { valid, error }
   */
  validateFile(file, maxSize = 10 * 1024 * 1024) {
    if (!file) {
      return { valid: false, error: 'No file selected' };
    }
    
    if (file.size > maxSize) {
      return { valid: false, error: 'File is too large (max 10MB)' };
    }
    
    return { valid: true };
  },

  /**
   * Sanitize HTML string
   * @param {string} str - String to sanitize
   * @returns {string} Sanitized string
   */
  sanitizeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  /**
   * Check if string is safe for CSS
   * @param {string} str - String to check
   * @returns {boolean} True if safe
   */
  isSafeCss(str) {
    if (typeof str !== 'string') return false;
    // Check for dangerous CSS patterns
    const dangerous = ['expression', 'javascript:', 'data:', 'url('];
    return !dangerous.some(d => str.toLowerCase().includes(d));
  }
};
