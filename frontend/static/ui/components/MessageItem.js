/**
 * ui/components/MessageItem.js
 * 
 * Message item component - reusable message bubble.
 */

export class MessageItem {
  constructor(msg, options = {}) {
    this.msg = msg;
    this.isOwn = options.isOwn || false;
    this.isMuted = options.isMuted || false;
    this.onReply = options.onReply || (() => {});
    this.onEdit = options.onEdit || (() => {});
    this.onDelete = options.onDelete || (() => {});
    this.element = null;
  }

  /**
   * Render the message item
   * @returns {HTMLElement|null} Message element or null if muted
   */
  render() {
    if (!this.isOwn && this.isMuted) return null;

    this.element = this._createElement();
    return this.element;
  }

  /**
   * Update the message with new data
   * @param {Object} msg - Updated message data
   */
  update(msg) {
    this.msg = msg;
    if (this.element) {
      const newElement = this._createElement();
      this.element.replaceWith(newElement);
      this.element = newElement;
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
   * Create message element
   * @private
   * @returns {HTMLElement} Message element
   */
  _createElement() {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper ' + (this.isOwn ? 'me' : 'other');
    if (this.msg.msg_id) wrapper.dataset.msgId = this.msg.msg_id;
    wrapper.dataset.from = this.msg.from;
    wrapper.dataset.time = this.msg.time;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    // Sender name
    if (!this.isOwn && (this.msg.to === 'global' || this.msg.to && this.msg.to !== 'global')) {
      const senderRow = this._createSenderRow();
      bubble.appendChild(senderRow);
    }

    // Reply-to preview
    if (this.msg.reply_to) {
      const replyDiv = this._createReplyPreview();
      bubble.appendChild(replyDiv);
    }

    // Content
    const content = this._createContent();
    bubble.appendChild(content);

    // Time
    const time = this._createTime();
    bubble.appendChild(time);

    // Action buttons
    if (this.msg.msg_id && !this.msg.deleted && this.msg.type === 'text') {
      const actions = this._createActions();
      bubble.appendChild(actions);
    }

    wrapper.appendChild(bubble);
    return wrapper;
  }

  /**
   * Create sender row
   * @private
   * @returns {HTMLElement} Sender row element
   */
  _createSenderRow() {
    const senderRow = document.createElement('div');
    senderRow.className = 'bubble-sender';
    senderRow.style.color = this._safeColor(this.msg.color);

    const nameSpan = document.createElement('span');
    nameSpan.textContent = this.msg.from;

    const repBadge = document.createElement('span');
    repBadge.className = 'rep-badge rep-' + (this.msg.reputation || 'New').toLowerCase();
    repBadge.textContent = this.msg.reputation || 'New';

    senderRow.appendChild(nameSpan);
    senderRow.appendChild(repBadge);
    return senderRow;
  }

  /**
   * Create reply preview
   * @private
   * @returns {HTMLElement} Reply preview element
   */
  _createReplyPreview() {
    const replyDiv = document.createElement('div');
    replyDiv.className = 'reply-preview';
    const origText = this.msg.reply_to.text || '[file]';
    replyDiv.innerHTML = `<strong>${this._escapeHtml(this.msg.reply_to.from || '?')}</strong>${this._escapeHtml(origText.slice(0, 80))}`;
    replyDiv.onclick = () => this._scrollToMsg(this.msg.reply_to.msg_id);
    return replyDiv;
  }

  /**
   * Create content element
   * @private
   * @returns {HTMLElement} Content element
   */
  _createContent() {
    if (this.msg.deleted) {
      const text = document.createElement('div');
      text.className = 'bubble-text';
      text.textContent = '🗑️ This message was deleted';
      text.style.opacity = '0.5';
      text.style.fontStyle = 'italic';
      return text;
    } else if (this.msg.type === 'text') {
      const text = document.createElement('div');
      text.className = 'bubble-text';
      text.textContent = this.msg.text;
      if (this.msg.edited) {
        const label = document.createElement('span');
        label.className = 'edited-label';
        label.textContent = ' (edited)';
        text.appendChild(label);
      }
      return text;
    } else if (this.msg.type === 'file') {
      return this._renderFileContent();
    }
    const text = document.createElement('div');
    text.className = 'bubble-text';
    text.textContent = '[Unsupported message type]';
    return text;
  }

  /**
   * Create time element
   * @private
   * @returns {HTMLElement} Time element
   */
  _createTime() {
    const time = document.createElement('div');
    time.className = 'bubble-time';
    time.textContent = this._formatTime(this.msg.time);
    return time;
  }

  /**
   * Create action buttons
   * @private
   * @returns {HTMLElement} Actions element
   */
  _createActions() {
    const actions = document.createElement('div');
    actions.className = 'msg-actions';

    const replyBtn = document.createElement('button');
    replyBtn.className = 'msg-action-btn';
    replyBtn.title = 'Reply';
    replyBtn.textContent = '↩️';
    replyBtn.onclick = () => this.onReply(this.msg);
    actions.appendChild(replyBtn);

    if (this.isOwn) {
      const editBtn = document.createElement('button');
      editBtn.className = 'msg-action-btn';
      editBtn.title = 'Edit';
      editBtn.textContent = '✏️';
      editBtn.onclick = () => this.onEdit(this.msg);
      actions.appendChild(editBtn);

      const delBtn = document.createElement('button');
      delBtn.className = 'msg-action-btn';
      delBtn.title = 'Delete';
      delBtn.textContent = '🗑️';
      delBtn.onclick = () => this.onDelete(this.msg);
      actions.appendChild(delBtn);
    }

    return actions;
  }

  /**
   * Render file content
   * @private
   * @returns {HTMLElement} File element
   */
  _renderFileContent() {
    const ft = this.msg.file_type || '';
    if (ft.startsWith('image/')) {
      const img = document.createElement('img');
      img.src = this._safeUrl(this.msg.url);
      img.alt = this.msg.name;
      img.onclick = () => this._openLightbox(this.msg.url);
      return img;
    } else if (ft.startsWith('audio/') || this.msg.name?.endsWith('.webm')) {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.src = this._safeUrl(this.msg.url);
      return audio;
    } else if (ft.startsWith('video/')) {
      const video = document.createElement('video');
      video.controls = true;
      video.src = this._safeUrl(this.msg.url);
      video.style.maxWidth = '260px';
      video.style.borderRadius = '6px';
      return video;
    } else {
      const a = document.createElement('a');
      a.className = 'file-attach';
      a.href = this._safeUrl(this.msg.url);
      a.target = '_blank';
      a.download = this.msg.name;
      a.rel = 'noopener noreferrer';

      const icon = document.createElement('span');
      icon.className = 'file-attach-icon';
      icon.textContent = '📎';

      const info = document.createElement('div');
      const nameEl = document.createElement('div');
      nameEl.className = 'file-attach-name';
      nameEl.textContent = this.msg.name;

      const sizeEl = document.createElement('div');
      sizeEl.className = 'file-attach-size';
      sizeEl.textContent = 'Tap to download';

      info.appendChild(nameEl);
      info.appendChild(sizeEl);
      a.appendChild(icon);
      a.appendChild(info);
      return a;
    }
  }

  /**
   * Format timestamp
   * @private
   * @param {number} ts - Timestamp
   * @returns {string} Formatted time
   */
  _formatTime(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  /**
   * Escape HTML
   * @private
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  _escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /**
   * Sanitize URL
   * @private
   * @param {string} url - URL to sanitize
   * @returns {string} Safe URL
   */
  _safeUrl(url) {
    if (typeof url !== 'string') return '';
    const trimmed = url.trim();
    if (trimmed.startsWith('/uploads/')) return trimmed;
    if (trimmed.startsWith('blob:')) return trimmed;
    return '';
  }

  /**
   * Sanitize color
   * @private
   * @param {string} color - Color to sanitize
   * @param {string} fallback - Fallback color
   * @returns {string} Safe color
   */
  _safeColor(color, fallback = '#25d366') {
    if (typeof color !== 'string') return fallback;
    const c = color.trim();
    if (/^#[0-9a-fA-F]{3}$/.test(c) || /^#[0-9a-fA-F]{6}$/.test(c)) return c;
    const allowed = new Set(['#25D366', '#00a884', '#53bdeb', '#f0b429', '#e06c75', '#c678dd', '#56b6c2', '#e5c07b']);
    if (allowed.has(c.toUpperCase()) || allowed.has(c)) return c;
    return fallback;
  }

  /**
   * Scroll to message
   * @private
   * @param {string} msgId - Message ID
   */
  _scrollToMsg(msgId) {
    const el = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.style.outline = '2px solid var(--accent)';
      setTimeout(() => { el.style.outline = ''; }, 1500);
    }
  }

  /**
   * Open lightbox
   * @private
   * @param {string} url - Image URL
   */
  _openLightbox(url) {
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
      document.getElementById('lightbox-img').src = this._safeUrl(url);
      lightbox.classList.add('active');
    }
  }
}
