// ─── LANCHAT.controlPlane ────────────────────────────────────────────────────
// The orchestrator. The ONLY module allowed to:
//   - restart ICE
//   - end calls
//   - change callPhase via lifecycle.transition()
//
// Receives events from healthEngine and statsEngine.
// Delegates execution to iceManager, mediaValidator, statsEngine.
// Never touches DOM directly — delegates to LANCHAT.ui.
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.controlPlane = (function () {
    var _restartTimer = null;

    return {
        // ── Called when health grade hits 'dead' ──────────────────────────────
        onHealthDead: function () {
            var pc = window.state && window.state.peerConnection;
            if (!pc) return;

            // Fix 8: validate ICE servers before attempting restart
            var iceServers = window.ICE_CONFIG && window.ICE_CONFIG.iceServers || [];
            if (!iceServers || iceServers.length === 0) {
                console.error('[ICE] No ICE servers available — cannot restart');
                LANCHAT.state.logSignal('ice_no_servers', {});
                if (typeof endCall === 'function') endCall('no_ice_servers');
                return;
            }
            var hasTURN = iceServers.some(function (s) {
                var urls = s.urls;
                if (!urls) return false;
                if (typeof urls === 'string') return urls.startsWith('turn:');
                return urls.some(function (u) { return u.startsWith('turn:'); });
            });
            // Expose TURN availability on state for other modules to read
            if (window.state) window.state.hasTURN = hasTURN;
            if (!hasTURN) {
                console.warn('[ICE] No TURN server configured — relay path unavailable');
                LANCHAT.state.logSignal('ice_no_turn', {});
            }

            // If no TURN is configured and we're not already on a relay path,
            // an ICE restart won't help — end cleanly instead of looping.
            var connType = (window.state && window.state.connectionType) || 'unknown';
            var onRelay = connType === 'TURN';

            if (!onRelay && !hasTURN) {
                console.warn('[ControlPlane] Health=dead, no TURN available — ending call (restart would loop)');
                LANCHAT.ui.updateConnectionBadge({ type: connType, quality: 'dead' });
                if (typeof endCall === 'function') endCall('no_turn');
                return;
            }

            LANCHAT.lifecycle.transition('reconnecting');
            LANCHAT.ui.onReconnecting();
            // Mood: reconnecting — fast pulse, orange
            if (window.LANCHAT && LANCHAT.mood) LANCHAT.mood.set('reconnecting');
            console.warn('[ControlPlane] Health=dead — initiating ICE restart');
            LANCHAT.state.logSignal('ice_restart_start', { connType: connType, hasTURN: hasTURN });
            // Dispatch on event bus
            LANCHAT.events.dispatchEvent(new CustomEvent('call:state', {
                detail: { state: 'reconnecting' }
            }));

            // Delegate role-aware restart to iceManager
            LANCHAT.ice.restart(pc);

            // Timeout: if still failed after 8s, end the call
            if (_restartTimer) clearTimeout(_restartTimer);
            _restartTimer = setTimeout(function () {
                _restartTimer = null;
                LANCHAT.health.clearRestartPending();
                var connState = pc && pc.connectionState;
                if (connState === 'failed' || connState === 'disconnected') {
                    console.error('[ControlPlane] ICE restart failed after 8s — ending call');
                    LANCHAT.state.logSignal('ice_restart_timeout', { connState: connState });
                    // Mood: failed — terminal state
                    if (window.LANCHAT && LANCHAT.mood) LANCHAT.mood.set('failed');
                    if (typeof endCall === 'function') endCall('ice_failed');
                } else {
                    console.log('[ControlPlane] ICE restart succeeded');
                    LANCHAT.state.logSignal('ice_restart_success', {});
                    LANCHAT.lifecycle.transition('ice_establishing');
                }
            }, 8000);
        },

        // ── Called when transport reconnects after ICE restart ────────────────
        onReconnected: function () {
            if (_restartTimer) { clearTimeout(_restartTimer); _restartTimer = null; }
            LANCHAT.health.clearRestartPending();
            LANCHAT.lifecycle.transition('ice_establishing');
            console.log('[ControlPlane] Reconnected — waiting for media confirmation');
        },

        // ── Called by statsEngine when media is confirmed ─────────────────────
        onMediaConfirmed: function () {
            LANCHAT.lifecycle.transition('connected');
            // UI update is handled by mediaValidator → LANCHAT.ui.onMediaReady()
        },

        // ── Teardown ──────────────────────────────────────────────────────────
        teardown: function () {
            if (_restartTimer) { clearTimeout(_restartTimer); _restartTimer = null; }
            LANCHAT.health.clearRestartPending();
            LANCHAT.health.reset();
            LANCHAT.media.reset();
            LANCHAT.stats.stop();
            LANCHAT.ice.drain();
            LANCHAT.signal.drain();
            LANCHAT.state.reset();
            LANCHAT.lifecycle.forceIdle();
            console.log('[ControlPlane] Teardown complete');
        },

        // ── Start monitoring (called after transport connects) ────────────────
        startMonitoring: function () {
            LANCHAT.stats.start();
        },

        stopMonitoring: function () {
            LANCHAT.stats.stop();
        },

        // ── Start a call (audio or video) ─────────────────────────────────────
        startCall: function (type) {
            console.log('[ControlPlane] Starting call:', type);

            var currentPhase = 'idle';
            if (LANCHAT.state && typeof LANCHAT.state.getCallPhase === 'function') {
                currentPhase = LANCHAT.state.getCallPhase();
            }
            if (currentPhase !== 'idle') {
                console.warn('[ControlPlane] Already in a call, phase:', currentPhase);
                return;
            }

            var target = window.state && window.state.currentChat;
            if (!target || target === 'global') {
                console.error('[ControlPlane] No valid chat target selected');
                return;
            }

            if (window.LANCHAT && LANCHAT.callSession && typeof LANCHAT.callSession.beginOutgoingCall === 'function') {
                LANCHAT.callSession.beginOutgoingCall(type);
            } else {
                console.error('[ControlPlane] callSession not available');
            }
        },
    };
}());

// Export for ES6 module imports
export const controlPlane = LANCHAT.controlPlane;
