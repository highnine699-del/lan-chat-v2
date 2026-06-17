/**
 * core/state/mediaState.js
 * 
 * Media state - streams, recorders, audio chunks.
 * Pure functions only, no side effects.
 */

export const mediaState = {
  localStream: null,
  mediaRecorder: null,
  audioChunks: [],
  recordTimer: null,
  recordSeconds: 0,
  recordMime: null,
  stopWave: null,

  /**
   * Set local media stream
   * @param {MediaStream} stream - Media stream
   */
  setLocalStream(stream) {
    this.localStream = stream;
  },

  /**
   * Get local media stream
   * @returns {MediaStream|null} Media stream or null
   */
  getLocalStream() {
    return this.localStream;
  },

  /**
   * Clear local stream
   */
  clearLocalStream() {
    this.localStream = null;
  },

  /**
   * Set media recorder
   * @param {MediaRecorder} recorder - Media recorder
   */
  setMediaRecorder(recorder) {
    this.mediaRecorder = recorder;
  },

  /**
   * Get media recorder
   * @returns {MediaRecorder|null} Media recorder or null
   */
  getMediaRecorder() {
    return this.mediaRecorder;
  },

  /**
   * Clear media recorder
   */
  clearMediaRecorder() {
    this.mediaRecorder = null;
  },

  /**
   * Add audio chunk
   * @param {Blob} chunk - Audio chunk
   */
  addAudioChunk(chunk) {
    this.audioChunks.push(chunk);
  },

  /**
   * Get audio chunks
   * @returns {Array} Audio chunks array
   */
  getAudioChunks() {
    return this.audioChunks;
  },

  /**
   * Clear audio chunks
   */
  clearAudioChunks() {
    this.audioChunks = [];
  },

  /**
   * Set record timer
   * @param {number} timerId - Timer ID
   */
  setRecordTimer(timerId) {
    this.recordTimer = timerId;
  },

  /**
   * Get record timer
   * @returns {number|null} Timer ID or null
   */
  getRecordTimer() {
    return this.recordTimer;
  },

  /**
   * Clear record timer
   */
  clearRecordTimer() {
    if (this.recordTimer) {
      clearInterval(this.recordTimer);
      this.recordTimer = null;
    }
  },

  /**
   * Set record seconds
   * @param {number} seconds - Record seconds
   */
  setRecordSeconds(seconds) {
    this.recordSeconds = seconds;
  },

  /**
   * Get record seconds
   * @returns {number} Record seconds
   */
  getRecordSeconds() {
    return this.recordSeconds;
  },

  /**
   * Reset record seconds
   */
  resetRecordSeconds() {
    this.recordSeconds = 0;
  },

  /**
   * Set record MIME type
   * @param {string} mime - MIME type
   */
  setRecordMime(mime) {
    this.recordMime = mime;
  },

  /**
   * Get record MIME type
   * @returns {string|null} MIME type or null
   */
  getRecordMime() {
    return this.recordMime;
  },

  /**
   * Set stop waveform function
   * @param {Function} fn - Stop function
   */
  setStopWave(fn) {
    this.stopWave = fn;
  },

  /**
   * Call stop waveform function
   */
  callStopWave() {
    if (this.stopWave) {
      this.stopWave();
      this.stopWave = null;
    }
  }
};
