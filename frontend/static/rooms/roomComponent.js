/**
 * rooms/roomComponent.js
 * 
 * Room list item component.
 * Reusable component for rendering individual room items.
 */

export class RoomItem {
  constructor(room, options = {}) {
    this.room = room;
    this.onClick = options.onClick || (() => {});
    this.isActive = options.isActive || false;
    this.element = null;
  }

  /**
   * Render the room item
   * @returns {HTMLElement} Room item element
   */
  render() {
    this.element = document.createElement('div');
    this.element.className = 'chat-item room-item' + (this.isActive ? ' active' : '');
    this.element.id = 'chat-item-room-' + this.room.room_id;
    this.element.onclick = () => this.onClick(this.room.room_id);

    const avatar = this._createAvatar();
    const info = this._createInfo();

    this.element.appendChild(avatar);
    this.element.appendChild(info);

    return this.element;
  }

  /**
   * Update the room item with new data
   * @param {Object} room - Updated room data
   */
  update(room) {
    this.room = room;
    if (this.element) {
      const nameEl = this.element.querySelector('.chat-item-name');
      const previewEl = this.element.querySelector('.chat-item-preview');

      if (nameEl) nameEl.textContent = room.name;
      if (previewEl) {
        previewEl.textContent = `${room.members} member${room.members !== 1 ? 's' : ''}` +
          (room.is_frozen ? ' • ❄️ frozen' : '');
      }
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
   * Create avatar element
   * @private
   * @returns {HTMLElement} Avatar element
   */
  _createAvatar() {
    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.style.background = '#1a3a5c';
    avatar.style.fontSize = '18px';
    avatar.textContent = '👥';
    return avatar;
  }

  /**
   * Create info element
   * @private
   * @returns {HTMLElement} Info element
   */
  _createInfo() {
    const info = document.createElement('div');
    info.className = 'chat-item-info';

    const nameEl = document.createElement('div');
    nameEl.className = 'chat-item-name';
    nameEl.textContent = this.room.name;

    const previewEl = document.createElement('div');
    previewEl.className = 'chat-item-preview';
    previewEl.textContent = `${this.room.members} member${this.room.members !== 1 ? 's' : ''}` +
      (this.room.is_frozen ? ' • ❄️ frozen' : '');

    info.appendChild(nameEl);
    info.appendChild(previewEl);

    return info;
  }
}
