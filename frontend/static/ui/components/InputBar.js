/**
 * ui/components/InputBar.js
 * 
 * Input bar component - message input with file/voice/emoji support.
 */

export class InputBar {
  constructor(options = {}) {
    this.onSend = options.onSend || (() => {});
    this.onTyping = options.onTyping || (() => {});
    this.onStopTyping = options.onStopTyping || (() => {});
    this.onFileUpload = options.onFileUpload || (() => {});
    this.onVoiceRecord = options.onVoiceRecord || (() => {});
    this.onEmojiToggle = options.onEmojiToggle || (() => {});
    this.element = null;
    this.typingTimeout = null;
  }

  /**
   * Render the input bar
   * @returns {HTMLElement} Input bar element
   */
  render() {
    this.element = this._createElement();
    this._attachEventListeners();
    return this.element;
  }

  /**
   * Get the input value
   * @returns {string} Input value
   */
  getValue() {
    const input = this.element?.querySelector('#msg-input');
    return input ? input.value : '';
  }

  /**
   * Set the input value
   * @param {string} value - Input value
   */
  setValue(value) {
    const input = this.element?.querySelector('#msg-input');
    if (input) {
      input.value = value;
      input.style.height = 'auto';
    }
  }

  /**
   * Clear the input
   */
  clear() {
    this.setValue('');
  }

  /**
   * Focus the input
   */
  focus() {
    const input = this.element?.querySelector('#msg-input');
    if (input) input.focus();
  }

  /**
   * Remove the element from DOM
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
    if (this.typingTimeout) {
      clearTimeout(this.typingTimeout);
      this.typingTimeout = null;
    }
  }

  /**
   * Create input bar element
   * @private
   * @returns {HTMLElement} Input bar element
   */
  _createElement() {
    const container = document.createElement('div');
    container.className = 'input-bar';

    const fileBtn = this._createFileButton();
    const emojiBtn = this._createEmojiButton();
    const micBtn = this._createMicButton();
    const input = this._createInput();
    const sendBtn = this._createSendButton();

    container.appendChild(fileBtn);
    container.appendChild(emojiBtn);
    container.appendChild(micBtn);
    container.appendChild(input);
    container.appendChild(sendBtn);

    return container;
  }

  /**
   * Create file button
   * @private
   * @returns {HTMLElement} File button element
   */
  _createFileButton() {
    const btn = document.createElement('button');
    btn.className = 'input-btn file-btn';
    btn.innerHTML = '📎';
    btn.title = 'Attach file';
    btn.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '*/*';
      input.addEventListener('change', (e) => {
        if (e.target.files[0]) this.onFileUpload(e.target.files[0]);
      });
      input.click();
    });
    return btn;
  }

  /**
   * Create emoji button
   * @private
   * @returns {HTMLElement} Emoji button element
   */
  _createEmojiButton() {
    const btn = document.createElement('button');
    btn.className = 'input-btn emoji-btn';
    btn.innerHTML = '😊';
    btn.title = 'Emoji';
    btn.id = 'emoji-btn';
    btn.addEventListener('click', () => this.onEmojiToggle());
    return btn;
  }

  /**
   * Create microphone button
   * @private
   * @returns {HTMLElement} Mic button element
   */
  _createMicButton() {
    const btn = document.createElement('button');
    btn.className = 'input-btn mic-btn';
    btn.innerHTML = '🎤';
    btn.title = 'Voice message';
    btn.id = 'mic-btn';
    btn.addEventListener('click', () => this.onVoiceRecord());
    return btn;
  }

  /**
   * Create input element
   * @private
   * @returns {HTMLElement} Input element
   */
  _createInput() {
    const input = document.createElement('textarea');
    input.className = 'msg-input';
    input.id = 'msg-input';
    input.placeholder = 'Type a message...';
    input.rows = 1;
    input.maxLength = 4000;
    return input;
  }

  /**
   * Create send button
   * @private
   * @returns {HTMLElement} Send button element
   */
  _createSendButton() {
    const btn = document.createElement('button');
    btn.className = 'send-btn';
    btn.innerHTML = '➤';
    btn.title = 'Send';
    btn.addEventListener('click', () => this._handleSend());
    return btn;
  }

  /**
   * Attach event listeners
   * @private
   */
  _attachEventListeners() {
    const input = this.element?.querySelector('#msg-input');
    if (!input) return;

    input.addEventListener('input', () => this._handleInput());
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._handleSend();
      }
    });
  }

  /**
   * Handle input event
   * @private
   */
  _handleInput() {
    const input = this.element?.querySelector('#msg-input');
    if (!input) return;

    // Auto-resize
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';

    // Send button glow
    const sendBtn = this.element?.querySelector('.send-btn');
    if (sendBtn) {
      sendBtn.classList.toggle('typing', input.value.trim().length > 0);
    }

    // Typing indicator
    this.onTyping();
    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.onStopTyping();
    }, 1500);
  }

  /**
   * Handle send
   * @private
   */
  _handleSend() {
    const input = this.element?.querySelector('#msg-input');
    if (!input) return;

    const text = input.value.trim();
    if (text) {
      this.onSend(text);
      this.clear();
    }
  }
}
