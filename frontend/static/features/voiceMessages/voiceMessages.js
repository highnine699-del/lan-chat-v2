/**
 * features/voiceMessages/voiceMessages.js
 * 
 * Voice message feature.
 * Handles voice recording, waveform visualization, and sending.
 */

import { mediaState } from '../../core/state/mediaState.js';
import { chatState } from '../../core/state/chatState.js';
import { eventBus } from '../../core/eventBus.js';

export const voiceMessages = {
  recordInterval: null,
  recordSeconds: 0,

  _busy: false,   // prevents concurrent startRecording calls

  /**
   * Start voice recording
   * @param {Function} onWaveformUpdate - Waveform update callback
   * @param {Function} onError - Error callback
   */
  async startRecording(onWaveformUpdate, onError) {
    if (this._busy) {
      console.warn('[VoiceMessages] Already starting/stopping, ignoring extra click');
      return;
    }
    this._busy = true;
    console.log('[VoiceMessages] startRecording called');
    try {
      console.log('[VoiceMessages] Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('[VoiceMessages] Microphone access granted, stream obtained');

      // Select best supported format
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
      ].find(t => MediaRecorder.isTypeSupported(t)) || '';

      console.log('[VoiceMessages] Selected MIME type:', mimeType);

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      console.log('[VoiceMessages] MediaRecorder created, state:', recorder.state);

      mediaState.setMediaRecorder(recorder);
      mediaState.setRecordMime(recorder.mimeType || mimeType || 'audio/webm');
      mediaState.clearAudioChunks();
      this.recordSeconds = 0;

      recorder.ondataavailable = e => mediaState.addAudioChunk(e.data);
      recorder.start(100);

      console.log('[VoiceMessages] MediaRecorder started');

      // Start waveform visualization
      this._startWaveform(stream, onWaveformUpdate);

      // Start timer
      this.recordInterval = setInterval(() => {
        this.recordSeconds++;
        eventBus.emit('voice:time_update', this.recordSeconds);
      }, 1000);

      eventBus.emit('voice:recording_started');
      console.log('[VoiceMessages] Recording started successfully');
      this._busy = false;
    } catch (err) {
      this._busy = false;
      console.error('[VoiceMessages] Recording error:', err);
      const msg = (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')
        ? 'Microphone access denied. Please allow microphone in your browser.'
        : `Recording failed: ${err.message}`;
      if (onError) onError(msg);
      eventBus.emit('voice:error', err);
    }
  },

  /**
   * Stop voice recording
   * @param {Function} onUpload - Upload callback
   */
  async stopRecording(onUpload) {
    const recorder = mediaState.getMediaRecorder();
    if (!recorder) return;

    clearInterval(this.recordInterval);
    mediaState.callStopWave();

    const mime = mediaState.getRecordMime() || 'audio/webm';
    const ext = mime.includes('mp4') ? 'mp4' : mime.includes('ogg') ? 'ogg' : 'webm';

    recorder.onstop = async () => {
      // Snapshot chunks NOW (before anything else clears them)
      const chunks = mediaState.getAudioChunks().slice();
      mediaState.clearAudioChunks();

      const blob = new Blob(chunks, { type: mime });
      const formData = new FormData();
      formData.append('file', blob, 'voice_' + Date.now() + '.' + ext);

      try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) {
          eventBus.emit('voice:upload_failed', data.error || res.status);
          return;
        }
        eventBus.emit('voice:uploaded', data);
        if (onUpload) onUpload(data);
      } catch (err) {
        eventBus.emit('voice:upload_error', err.message);
      }
    };

    recorder.stop();
    recorder.stream.getTracks().forEach(t => t.stop());
    mediaState.clearMediaRecorder();
    // NOTE: clearAudioChunks() moved into onstop above — do NOT call it here

    eventBus.emit('voice:recording_stopped');
  },

  /**
   * Cancel voice recording
   */
  cancelRecording() {
    const recorder = mediaState.getMediaRecorder();
    if (!recorder) return;

    clearInterval(this.recordInterval);
    mediaState.callStopWave();
    recorder.stream.getTracks().forEach(t => t.stop());
    mediaState.clearMediaRecorder();
    mediaState.clearAudioChunks();

    eventBus.emit('voice:recording_cancelled');
  },

  /**
   * Get recording duration
   * @returns {number} Duration in seconds
   */
  getDuration() {
    return this.recordSeconds;
  },

  /**
   * Format duration
   * @param {number} seconds - Seconds
   * @returns {string} Formatted duration (mm:ss)
   */
  formatDuration(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  },

  /**
   * Toggle voice recording
   * @param {Function} onWaveformUpdate - Waveform update callback
   * @param {Function} onUpload - Upload callback
   * @param {Function} onError - Error callback
   */
  async toggle(onWaveformUpdate, onUpload, onError) {
    console.log('[VoiceMessages] toggle called');
    const recorder = mediaState.getMediaRecorder();
    console.log('[VoiceMessages] Current recorder state:', recorder ? recorder.state : 'none');
    if (recorder && recorder.state === 'recording') {
      console.log('[VoiceMessages] Stopping recording');
      this.stopRecording(onUpload);
    } else {
      console.log('[VoiceMessages] Starting recording');
      this.startRecording(onWaveformUpdate, onError);
    }
  },

  /**
   * Start waveform visualization
   * @private
   * @param {MediaStream} stream - Audio stream
   * @param {Function} onUpdate - Update callback
   */
  _startWaveform(stream, onUpdate) {
    const canvas = document.getElementById('voice-waveform');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.6;
    const source = audioCtx.createMediaStreamSource(stream);
    source.connect(analyser);

    const bufLen = analyser.frequencyBinCount;
    const dataArr = new Uint8Array(bufLen);

    const BAR_W = 2;
    const BAR_GAP = 1;
    const STEP = BAR_W + BAR_GAP;
    const W = canvas.width;
    const H = canvas.height;
    const midY = H / 2;
    const NUM_BARS = Math.floor(W / STEP);

    const noise = Array.from({ length: NUM_BARS }, () => 0.15 + Math.random() * 0.25);
    const smoothed = new Float32Array(NUM_BARS).fill(0);

    let waveRaf;
    const drawWave = () => {
      waveRaf = requestAnimationFrame(drawWave);
      analyser.getByteFrequencyData(dataArr);

      let sum = 0;
      for (let i = 0; i < bufLen; i++) sum += dataArr[i];
      const loudness = sum / (bufLen * 255);

      ctx.clearRect(0, 0, W, H);

      for (let i = 0; i < NUM_BARS; i++) {
        const binIdx = Math.floor((i / (NUM_BARS - 1)) * bufLen);
        const binVal = dataArr[binIdx] / 255;

        const bell = Math.sin((i / (NUM_BARS - 1)) * Math.PI);
        const target = loudness < 0.01
          ? noise[i] * 0.18
          : (binVal * 0.5 + loudness * 0.5) * bell * 0.92 + noise[i] * loudness * 0.3;

        smoothed[i] += (target - smoothed[i]) * 0.25;

        const halfH = Math.max(1.5, smoothed[i] * (midY - 1));
        const x = i * STEP;

        ctx.fillStyle = 'rgba(180, 180, 185, 0.85)';
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, midY - halfH, BAR_W, halfH * 2, 1);
        } else {
          ctx.rect(x, midY - halfH, BAR_W, halfH * 2);
        }
        ctx.fill();
      }

      if (onUpdate) onUpdate(loudness);
    };
    drawWave();

    mediaState.setStopWave(() => {
      cancelAnimationFrame(waveRaf);
      audioCtx.close();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    });
  }
};
