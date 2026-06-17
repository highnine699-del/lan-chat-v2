/**
 * core/eventBus.js
 * 
 * Custom event emitter for decoupling modules.
 * Enables loose coupling between components by allowing them to communicate
 * via events rather than direct function calls.
 */

export const eventBus = {
  listeners: {},

  /**
   * Emit an event to all registered listeners
   * @param {string} event - Event name
   * @param {*} data - Data to pass to listeners
   */
  emit(event, data) {
    (this.listeners[event] || []).forEach(fn => {
      try {
        fn(data);
      } catch (err) {
        console.error(`[eventBus] Error in listener for '${event}':`, err);
      }
    });
  },

  /**
   * Register a listener for an event
   * @param {string} event - Event name
   * @param {Function} fn - Callback function
   */
  on(event, fn) {
    this.listeners[event] = this.listeners[event] || [];
    this.listeners[event].push(fn);
  },

  /**
   * Remove a specific listener for an event
   * @param {string} event - Event name
   * @param {Function} fn - Callback function to remove
   */
  off(event, fn) {
    this.listeners[event] = (this.listeners[event] || []).filter(f => f !== fn);
  },

  /**
   * Remove all listeners for an event (or all events if no event specified)
   * @param {string} [event] - Event name (optional)
   */
  clear(event) {
    if (event) {
      delete this.listeners[event];
    } else {
      this.listeners = {};
    }
  },

  /**
   * Get the number of listeners for an event
   * @param {string} event - Event name
   * @returns {number} Number of listeners
   */
  listenerCount(event) {
    return (this.listeners[event] || []).length;
  }
};
