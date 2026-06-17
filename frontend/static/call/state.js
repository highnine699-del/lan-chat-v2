// ─── LANCHAT.state ────────────────────────────────────────────────────────────
// Single source of truth for call state.
// All other modules READ from here. Only callSession.js WRITES to here.
// app.js legacy `state` object is kept for chat/UI — this owns call state only.
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.state = (function () {
    // Private backing store
    var _s = {
        // ── Call identity ──────────────────────────────────────────────────────
        callId: null,       // crypto.randomUUID() — nulled on endCall
        callRole: null,       // 'offerer' | 'answerer'
        callTarget: null,       // display string of remote peer
        callType: null,       // 'voice' | 'video'

        // ── FSM phases ─────────────────────────────────────────────────────────
        // callPhase: coarse lifecycle gate used by ICE buffer and signal guards
        //   idle → connecting → sdp_exchanged → ice_establishing →
        //   media_ready → connected → reconnecting → failed → closing
        callPhase: 'idle',
        signalingPhase: 'idle',   // SDP axis: idle|have_offer|have_answer|stable
        transportPhase: 'idle',   // ICE axis: idle|checking|connected|degrading|unstable|dead

        // ── Media ──────────────────────────────────────────────────────────────
        mediaReady: false,      // true only after audio confirmed by statsEngine
        mediaState: 'idle',     // 'idle'|'acquiring'|'ready'|'failed'

        // ── Timing ─────────────────────────────────────────────────────────────
        callStartedAt: null,
        callEndedAt: 0,        // epoch ms — quarantine window reads this

        // ── WebRTC ─────────────────────────────────────────────────────────────
        peerConnection: null,   // RTCPeerConnection — owned here, managed by lifecycle

        // ── Backpressure ───────────────────────────────────────────────────────
        pendingSignals: 0,
        lastSignalAck: 0,

        // ── Fix 4: Signal timeline ─────────────────────────────────────────────
        // Structured event log for post-mortem replay. Never cleared on reset.
        signalTimeline: [],
    };

    // Public API — intentionally minimal
    return {
        // Read the full snapshot (returns a shallow copy — don't mutate)
        get: function () { return Object.assign({}, _s); },

        // Individual getters used by modules
        getCallId: function () { return _s.callId; },
        getCallPhase: function () { return _s.callPhase; },
        getCallRole: function () { return _s.callRole; },
        getCallTarget: function () { return _s.callTarget; },
        getCallType: function () { return _s.callType; },
        getSignalingPhase: function () { return _s.signalingPhase; },
        getTransportPhase: function () { return _s.transportPhase; },
        isMediaReady: function () { return _s.mediaReady; },
        getCallEndedAt: function () { return _s.callEndedAt; },

        // Setters — called only by callSession.js and the modules it delegates to
        setCallId: function (v) { _s.callId = v; },
        setCallRole: function (v) { _s.callRole = v; },
        setCallTarget: function (v) { _s.callTarget = v; },
        setCallType: function (v) { _s.callType = v; },
        setCallPhase: function (v) { _s.callPhase = v; },
        setSignalingPhase: function (v) { _s.signalingPhase = v; },
        setTransportPhase: function (v) { _s.transportPhase = v; },
        setMediaReady: function (v) { _s.mediaReady = v; },
        setMediaState: function (v) { _s.mediaState = v; },
        setCallStartedAt: function (v) { _s.callStartedAt = v; },

        // Peer connection management
        getPeerConnection: function () { return _s.peerConnection; },
        setPeerConnection: function (v) { _s.peerConnection = v; },

        // Signal backpressure
        incPending: function () { _s.pendingSignals++; },
        decPending: function () { _s.pendingSignals = Math.max(0, _s.pendingSignals - 1); },
        ackSignal: function () { _s.lastSignalAck = Date.now(); },
        getPending: function () { return _s.pendingSignals; },

        // ── Fix 4: Signal timeline ────────────────────────────────────────────
        // Structured event log — replay exactly what happened when a call fails.
        // Capped at 50 entries (oldest dropped). Survives endCall for post-mortem.
        logSignal: function (event, data) {
            var entry = Object.assign({ t: Date.now(), event: event }, data || {});
            _s.signalTimeline.push(entry);
            if (_s.signalTimeline.length > 50) _s.signalTimeline.shift();
        },

        getTimeline: function () { return _s.signalTimeline.slice(); },

        // Full reset — called by callSession.endCall()
        reset: function () {
            _s.callId = null;
            _s.callRole = null;
            _s.callTarget = null;
            _s.callType = null;
            _s.callPhase = 'idle';
            _s.signalingPhase = 'idle';
            _s.transportPhase = 'idle';
            _s.mediaReady = false;
            _s.mediaState = 'idle';
            _s.callStartedAt = null;
            _s.callEndedAt = Date.now();   // stamp quarantine window
            _s.pendingSignals = 0;
            _s.peerConnection = null;      // cleared on reset so lifecycle.endCall() can check
            // Timeline is intentionally NOT cleared on reset — kept for post-mortem
        },
    };
}());

// Export for ES6 module imports
export const callState = LANCHAT.state;
