/**
 * utils/storage.js
 * 
 * Local storage utility functions.
 */

export const storage = {
  /**
   * Get item from localStorage
   * @param {string} key - Storage key
   * @returns {any} Stored value or null
   */
  get(key) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch {
      return null;
    }
  },

  /**
   * Set item in localStorage
   * @param {string} key - Storage key
   * @param {any} value - Value to store
   * @returns {boolean} Success status
   */
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Remove item from localStorage
   * @param {string} key - Storage key
   * @returns {boolean} Success status
   */
  remove(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Clear all items from localStorage
   * @returns {boolean} Success status
   */
  clear() {
    try {
      localStorage.clear();
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Get all keys
   * @returns {Array} Array of keys
   */
  keys() {
    try {
      return Object.keys(localStorage);
    } catch {
      return [];
    }
  },

  /**
   * Check if key exists
   * @param {string} key - Storage key
   * @returns {boolean} True if exists
   */
  has(key) {
    try {
      return localStorage.getItem(key) !== null;
    } catch {
      return false;
    }
  },

  /**
   * Get item with default
   * @param {string} key - Storage key
   * @param {any} defaultValue - Default value
   * @returns {any} Stored value or default
   */
  getWithDefault(key, defaultValue = null) {
    const value = this.get(key);
    return value !== null ? value : defaultValue;
  },

  /**
   * Set item with expiration
   * @param {string} key - Storage key
   * @param {any} value - Value to store
   * @param {number} ttl - Time to live in milliseconds
   */
  setWithExpiry(key, value, ttl) {
    const item = {
      value,
      expiry: Date.now() + ttl
    };
    this.set(key, item);
  },

  /**
   * Get item with expiration check
   * @param {string} key - Storage key
   * @returns {any} Stored value or null if expired
   */
  getWithExpiry(key) {
    const item = this.get(key);
    if (!item || !item.expiry) return null;
    
    if (Date.now() > item.expiry) {
      this.remove(key);
      return null;
    }
    
    return item.value;
  }
};
