/**
 * call/callSession.js
 *
 * WebRTC call orchestration — bridges eventBus socket events to the
 * legacy LANCHAT call infrastructure (signal, ice, lifecycle, ui).
 */

import { eventBus } from '../core/eventBus.js';
import { chatState } from '../core/state/chatState.js';
import { config } from '../core/config.js';

export const callSession = {
  _initialized: false,
  _pendingOffer: null,
  _incomingFrom: null,
  _incomingType: 'voice',
  _localStream: null,

  init() {
    if (this._initialized) return;

    eventBus.on('socket:incoming_call', (data) => this._onIncomingCall(data));
    eventBus.on('socket:call_started', () => this._onCallStarted());
    eventBus.on('socket:call_ended', () => this._endCall('remote_ended'));
    eventBus.on('socket:webrtc_signal', (data) => this._onSignal(data));
    eventBus.on('socket:call_signal', (data) => this._onCallSignal(data));

    const acceptBtn = document.getElementById('accept-btn');
    const rejectBtn = document.getElementById('reject-btn');
    const endBtn = document.getElementById('end-call-btn');

    if (acceptBtn) {
      acceptBtn.addEventListener('click', () => this.acceptIncoming());
    }
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => this.rejectIncoming());
    }
    if (endBtn) {
      endBtn.addEventListener('click', () => this._endCall('user_ended'));
    }

    this._initialized = true;
    console.log('[LAN Chat V2] callSession initialized');
  },

  async beginOutgoingCall(type) {
    const L = window.LANCHAT;
    if (!L) return;

    const target = chatState.currentChat;
    if (!target || target === 'global') {
      alert('Select a user to call.');
      return;
    }

    if (L.lifecycle?.inQuarantine?.()) {
      console.warn('[CallSession] In quarantine window — ignoring start');
      return;
    }

    const phase = L.state?.getCallPhase?.() || 'idle';
    if (phase !== 'idle') {
      console.warn('[CallSession] Already in call phase:', phase);
      return;
    }

    L.state.setCallTarget(target);
    L.state.setCallType(type);
    L.state.setCallRole('offerer');
    L.state.setCallId(crypto.randomUUID());
    L.state.setCallStartedAt(Date.now());
    L.lifecycle.transition('connecting');

    const user = chatState.users.find(u => u.display === target);
    L.ui.setCallerInfo(target, user?.color);
    L.ui.setVideoMode(type === 'video');
    L.ui.showControls();
    L.ui.showOverlay();
    L.ui.setCallStatus('Calling…');
    if (L.mood) L.mood.set('connecting');

    const socket = chatState.getSocket();
    if (socket) {
      const eventName = type === 'video' ? 'video-call-user' : 'call-user';
      socket.emit(eventName, { to: target });
    }

    try {
      await this._ensureIceConfig();
      await this._acquireMedia(type);
      const pc = await this._createPeerConnection(target, type);
      L.state.setPeerConnection(pc);

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      L.state.setSignalingPhase('have_offer');

      L.signal.emit({
        to: target,
        type: 'offer',
        sdp: offer,
        callType: type,
        session_id: L.state.getCallId(),
      });

      L.lifecycle.transition('sdp_exchanged');
      L.lifecycle.transition('ice_establishing');
      L.controlPlane.startMonitoring();
    } catch (err) {
      console.error('[CallSession] Outgoing call failed:', err);
      alert(err.message || 'Could not start call');
      this._endCall('setup_failed');
    }
  },

  async acceptIncoming() {
    const L = window.LANCHAT;
    if (!L || !this._incomingFrom) return;

    const target = this._incomingFrom;
    const type = this._incomingType;

    L.state.setCallTarget(target);
    L.state.setCallType(type);
    L.state.setCallRole('answerer');
    L.state.setCallId(crypto.randomUUID());
    L.state.setCallStartedAt(Date.now());
    L.lifecycle.transition('connecting');

    const user = chatState.users.find(u => u.display === target);
    L.ui.setCallerInfo(target, user?.color);
    L.ui.setVideoMode(type === 'video');
    L.ui.showControls();
    L.ui.setCallStatus('Connecting…');

    const socket = chatState.getSocket();
    if (socket) {
      socket.emit('call-accepted', { to: target });
    }

    try {
      await this._ensureIceConfig();
      await this._acquireMedia(type);

      if (this._pendingOffer) {
        await this._handleOffer(this._pendingOffer, target, type);
        this._pendingOffer = null;
      }
    } catch (err) {
      console.error('[CallSession] Accept failed:', err);
      this._endCall('accept_failed');
    }
  },

  rejectIncoming() {
    const L = window.LANCHAT;
    const target = this._incomingFrom;
    if (target && chatState.getSocket()) {
      chatState.getSocket().emit('call-rejected', { to: target });
      L?.signal?.emit?.({ to: target, type: 'reject', session_id: L.state.getCallId() });
    }
    this._incomingFrom = null;
    this._pendingOffer = null;
    L?.ui?.hideOverlay?.();
    L?.lifecycle?.forceIdle?.();
    L?.state?.reset?.();
  },

  _onIncomingCall(data) {
    const L = window.LANCHAT;
    if (!L) return;

    if (L.lifecycle?.inQuarantine?.()) return;

    const phase = L.state?.getCallPhase?.() || 'idle';
    if (phase !== 'idle') {
      this.rejectIncoming();
      return;
    }

    const from = data?.from;
    if (!from) {
      console.warn('[CallSession] incoming_call missing "from" field — rejecting to avoid targeting global');
      return;
    }
    this._incomingFrom = from;
    this._incomingType = data?.callType || 'voice';

    const user = chatState.users.find(u => u.display === from);
    L.ui.setCallerInfo(from, user?.color);
    L.ui.setVideoMode(this._incomingType === 'video');
    L.ui.showIncomingActions();
    L.ui.showOverlay();
    L.ui.setCallStatus('Incoming call…');
    if (L.mood) L.mood.set('connecting');
  },

  _onCallStarted() {
    const L = window.LANCHAT;
    L?.ui?.showControls?.();
    L?.ui?.setCallStatus?.('Connected');
    L?.lifecycle?.transition?.('connected');
  },

  async _onSignal(data) {
    if (!data?.type) return;

    const L = window.LANCHAT;
    const from = data.from;
    const type = data.type;

    if (type === 'session_ack') {
      if (data.session_id) L?.state?.setCallId?.(data.session_id);
      return;
    }

    if (type === 'error') {
      console.error('[CallSession] Signal error:', data.error);
      L?.ui?.showCallWarning?.(data.error || 'Call error');
      return;
    }

    if (type === 'offer') {
      const callType = data.callType || 'voice';
      this._incomingType = callType;
      if (!this._incomingFrom) this._incomingFrom = from;

      const phase = L?.state?.getCallPhase?.() || 'idle';
      if (phase === 'idle') {
        this._pendingOffer = data;
        const user = chatState.users.find(u => u.display === from);
        L?.ui?.setCallerInfo?.(from, user?.color);
        L?.ui?.setVideoMode?.(callType === 'video');
        L?.ui?.showIncomingActions?.();
        L?.ui?.showOverlay?.();
        L?.ui?.setCallStatus?.('Incoming call…');
        if (L?.mood) L.mood.set('connecting');
        return;
      }

      try {
        await this._handleOffer(data, from, callType);
      } catch (err) {
        console.error('[CallSession] Error handling offer:', err);
        L?.ui?.showCallWarning?.('Failed to handle call offer');
        this._endCall('offer_handling_failed');
      }
      return;
    }

    if (type === 'answer') {
      try {
        await this._handleAnswer(data);
      } catch (err) {
        console.error('[CallSession] Error handling answer:', err);
        L?.ui?.showCallWarning?.('Failed to handle call answer');
        this._endCall('answer_handling_failed');
      }
      return;
    }

    if (type === 'candidate' || type === 'ice') {
      try {
        await this._handleCandidate(data);
      } catch (err) {
        console.error('[CallSession] Error handling candidate:', err);
        // Non-fatal error - just log and continue
      }
      return;
    }

    if (type === 'end' || type === 'reject') {
      this._endCall(type);
    }
  },

  _onCallSignal(data) {
    this._onSignal(data);
  },

  async _handleOffer(data, from, callType) {
    const L = window.LANCHAT;
    let pc = L.state.getPeerConnection();

    try {
      if (!pc) {
        L.state.setCallTarget(from);
        L.state.setCallType(callType);
        if (!L.state.getCallRole()) L.state.setCallRole('answerer');
        await this._acquireMedia(callType);
        pc = await this._createPeerConnection(from, callType);
        L.state.setPeerConnection(pc);
      }

      await pc.setRemoteDescription(data.sdp);
      L.state.setSignalingPhase('have_offer');
      L.ice.flushInbound(pc);

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      L.state.setSignalingPhase('have_answer');

      L.signal.emit({
        to: from,
        type: 'answer',
        sdp: answer,
        session_id: data.session_id || L.state.getCallId(),
      });

      L.lifecycle.transition('sdp_exchanged');
      L.lifecycle.transition('ice_establishing');
      L.controlPlane.startMonitoring();
      L.ui.showControls();
    } catch (err) {
      console.error('[CallSession] _handleOffer error:', err);
      throw err;
    }
  },

  async _handleAnswer(data) {
    const L = window.LANCHAT;
    const pc = L.state.getPeerConnection();
    if (!pc) {
      console.warn('[CallSession] _handleAnswer: no peer connection');
      return;
    }

    try {
      await pc.setRemoteDescription(data.sdp);
      L.state.setSignalingPhase('stable');
      L.ice.flushInbound(pc);
      L.lifecycle.transition('sdp_exchanged');
      L.lifecycle.transition('ice_establishing');
      L.ui.setCallStatus('Connected');
    } catch (err) {
      console.error('[CallSession] _handleAnswer error:', err);
      throw err;
    }
  },

  async _handleCandidate(data) {
    const L = window.LANCHAT;
    const pc = L.state.getPeerConnection();
    if (!pc) {
      console.warn('[CallSession] _handleCandidate: no peer connection');
      return;
    }

    const candidate = data.candidate;
    if (!candidate) {
      console.warn('[CallSession] _handleCandidate: no candidate data');
      return;
    }

    try {
      if (pc.remoteDescription) {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
      } else {
        L.ice.bufferInbound(candidate);
      }
    } catch (err) {
      console.warn('[CallSession] addIceCandidate error (may be normal):', err.message);
      // Non-fatal - ICE candidate failures don't break the call
    }
  },

  async _createPeerConnection(target, type) {
    const L = window.LANCHAT;
    const iceConfig = window.ICE_CONFIG || { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

    const pc = new RTCPeerConnection(iceConfig);
    window.state.peerConnection = pc;

    if (this._localStream) {
      this._localStream.getTracks().forEach(track => pc.addTrack(track, this._localStream));
    }

    pc.onicecandidate = (e) => {
      if (!e.candidate) return;
      L.signal.emit({
        to: target,
        type: 'candidate',
        candidate: e.candidate.toJSON(),
        session_id: L.state.getCallId(),
      });
    };

    pc.ontrack = (e) => {
      const remoteAudio = document.getElementById('remote-audio');
      const remoteVideo = document.getElementById('remote-video');
      if (e.track.kind === 'audio' && remoteAudio) {
        remoteAudio.srcObject = e.streams[0];
      }
      if (e.track.kind === 'video' && remoteVideo) {
        remoteVideo.srcObject = e.streams[0];
        const pip = document.getElementById('call-video-pip');
        if (pip) pip.style.display = 'block';
      }
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      if (state === 'connected') {
        L.lifecycle.transition('connected');
        L.ui.setCallStatus('Connected');
        if (L.media.checkReceivers(pc)) {
          L.media.validate({ pc, audioBytes: 1, trackActive: true });
        }
      } else if (state === 'failed' || state === 'disconnected') {
        L.ui.onReconnecting();
      }
    };

    if (type === 'video' && this._localStream) {
      const localVideo = document.getElementById('local-video');
      if (localVideo) {
        localVideo.srcObject = this._localStream;
        localVideo.muted = true;
      }
    }

    return pc;
  },

  async _acquireMedia(type) {
    if (this._localStream) {
      this._localStream.getTracks().forEach(t => t.stop());
      this._localStream = null;
    }

    const constraints = type === 'video'
      ? { audio: true, video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } }
      : { audio: true, video: false };

    this._localStream = await navigator.mediaDevices.getUserMedia(constraints);
    window.state.localStream = this._localStream;
    window.LANCHAT?.state?.setMediaState?.('acquiring');
  },

  async _ensureIceConfig() {
    if (window.ICE_CONFIG) return window.ICE_CONFIG;
    const socket = chatState.getSocket();
    const sid = socket?.id || '';
    window.ICE_CONFIG = await config.getIceConfig(sid);
    return window.ICE_CONFIG;
  },

  _endCall(reason) {
    const L = window.LANCHAT;
    const target = L?.state?.getCallTarget?.() || this._incomingFrom;

    if (target && chatState.getSocket()) {
      chatState.getSocket().emit('end-call', { to: target });
      if (L?.state?.getCallId?.()) {
        L.signal.emit({ to: target, type: 'end', session_id: L.state.getCallId() });
      }
    }

    if (this._localStream) {
      this._localStream.getTracks().forEach(t => t.stop());
      this._localStream = null;
      window.state.localStream = null;
    }

    const remoteAudio = document.getElementById('remote-audio');
    const remoteVideo = document.getElementById('remote-video');
    const localVideo = document.getElementById('local-video');
    if (remoteAudio) remoteAudio.srcObject = null;
    if (remoteVideo) remoteVideo.srcObject = null;
    if (localVideo) localVideo.srcObject = null;

    this._incomingFrom = null;
    this._pendingOffer = null;

    L?.stats?.stop?.();
    L?.ice?.drain?.();
    L?.signal?.drain?.();
    L?.lifecycle?.endCall?.(reason);
  },
};
