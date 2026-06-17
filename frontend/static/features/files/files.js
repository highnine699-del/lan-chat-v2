/**
 * features/files/files.js
 * 
 * File upload/download feature.
 * Handles file selection, upload, and download.
 */

import { eventBus } from '../../core/eventBus.js';

export const files = {
  /**
   * Select and upload a file
   * @param {Function} onUpload - Upload callback
   */
  selectFile(onUpload) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '*/*';
    input.onchange = (e) => {
      if (e.target.files[0]) {
        this.uploadFile(e.target.files[0], onUpload);
      }
    };
    input.click();
  },

  /**
   * Upload a file
   * @param {File} file - File to upload
   * @param {Function} onUpload - Upload callback
   */
  async uploadFile(file, onUpload) {
    const formData = new FormData();
    formData.append('file', file);

    eventBus.emit('file:uploading', file);

    try {
      const res = await fetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok) {
        eventBus.emit('file:upload_failed', data.error || `Server error ${res.status}`);
        if (onUpload) onUpload(null, data.error || `Server error ${res.status}`);
        return;
      }

      eventBus.emit('file:uploaded', data);
      if (onUpload) onUpload(data, null);
    } catch (err) {
      eventBus.emit('file:upload_error', err.message);
      if (onUpload) onUpload(null, err.message);
    }
  },

  /**
   * Alias for uploadFile - for compatibility
   * @param {File} file - File to upload
   * @param {Function} onUpload - Upload callback
   */
  async upload(file, onUpload) {
    return this.uploadFile(file, onUpload);
  },

  /**
   * Download a file
   * @param {string} url - File URL
   * @param {string} name - File name
   */
  downloadFile(url, name) {
    const a = document.createElement('a');
    a.href = this._safeUrl(url);
    a.download = name;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.click();
    eventBus.emit('file:downloaded', { url, name });
  },

  /**
   * Get file icon based on type
   * @param {string} fileType - File MIME type
   * @returns {string} Emoji icon
   */
  getFileIcon(fileType) {
    if (!fileType) return '📎';
    if (fileType.startsWith('image/')) return '🖼️';
    if (fileType.startsWith('video/')) return '🎬';
    if (fileType.startsWith('audio/')) return '🎵';
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('word') || fileType.includes('document')) return '📝';
    if (fileType.includes('excel') || fileType.includes('spreadsheet')) return '📊';
    if (fileType.includes('zip') || fileType.includes('rar')) return '📦';
    return '📎';
  },

  /**
   * Format file size
   * @param {number} bytes - File size in bytes
   * @returns {string} Formatted size
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
  }
};
