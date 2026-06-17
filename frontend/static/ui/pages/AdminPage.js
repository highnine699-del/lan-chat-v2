/**
 * ui/pages/AdminPage.js
 * 
 * Admin page component.
 * Handles admin controls and user management.
 */

import { eventBus } from '../../core/eventBus.js';

export class AdminPage {
  constructor(options = {}) {
    this.onKick = options.onKick || (() => {});
    this.onBan = options.onBan || (() => {});
    this.onMute = options.onMute || (() => {});
    this.element = null;
  }

  /**
   * Render the admin page
   * @returns {HTMLElement} Admin page element
   */
  render() {
    this.element = this._createElement();
    return this.element;
  }

  /**
   * Update user list
   * @param {Array} users - Users array
   */
  updateUserList(users) {
    const list = this.element?.querySelector('.admin-user-list');
    if (!list) return;

    list.innerHTML = '';
    users.forEach(user => {
      const item = this._createUserItem(user);
      list.appendChild(item);
    });
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
   * Create admin page element
   * @private
   * @returns {HTMLElement} Admin page element
   */
  _createElement() {
    const page = document.createElement('div');
    page.className = 'admin-page';

    const header = document.createElement('h2');
    header.textContent = 'Admin Panel';

    const list = document.createElement('div');
    list.className = 'admin-user-list';

    page.appendChild(header);
    page.appendChild(list);

    return page;
  }

  /**
   * Create user item
   * @private
   * @param {Object} user - User object
   * @returns {HTMLElement} User item element
   */
  _createUserItem(user) {
    const item = document.createElement('div');
    item.className = 'admin-user-item';

    const info = document.createElement('div');
    info.className = 'admin-user-info';
    info.textContent = user.display;

    const actions = document.createElement('div');
    actions.className = 'admin-user-actions';

    const kickBtn = document.createElement('button');
    kickBtn.className = 'admin-btn';
    kickBtn.textContent = 'Kick';
    kickBtn.onclick = () => this.onKick(user.display);

    const banBtn = document.createElement('button');
    banBtn.className = 'admin-btn danger';
    banBtn.textContent = 'Ban';
    banBtn.onclick = () => this.onBan(user.display);

    const muteBtn = document.createElement('button');
    muteBtn.className = 'admin-btn';
    muteBtn.textContent = 'Mute';
    muteBtn.onclick = () => this.onMute(user.display, 300);

    actions.appendChild(kickBtn);
    actions.appendChild(banBtn);
    actions.appendChild(muteBtn);

    item.appendChild(info);
    item.appendChild(actions);

    return item;
  }
}
