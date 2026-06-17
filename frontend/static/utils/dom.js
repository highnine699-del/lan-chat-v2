/**
 * utils/dom.js
 * 
 * DOM utility functions.
 */

export const dom = {
  /**
   * Get element by ID
   * @param {string} id - Element ID
   * @returns {HTMLElement|null} Element or null
   */
  get(id) {
    return document.getElementById(id);
  },

  /**
   * Query selector
   * @param {string} selector - CSS selector
   * @param {HTMLElement} parent - Parent element (optional)
   * @returns {HTMLElement|null} Element or null
   */
  query(selector, parent = document) {
    return parent.querySelector(selector);
  },

  /**
   * Query all elements
   * @param {string} selector - CSS selector
   * @param {HTMLElement} parent - Parent element (optional)
   * @returns {NodeList} Elements
   */
  queryAll(selector, parent = document) {
    return parent.querySelectorAll(selector);
  },

  /**
   * Create element with attributes
   * @param {string} tag - HTML tag
   * @param {Object} attrs - Attributes
   * @returns {HTMLElement} Created element
   */
  create(tag, attrs = {}) {
    const el = document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => {
      if (key === 'className') {
        el.className = value;
      } else if (key === 'style' && typeof value === 'object') {
        Object.assign(el.style, value);
      } else if (key.startsWith('data-')) {
        el.dataset[key.slice(5)] = value;
      } else {
        el[key] = value;
      }
    });
    return el;
  },

  /**
   * Remove element
   * @param {HTMLElement} el - Element to remove
   */
  remove(el) {
    if (el && el.parentNode) {
      el.parentNode.removeChild(el);
    }
  },

  /**
   * Add class
   * @param {HTMLElement} el - Element
   * @param {string} className - Class name
   */
  addClass(el, className) {
    if (el) el.classList.add(className);
  },

  /**
   * Remove class
   * @param {HTMLElement} el - Element
   * @param {string} className - Class name
   */
  removeClass(el, className) {
    if (el) el.classList.remove(className);
  },

  /**
   * Toggle class
   * @param {HTMLElement} el - Element
   * @param {string} className - Class name
   * @param {boolean} force - Force add/remove (optional)
   */
  toggleClass(el, className, force) {
    if (el) el.classList.toggle(className, force);
  },

  /**
   * Scroll to element
   * @param {HTMLElement} el - Element to scroll to
   * @param {Object} options - Scroll options
   */
  scrollTo(el, options = { behavior: 'smooth', block: 'center' }) {
    if (el) el.scrollIntoView(options);
  },

  /**
   * Escape HTML
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  /**
   * Sanitize URL
   * @param {string} url - URL to sanitize
   * @returns {string} Safe URL
   */
  safeUrl(url) {
    if (typeof url !== 'string') return '';
    const trimmed = url.trim();
    if (trimmed.startsWith('/uploads/')) return trimmed;
    if (trimmed.startsWith('blob:')) return trimmed;
    return '';
  },

  /**
   * Sanitize color
   * @param {string} color - Color to sanitize
   * @param {string} fallback - Fallback color
   * @returns {string} Safe color
   */
  safeColor(color, fallback = '#25d366') {
    if (typeof color !== 'string') return fallback;
    const c = color.trim();
    if (/^#[0-9a-fA-F]{3}$/.test(c) || /^#[0-9a-fA-F]{6}$/.test(c)) return c;
    const allowed = new Set([
      '#25D366', '#00a884', '#53bdeb', '#f0b429',
      '#e06c75', '#c678dd', '#56b6c2', '#e5c07b',
    ]);
    if (allowed.has(c.toUpperCase()) || allowed.has(c)) return c;
    return fallback;
  }
};
