/**
 * ui/pages/ChatPage.js
 * 
 * Chat page component - main chat interface.
 * Handles message display, input, and chat switching.
 * V2: Attaches event listeners to DOM elements, replacing inline HTML handlers.
 */

import { chatState } from '../../core/state/chatState.js';
import { uiState } from '../../core/state/uiState.js';
import { eventBus } from '../../core/eventBus.js';
import { InputBar } from '../components/InputBar.js';
import { MessageItem } from '../components/MessageItem.js';

export class ChatPage {
  constructor(options = {}) {
    this.onSend = options.onSend || (() => {});
    this.onTyping = options.onTyping || (() => {});
    this.onStopTyping = options.onStopTyping || (() => {});
    this.onFileUpload = options.onFileUpload || (() => {});
    this.onVoiceRecord = options.onVoiceRecord || (() => {});
    this.onEmojiToggle = options.onEmojiToggle || (() => {});
    this.onReply = options.onReply || (() => {});
    this.onEdit = options.onEdit || (() => {});
    this.onDelete = options.onDelete || (() => {});
    this.element = null;
    this.inputBar = null;
    this.messageItems = new Map();
    this._listenersAttached = false;
  }

  /**
   * Initialize chat page - attach event listeners to DOM elements
   * This replaces inline HTML handlers with addEventListener
   */
  init() {
    if (this._listenersAttached) return;

    // Attach listeners to existing DOM elements
    this._attachMessageInputListeners();
    this._attachFileUploadListeners();
    this._attachScrollToBottomListeners();
    this._attachChatSearchListeners();

    this._listenersAttached = true;
    console.log('[LAN Chat V2] [DEBUG] ChatPage event listeners attached');
  }

  /**
   * Attach listeners to message input
   * @private
   */
  _attachMessageInputListeners() {
    const msgInput = document.getElementById('msg-input');
    if (msgInput) {
      // Handle Enter key to send
      msgInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.onSend();
        }
      });

      // Handle typing indicator
      msgInput.addEventListener('input', (e) => {
        this.onTyping(e.target.value);
      });
    }
  }

  /**
   * Attach listeners to file upload
   * @private
   */
  _attachFileUploadListeners() {
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
          this.onFileUpload(e.target.files[0]);
        }
      });
    }
  }

  /**
   * Attach listeners to scroll to bottom
   * @private
   */
  _attachScrollToBottomListeners() {
    const scrollBtn = document.getElementById('scroll-to-bottom');
    if (scrollBtn) {
      scrollBtn.addEventListener('click', () => {
        this.scrollToBottom();
      });
    }
  }

  /**
   * Attach listeners to chat search
   * @private
   */
  _attachChatSearchListeners() {
    const searchInput = document.getElementById('search-box');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this._filterChats(e.target.value);
      });

      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          const searchContainer = document.getElementById('chat-search');
          if (searchContainer) {
            searchContainer.style.display = 'none';
          }
        }
      });
    }
  }

  /**
   * Filter chats by search query
   * @private
   * @param {string} query - Search query
   */
  _filterChats(query) {
    const lowerQuery = query.toLowerCase();
    const items = document.querySelectorAll('.chat-item');
    items.forEach(item => {
      const name = item.querySelector('.chat-name')?.textContent.toLowerCase() || '';
      item.style.display = name.includes(lowerQuery) ? 'flex' : 'none';
    });
  }

  /**
   * Render the chat page
   * @returns {HTMLElement} Chat page element
   */
  render() {
    this.element = this._createElement();
    this.inputBar = new InputBar({
      onSend: this.onSend,
      onTyping: this.onTyping,
      onStopTyping: this.onStopTyping,
      onFileUpload: this.onFileUpload,
      onVoiceRecord: this.onVoiceRecord,
      onEmojiToggle: this.onEmojiToggle,
    });
    this.element.querySelector('.input-container').appendChild(this.inputBar.render());
    return this.element;
  }

  /**
   * Update messages display
   * @param {Array} messages - Messages array
   * @param {string} myDisplay - My display name
   */
  updateMessages(messages, myDisplay) {
    const container = this.element?.querySelector('#messages');
    if (!container) return;

    container.innerHTML = '';
    this.messageItems.clear();

    messages.forEach(msg => {
      const isOwn = msg.from === myDisplay;
      const isMuted = chatState.isMuted(msg.from);
      const item = new MessageItem(msg, {
        isOwn,
        isMuted,
        onReply: this.onReply,
        onEdit: this.onEdit,
        onDelete: this.onDelete,
      });
      const el = item.render();
      if (el) {
        container.appendChild(el);
        this.messageItems.set(msg.msg_id, item);
      }
    });
  }

  /**
   * Add a single message
   * @param {Object} msg - Message object
   * @param {string} myDisplay - My display name
   */
  addMessage(msg, myDisplay) {
    const container = this.element?.querySelector('#messages');
    if (!container) return;

    const isOwn = msg.from === myDisplay;
    const isMuted = chatState.isMuted(msg.from);
    const item = new MessageItem(msg, {
      isOwn,
      isMuted,
      onReply: this.onReply,
      onEdit: this.onEdit,
      onDelete: this.onDelete,
    });
    const el = item.render();
    if (el) {
      container.appendChild(el);
      this.messageItems.set(msg.msg_id, item);
    }
  }

  /**
   * Update a message
   * @param {Object} msg - Updated message object
   */
  updateMessage(msg) {
    const item = this.messageItems.get(msg.msg_id);
    if (item) {
      item.update(msg);
    }
  }

  /**
   * Remove a message
   * @param {string} msgId - Message ID
   */
  removeMessage(msgId) {
    const item = this.messageItems.get(msgId);
    if (item) {
      item.destroy();
      this.messageItems.delete(msgId);
    }
  }

  /**
   * Scroll to bottom
   */
  scrollToBottom() {
    const container = this.element?.querySelector('#messages');
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }
  }

  /**
   * Update typing indicator
   * @param {string} html - HTML string for typing indicator
   */
  updateTypingIndicator(html) {
    const indicator = this.element?.querySelector('#typing-indicator');
    if (indicator) {
      indicator.innerHTML = html;
    }
  }

  /**
   * Update header
   * @param {Object} headerData - Header data { name, status, avatar }
   */
  updateHeader(headerData) {
    const nameEl = this.element?.querySelector('#header-name');
    const statusEl = this.element?.querySelector('#header-status');
    const avatarEl = this.element?.querySelector('#header-avatar');

    if (nameEl) nameEl.textContent = headerData.name;
    if (statusEl) statusEl.textContent = headerData.status;
    if (avatarEl && headerData.avatar) {
      avatarEl.style.background = headerData.avatar.background;
      avatarEl.textContent = headerData.avatar.text;
    }
  }

  /**
   * Show/hide call buttons
   * @param {boolean} show - Show or hide
   */
  toggleCallButtons(show) {
    const actions = this.element?.querySelector('.header-actions');
    if (actions) {
      actions.style.display = show ? 'flex' : 'none';
    }
  }

  /**
   * Remove the element from DOM
   */
  destroy() {
    if (this.inputBar) {
      this.inputBar.destroy();
      this.inputBar = null;
    }
    this.messageItems.forEach(item => item.destroy());
    this.messageItems.clear();
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
  }

  /**
   * Create chat page element
   * @private
   * @returns {HTMLElement} Chat page element
   */
  _createElement() {
    const page = document.createElement('div');
    page.className = 'chat-page';

    const header = this._createHeader();
    const messages = this._createMessagesContainer();
    const typing = this._createTypingIndicator();
    const inputContainer = this._createInputContainer();

    page.appendChild(header);
    page.appendChild(messages);
    page.appendChild(typing);
    page.appendChild(inputContainer);

    return page;
  }

  /**
   * Create header
   * @private
   * @returns {HTMLElement} Header element
   */
  _createHeader() {
    const header = document.createElement('div');
    header.className = 'chat-header';

    const avatar = document.createElement('div');
    avatar.id = 'header-avatar';
    avatar.className = 'header-avatar';
    avatar.textContent = '👤';

    const info = document.createElement('div');
    info.className = 'header-info';

    const name = document.createElement('div');
    name.id = 'header-name';
    name.className = 'header-name';
    name.textContent = 'Global Chat';

    const status = document.createElement('div');
    status.id = 'header-status';
    status.className = 'header-status';
    status.textContent = 'Loading...';

    const actions = document.createElement('div');
    actions.className = 'header-actions';
    actions.style.display = 'none';

    info.appendChild(name);
    info.appendChild(status);
    header.appendChild(avatar);
    header.appendChild(info);
    header.appendChild(actions);

    return header;
  }

  /**
   * Create messages container
   * @private
   * @returns {HTMLElement} Messages container
   */
  _createMessagesContainer() {
    const container = document.createElement('div');
    container.id = 'messages';
    container.className = 'messages';
    return container;
  }

  /**
   * Create typing indicator
   * @private
   * @returns {HTMLElement} Typing indicator
   */
  _createTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'typing-indicator';
    return indicator;
  }

  /**
   * Create input container
   * @private
   * @returns {HTMLElement} Input container
   */
  _createInputContainer() {
    const container = document.createElement('div');
    container.className = 'input-container';
    return container;
  }
}
