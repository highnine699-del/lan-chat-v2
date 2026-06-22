/**
 * ui/pages/CallUI.js
 * 
 * Call UI page component - call interface with voice/video controls.
 * Handles call start/end, mute, camera toggle, and call status display.
 * V2: Attaches event listeners to DOM elements, replacing inline HTML handlers.
 */

import { chatState } from '../../core/state/chatState.js';
import { eventBus } from '../../core/eventBus.js';

export class CallUI {
  constructor(options = {}) {
    this.onStartCall = options.onStartCall || (() => {});
    this.onEndCall = options.onEndCall || (() => {});
    this.onToggleMute = options.onToggleMute || (() => {});
    this.onToggleCamera = options.onToggleCamera || (() => {});
    this._listenersAttached = false;
  }

  /**
   * Initialize call UI - attach event listeners to DOM elements
   * This replaces inline HTML handlers with addEventListener
   */
  init() {
    if (this._listenersAttached) return;

    // Attach listeners to existing DOM elements
    this._attachCallButtonListeners();
    this._attachCallControlListeners();
    this._attachCallOverlayListeners();

    this._listenersAttached = true;
    console.log('[LAN Chat V2] [DEBUG] CallUI event listeners attached');
  }

  /**
   * Attach listeners to call buttons
   * @private
   */
  _attachCallButtonListeners() {
    const voiceCallBtn = document.getElementById('voice-call-btn');
    if (voiceCallBtn) {
      voiceCallBtn.addEventListener('click', () => {
        this.onStartCall('voice');
      });
    }

    const videoCallBtn = document.getElementById('video-call-btn');
    if (videoCallBtn) {
      videoCallBtn.addEventListener('click', () => {
        this.onStartCall('video');
      });
    }
  }

  /**
   * Attach listeners to call controls
   * @private
   */
  _attachCallControlListeners() {
    // NOTE: end-call-btn is handled exclusively by callSession.init() to avoid
    // double-firing lifecycle.endCall(). Do NOT add another listener here.

    const muteBtn = document.getElementById('mute-btn');
    if (muteBtn) {
      muteBtn.addEventListener('click', () => {
        this.onToggleMute();
      });
    }

    // HTML id is 'cam-btn' — not 'camera-btn'
    const cameraBtn = document.getElementById('cam-btn');
    if (cameraBtn) {
      cameraBtn.addEventListener('click', () => {
        this.onToggleCamera();
      });
    }
  }

  /**
   * Attach listeners to call overlay
   * @private
   */
  _attachCallOverlayListeners() {
    const overlay = document.getElementById('call-overlay');
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          // Click outside to minimize (optional)
        }
      });
    }
  }

  /**
   * Show call overlay
   * @param {Object} callData - Call data { type, target, sessionId }
   */
  showCallOverlay(callData) {
    const overlay = document.getElementById('call-overlay');
    if (overlay) {
      overlay.style.display = 'flex';
      this._updateCallInfo(callData);
    }
  }

  /**
   * Hide call overlay
   */
  hideCallOverlay() {
    const overlay = document.getElementById('call-overlay');
    if (overlay) {
      overlay.style.display = 'none';
    }
  }

  /**
   * Update call info display
   * @private
   * @param {Object} callData - Call data
   */
  _updateCallInfo(callData) {
    const statusEl = document.getElementById('call-status');
    const targetEl = document.getElementById('call-target');
    const typeEl = document.getElementById('call-type');

    if (statusEl) {
      statusEl.textContent = 'Connecting...';
    }
    if (targetEl) {
      targetEl.textContent = callData.target || 'Unknown';
    }
    if (typeEl) {
      typeEl.textContent = callData.type === 'video' ? '📹 Video Call' : '📞 Voice Call';
    }
  }

  /**
   * Update call status
   * @param {string} status - Call status
   */
  updateCallStatus(status) {
    const statusEl = document.getElementById('call-status');
    if (statusEl) {
      statusEl.textContent = status;
    }
  }

  /**
   * Update mute button state
   * @param {boolean} muted - Muted state
   */
  updateMuteState(muted) {
    const muteBtn = document.getElementById('mute-btn');
    if (muteBtn) {
      muteBtn.classList.toggle('muted', muted);
      muteBtn.innerHTML = muted ? '🔇' : '🎤';
    }
  }

  /**
   * Update camera button state
   * @param {boolean} off - Camera off state
   */
  updateCameraState(off) {
    const cameraBtn = document.getElementById('cam-btn'); // HTML id is cam-btn
    if (cameraBtn) {
      cameraBtn.classList.toggle('cam-off', off);
      cameraBtn.title = off ? 'Camera on' : 'Camera off';
    }
  }

  /**
   * Show/hide call buttons in header
   * @param {boolean} show - Show or hide
   */
  toggleCallButtons(show) {
    const actions = document.querySelector('.header-actions');
    if (actions) {
      actions.style.display = show ? 'flex' : 'none';
    }
  }
}
