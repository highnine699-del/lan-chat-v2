/**
 * utils/analytics.js
 * 
 * Analytics utility functions.
 */

export const analytics = {
  /**
   * Track an event
   * @param {string} event - Event name
   * @param {Object} data - Event data
   */
  track(event, data = {}) {
    console.log(`[Analytics] ${event}`, data);
    // In production, this would send to an analytics service
  },

  /**
   * Track page view
   * @param {string} page - Page name
   */
  trackPageView(page) {
    this.track('page_view', { page });
  },

  /**
   * Track user action
   * @param {string} action - Action name
   * @param {Object} data - Action data
   */
  trackAction(action, data = {}) {
    this.track('user_action', { action, ...data });
  },

  /**
   * Track error
   * @param {Error} error - Error object
   * @param {Object} context - Error context
   */
  trackError(error, context = {}) {
    this.track('error', {
      message: error.message,
      stack: error.stack,
      ...context
    });
  },

  /**
   * Track performance metric
   * @param {string} metric - Metric name
   * @param {number} value - Metric value
   */
  trackPerformance(metric, value) {
    this.track('performance', { metric, value });
  },

  /**
   * Start performance timer
   * @param {string} name - Timer name
   * @returns {number} Start time
   */
  startTimer(name) {
    const startTime = performance.now();
    return { name, startTime };
  },

  /**
   * End performance timer
   * @param {Object} timer - Timer object
   */
  endTimer(timer) {
    const duration = performance.now() - timer.startTime;
    this.trackPerformance(timer.name, duration);
  },

  /**
   * Track feature usage
   * @param {string} feature - Feature name
   */
  trackFeature(feature) {
    this.track('feature_used', { feature });
  }
};
