/**
 * ui/components/Modal.js
 * 
 * Modal component - reusable modal dialog.
 */

export class Modal {
  constructor(options = {}) {
    this.title = options.title || '';
    this.content = options.content || '';
    this.onClose = options.onClose || (() => {});
    this.onConfirm = options.onConfirm || (() => {});
    this.showConfirm = options.showConfirm || false;
    this.confirmText = options.confirmText || 'Confirm';
    this.element = null;
  }

  /**
   * Render the modal
   * @returns {HTMLElement} Modal element
   */
  render() {
    this.element = this._createElement();
    this._attachEventListeners();
    return this.element;
  }

  /**
   * Show the modal
   */
  show() {
    if (this.element) {
      this.element.style.display = 'flex';
      requestAnimationFrame(() => {
        this.element.classList.add('active');
      });
    }
  }

  /**
   * Hide the modal
   */
  hide() {
    if (this.element) {
      this.element.classList.remove('active');
      setTimeout(() => {
        this.element.style.display = 'none';
      }, 200);
    }
  }

  /**
   * Update modal content
   * @param {Object} options - Update options
   */
  update(options) {
    if (options.title !== undefined) this.title = options.title;
    if (options.content !== undefined) this.content = options.content;
    if (options.showConfirm !== undefined) this.showConfirm = options.showConfirm;
    if (options.confirmText !== undefined) this.confirmText = options.confirmText;

    if (this.element) {
      const titleEl = this.element.querySelector('.modal-title');
      const contentEl = this.element.querySelector('.modal-content');
      const confirmBtn = this.element.querySelector('.modal-confirm-btn');

      if (titleEl) titleEl.textContent = this.title;
      if (contentEl) contentEl.innerHTML = this.content;
      if (confirmBtn) {
        confirmBtn.textContent = this.confirmText;
        confirmBtn.style.display = this.showConfirm ? 'inline-block' : 'none';
      }
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
   * Create modal element
   * @private
   * @returns {HTMLElement} Modal element
   */
  _createElement() {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';

    const modal = document.createElement('div');
    modal.className = 'modal';

    const header = this._createHeader();
    const body = this._createBody();
    const footer = this._createFooter();

    modal.appendChild(header);
    modal.appendChild(body);
    modal.appendChild(footer);
    backdrop.appendChild(modal);

    return backdrop;
  }

  /**
   * Create header
   * @private
   * @returns {HTMLElement} Header element
   */
  _createHeader() {
    const header = document.createElement('div');
    header.className = 'modal-header';

    const title = document.createElement('h3');
    title.className = 'modal-title';
    title.textContent = this.title;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close-btn';
    closeBtn.innerHTML = '✕';
    closeBtn.onclick = () => this.hide();

    header.appendChild(title);
    header.appendChild(closeBtn);

    return header;
  }

  /**
   * Create body
   * @private
   * @returns {HTMLElement} Body element
   */
  _createBody() {
    const body = document.createElement('div');
    body.className = 'modal-body';

    const content = document.createElement('div');
    content.className = 'modal-content';
    content.innerHTML = this.content;

    body.appendChild(content);

    return body;
  }

  /**
   * Create footer
   * @private
   * @returns {HTMLElement} Footer element
   */
  _createFooter() {
    const footer = document.createElement('div');
    footer.className = 'modal-footer';

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'modal-cancel-btn';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onclick = () => this.hide();

    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'modal-confirm-btn';
    confirmBtn.textContent = this.confirmText;
    confirmBtn.style.display = this.showConfirm ? 'inline-block' : 'none';
    confirmBtn.onclick = () => {
      this.onConfirm();
      this.hide();
    };

    footer.appendChild(cancelBtn);
    footer.appendChild(confirmBtn);

    return footer;
  }

  /**
   * Attach event listeners
   * @private
   */
  _attachEventListeners() {
    if (this.element) {
      this.element.addEventListener('click', (e) => {
        if (e.target === this.element) {
          this.hide();
        }
      });
    }
  }
}
