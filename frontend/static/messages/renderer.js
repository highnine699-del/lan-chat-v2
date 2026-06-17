/**
 * messages/renderer.js
 * 
 * Message DOM rendering component.
 * Creates message elements with proper styling and event handlers.
 */

export const renderer = {
  /**
   * Create a message DOM element
   * @param {Object} msg - Message object
   * @param {Object} options - Rendering options
   * @returns {HTMLElement} Message element
   */
  createMessageElement(msg, options = {}) {
    const {
      isMuted = false,
      isOwn = false,
      isReplying = false,
      onReply = () => {},
      onReact = () => {},
      onDelete = () => {},
      onEdit = () => {}
    } = options;

    // Skip muted messages
    if (!isOwn && isMuted) return null;

    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper ' + (isOwn ? 'me' : 'other');
    if (msg.msg_id) wrapper.dataset.msgId = msg.msg_id;
    wrapper.dataset.from = msg.from;
    wrapper.dataset.time = msg.time;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    // Sender name for global/room messages
    if (!isOwn && (msg.to === 'global' || msg.to && msg.to !== 'global')) {
      const senderRow = document.createElement('div');
      senderRow.className = 'bubble-sender';
      senderRow.style.color = this._safeColor(msg.color);

      const nameSpan = document.createElement('span');
      nameSpan.textContent = msg.from;

      const repBadge = document.createElement('span');
      repBadge.className = 'rep-badge rep-' + (msg.reputation || 'New').toLowerCase();
      repBadge.textContent = msg.reputation || 'New';

      senderRow.appendChild(nameSpan);
      senderRow.appendChild(repBadge);
      bubble.appendChild(senderRow);
    }

    // Reply-to preview
    if (msg.reply_to) {
      const replyDiv = document.createElement('div');
      replyDiv.className = 'reply-preview';
      const origText = msg.reply_to.text || '[file]';
      replyDiv.innerHTML = `<strong>${this._escapeHtml(msg.reply_to.from || '?')}</strong>${this._escapeHtml(origText.slice(0, 80))}`;
      replyDiv.onclick = () => this._scrollToMsg(msg.reply_to.msg_id);
      bubble.appendChild(replyDiv);
    }

    // Content
    if (msg.deleted) {
      const text = document.createElement('div');
      text.className = 'bubble-text';
      text.textContent = '🗑️ This message was deleted';
      text.style.opacity = '0.5';
      text.style.fontStyle = 'italic';
      bubble.appendChild(text);
    } else if (msg.type === 'text') {
      const text = document.createElement('div');
      text.className = 'bubble-text';
      text.textContent = msg.text;
      if (msg.edited) {
        const label = document.createElement('span');
        label.className = 'edited-label';
        label.textContent = ' (edited)';
        text.appendChild(label);
      }
      bubble.appendChild(text);
    } else if (msg.type === 'voice') {
      const wrapper = document.createElement('div');
      wrapper.className = 'voice-msg';

      const audio = document.createElement('audio');
      audio.controls = true;
      audio.src = this._safeUrl(msg.url);
      audio.style.maxWidth = '240px';

      const dur = msg.duration != null
        ? document.createElement('span')
        : null;
      if (dur) {
        const s = Math.round(msg.duration);
        dur.textContent = `🎙️ ${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
        dur.style.cssText = 'font-size:12px;color:var(--text-secondary);display:block;margin-top:4px;';
      }

      wrapper.appendChild(audio);
      if (dur) wrapper.appendChild(dur);
      bubble.appendChild(wrapper);
    } else if (msg.type === 'file') {
      const el = this._renderFileContent(msg);
      bubble.appendChild(el);
    }

    // Time
    const time = document.createElement('div');
    time.className = 'bubble-time';
    time.textContent = this._formatTime(msg.time);
    bubble.appendChild(time);

    // Action buttons
    if (msg.msg_id && !msg.deleted && msg.type === 'text') {
      const actions = document.createElement('div');
      actions.className = 'msg-actions';

      const replyBtn = document.createElement('button');
      replyBtn.className = 'msg-action-btn';
      replyBtn.title = 'Reply';
      replyBtn.textContent = '↩️';
      replyBtn.onclick = () => onReply(msg);
      actions.appendChild(replyBtn);

      if (isOwn) {
        const editBtn = document.createElement('button');
        editBtn.className = 'msg-action-btn';
        editBtn.title = 'Edit';
        editBtn.textContent = '✏️';
        editBtn.onclick = () => onEdit(msg);
        actions.appendChild(editBtn);

        const delBtn = document.createElement('button');
        delBtn.className = 'msg-action-btn';
        delBtn.title = 'Delete';
        delBtn.textContent = '🗑️';
        delBtn.onclick = () => onDelete(msg);
        actions.appendChild(delBtn);
      }

      bubble.appendChild(actions);
    }

    wrapper.appendChild(bubble);
    return wrapper;
  },

  /**
   * Render file content
   * @private
   * @param {Object} msg - Message object
   * @returns {HTMLElement} File element
   */
  _renderFileContent(msg) {
    const ft = msg.file_type || '';
    if (ft.startsWith('image/')) {
      const img = document.createElement('img');
      img.src = this._safeUrl(msg.url);
      img.alt = msg.name;
      img.onclick = () => this._openLightbox(msg.url);
      return img;
    } else if (ft.startsWith('audio/') || msg.name?.endsWith('.webm') || msg.name?.endsWith('.ogg') || msg.name?.endsWith('.mp3')) {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.src = this._safeUrl(msg.url);
      return audio;
    } else if (ft.startsWith('video/')) {
      const video = document.createElement('video');
      video.controls = true;
      video.src = this._safeUrl(msg.url);
      video.style.maxWidth = '260px';
      video.style.borderRadius = '6px';
      return video;
    } else {
      const a = document.createElement('a');
      a.className = 'file-attach';
      a.href = this._safeUrl(msg.url);
      a.target = '_blank';
      a.download = msg.name;
      a.rel = 'noopener noreferrer';

      const icon = document.createElement('span');
      icon.className = 'file-attach-icon';
      icon.textContent = '📎';

      const info = document.createElement('div');
      const nameEl = document.createElement('div');
      nameEl.className = 'file-attach-name';
      nameEl.textContent = msg.name;

      const sizeEl = document.createElement('div');
      sizeEl.className = 'file-attach-size';
      sizeEl.textContent = 'Tap to download';

      info.appendChild(nameEl);
      info.appendChild(sizeEl);
      a.appendChild(icon);
      a.appendChild(info);
      return a;
    }
  },

  /**
   * Format timestamp
   * @private
   * @param {number} ts - Timestamp
   * @returns {string} Formatted time
   */
  _formatTime(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },

  /**
   * Escape HTML
   * @private
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  _escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  },

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
  },

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
    const allowed = new Set([
      '#25D366', '#00a884', '#53bdeb', '#f0b429',
      '#e06c75', '#c678dd', '#56b6c2', '#e5c07b',
    ]);
    if (allowed.has(c.toUpperCase()) || allowed.has(c)) return c;
    return fallback;
  },

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
  },

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
};
