// ─── LANCHAT.lifecycle ────────────────────────────────────────────────────────
// FSM: enforces valid callPhase transitions.
// Nothing outside this module may change callPhase directly.
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.lifecycle = (function () {
    // Valid transitions: from → [allowed to states]
    var TRANSITIONS = {
        'idle': ['connecting'],
        'connecting': ['sdp_exchanged', 'failed', 'closing'],
        'sdp_exchanged': ['ice_establishing', 'failed', 'closing'],
        'ice_establishing': ['media_ready', 'reconnecting', 'failed', 'closing'],
        'media_ready': ['connected', 'reconnecting', 'failed', 'closing'],
        'connected': ['reconnecting', 'closing'],
        'reconnecting': ['ice_establishing', 'media_ready', 'failed', 'closing'],
        'failed': ['connecting', 'closing'],
        'closing': ['idle'],
    };

    function canTransition(from, to) {
        var allowed = TRANSITIONS[from];
        return allowed ? allowed.indexOf(to) !== -1 : false;
    }

    return {
        // Attempt a phase transition. Returns true on success, false if invalid.
        // Logs a warning on invalid transitions but never throws — the call must
        // not crash because of a state machine violation.
        transition: function (to) {
            var from = 'idle';
            if (LANCHAT.state && typeof LANCHAT.state.getCallPhase === 'function') {
                from = LANCHAT.state.getCallPhase();
            }
            if (from === to) return true;   // no-op, already there
            if (!canTransition(from, to)) {
                console.warn('[FSM] Invalid transition:', from, '→', to, '— ignored');
                return false;
            }
            if (LANCHAT.state && typeof LANCHAT.state.setCallPhase === 'function') {
                LANCHAT.state.setCallPhase(to);
            }
            console.log('[FSM]', from, '→', to);
            return true;
        },

        // Force a phase without validation — only for endCall teardown
        forceIdle: function () {
            if (LANCHAT.state && typeof LANCHAT.state.setCallPhase === 'function') {
                LANCHAT.state.setCallPhase('idle');
            }
        },

        canTransition: canTransition,

        // Quarantine check: are we within the post-end silence window?
        inQuarantine: function () {
            var WINDOW_MS = 4000;
            var elapsed = Date.now() - LANCHAT.state.getCallEndedAt();
            return elapsed < WINDOW_MS;
        },

        // End call - V2 implementation
        endCall: function (reason) {
            console.log('[Lifecycle] ENDING CALL - reason:', reason);

            // Clean up peer connection before reset clears the reference
            var pc = LANCHAT.state.getPeerConnection();
            if (pc) {
                pc.close();
            }

            // Force to idle state
            this.forceIdle();

            // Reset call state
            LANCHAT.state.reset();

            // Drain ICE buffers
            if (LANCHAT.ice) {
                LANCHAT.ice.drain();
            }

            // Hide call UI
            if (LANCHAT.ui) {
                LANCHAT.ui.hideOverlay();
            }

            // Reset mood
            if (LANCHAT.mood) {
                LANCHAT.mood.set('idle');
            }

            console.log('[Lifecycle] Call ended successfully');
        },
    };
}());

// Export for ES6 module imports
export const lifecycle = LANCHAT.lifecycle;
