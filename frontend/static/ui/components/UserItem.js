/**
 * ui/components/UserItem.js
 * 
 * User item component - reusable user list item.
 */

export class UserItem {
  constructor(user, options = {}) {
    this.user = user;
    this.isActive = options.isActive || false;
    this.onClick = options.onClick || (() => {});
    this.onMute = options.onMute || (() => {});
    this.element = null;
  }

  /**
   * Render the user item
   * @returns {HTMLElement} User item element
   */
  render() {
    this.element = this._createElement();
    return this.element;
  }

  /**
   * Update the user with new data
   * @param {Object} user - Updated user data
   */
  update(user) {
    this.user = user;
    if (this.element) {
      const nameEl = this.element.querySelector('.chat-item-name span');
      const repBadge = this.element.querySelector('.rep-badge');
      const dot = this.element.querySelector('.online-dot');

      if (nameEl) nameEl.textContent = user.display;
      if (repBadge) {
        repBadge.className = 'rep-badge rep-' + (user.reputation || 'new').toLowerCase();
        repBadge.textContent = user.reputation || 'New';
      }
      if (dot) dot.style.background = user.online ? '#25d366' : '#666';
    }
  }

  /**
   * Set active state
   * @param {boolean} isActive - Active state
   */
  setActive(isActive) {
    this.isActive = isActive;
    if (this.element) {
      this.element.classList.toggle('active', isActive);
    }
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
   * Create user element
   * @private
   * @returns {HTMLElement} User element
   */
  _createElement() {
    const item = document.createElement('div');
    item.className = 'chat-item user-item' + (this.isActive ? ' active' : '');
    item.id = 'chat-item-' + CSS.escape(this.user.display);
    item.onclick = () => this.onClick(this.user.display);

    // Long-press for mute
    this._attachLongPress(item);

    const avatar = this._createAvatar();
    const info = this._createInfo();
    const dot = this._createOnlineDot();

    item.appendChild(avatar);
    item.appendChild(info);
    item.appendChild(dot);

    return item;
  }

  /**
   * Create avatar
   * @private
   * @returns {HTMLElement} Avatar element
   */
  _createAvatar() {
    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.style.background = this.user.color;
    avatar.textContent = this.user.username[0].toUpperCase();
    return avatar;
  }

  /**
   * Create info section
   * @private
   * @returns {HTMLElement} Info element
   */
  _createInfo() {
    const info = document.createElement('div');
    info.className = 'chat-item-info';

    const nameRow = document.createElement('div');
    nameRow.className = 'chat-item-name';

    const nameSpan = document.createElement('span');
    nameSpan.textContent = this.user.display;

    const repBadge = document.createElement('span');
    repBadge.className = 'rep-badge rep-' + (this.user.reputation || 'new').toLowerCase();
    repBadge.textContent = this.user.reputation || 'New';

    nameRow.appendChild(nameSpan);
    nameRow.appendChild(repBadge);

    const preview = document.createElement('div');
    preview.className = 'chat-item-preview';
    preview.id = 'preview-' + CSS.escape(this.user.display);
    preview.textContent = 'Click to chat privately';

    info.appendChild(nameRow);
    info.appendChild(preview);

    return info;
  }

  /**
   * Create online dot
   * @private
   * @returns {HTMLElement} Dot element
   */
  _createOnlineDot() {
    const dot = document.createElement('div');
    dot.className = 'online-dot';
    dot.style.background = this.user.online ? '#25d366' : '#666';
    return dot;
  }

  /**
   * Attach long-press for mute
   * @private
   * @param {HTMLElement} el - Element to attach to
   */
  _attachLongPress(el) {
    let timer = null;
    let startX = 0;
    let startY = 0;

    const start = (e) => {
      if (e.type === 'mousedown' && e.button !== 0) return;
      if (e.type === 'touchstart') {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
      timer = setTimeout(() => {
        this.onMute(this.user.display);
        if (navigator.vibrate) navigator.vibrate(10);
        timer = null;
      }, 500);
    };

    const move = (e) => {
      if (!timer) return;
      if (e.type === 'touchmove') {
        const dx = Math.abs(e.touches[0].clientX - startX);
        const dy = Math.abs(e.touches[0].clientY - startY);
        if (dx > 10 || dy > 10) cancel();
      }
    };

    const cancel = () => {
      if (timer) { clearTimeout(timer); timer = null; }
    };

    el.addEventListener('touchstart', start, { passive: true });
    el.addEventListener('touchmove', move, { passive: true });
    el.addEventListener('touchend', cancel, { passive: true });
    el.addEventListener('touchcancel', cancel, { passive: true });
    el.addEventListener('mousedown', start);
    el.addEventListener('mouseup', cancel);
    el.addEventListener('mouseleave', cancel);

    // Right-click for desktop
    el.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      this.onMute(this.user.display);
    });
  }
}
