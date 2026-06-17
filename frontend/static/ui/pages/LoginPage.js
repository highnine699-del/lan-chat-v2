/**
 * ui/pages/LoginPage.js
 * 
 * Login page component.
 * Handles user authentication and login form.
 */

import { eventBus } from '../../core/eventBus.js';

export class LoginPage {
  constructor(options = {}) {
    this.onLogin = options.onLogin || (() => {});
    this.element = null;
  }

  /**
   * Render the login page
   * @returns {HTMLElement} Login page element
   */
  render() {
    this.element = this._createElement();
    this._attachEventListeners();
    return this.element;
  }

  /**
   * Remove the element from DOM
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
  }

  /**
   * Get username input value
   * @returns {string} Username
   */
  getUsername() {
    const input = this.element?.querySelector('#username-input');
    return input ? input.value.trim() : '';
  }

  /**
   * Set error message
   * @param {string} message - Error message
   */
  setError(message) {
    const errorEl = this.element?.querySelector('.login-error');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = message ? 'block' : 'none';
    }
  }

  /**
   * Create login page element
   * @private
   * @returns {HTMLElement} Login page element
   */
  _createElement() {
    const page = document.createElement('div');
    page.className = 'login-page';

    const container = document.createElement('div');
    container.className = 'login-container';

    const logo = document.createElement('div');
    logo.className = 'login-logo';
    logo.textContent = '💬';

    const title = document.createElement('h1');
    title.className = 'login-title';
    title.textContent = 'LAN Chat';

    const subtitle = document.createElement('p');
    subtitle.className = 'login-subtitle';
    subtitle.textContent = 'Secure local messaging';

    const form = this._createForm();

    const error = document.createElement('div');
    error.className = 'login-error';
    error.style.display = 'none';

    container.appendChild(logo);
    container.appendChild(title);
    container.appendChild(subtitle);
    container.appendChild(error);
    container.appendChild(form);
    page.appendChild(container);

    return page;
  }

  /**
   * Create login form
   * @private
   * @returns {HTMLElement} Form element
   */
  _createForm() {
    const form = document.createElement('form');
    form.className = 'login-form';

    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group';

    const label = document.createElement('label');
    label.textContent = 'Username';

    const input = document.createElement('input');
    input.type = 'text';
    input.id = 'username-input';
    input.className = 'login-input';
    input.placeholder = 'Enter your username';
    input.maxLength = 20;
    input.required = true;
    input.autocomplete = 'off';

    inputGroup.appendChild(label);
    inputGroup.appendChild(input);

    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'login-button';
    button.textContent = 'Join Chat';

    form.appendChild(inputGroup);
    form.appendChild(button);

    return form;
  }

  /**
   * Attach event listeners
   * @private
   */
  _attachEventListeners() {
    const form = this.element?.querySelector('.login-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = this.getUsername();
        if (username) {
          this.onLogin(username);
        }
      });
    }
  }
}
