// ─── LANCHAT.health ───────────────────────────────────────────────────────────
// Turns raw stats into decisions. Reads stats, outputs actions.
// NEVER directly modifies WebRTC. NEVER touches DOM.
// Only requests actions via LANCHAT.controlPlane.
//
// Output grades: 'good' | 'degrading' | 'unstable' | 'dead'
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.health = (function () {
    var _history = [];   // rolling window of grade snapshots
    var _badCount = 0;    // consecutive bad samples (hysteresis)
    var _restartPending = false;

    var THRESHOLDS = {
        LOSS_DEAD: 0.40,
        LOSS_UNSTABLE: 0.20,
        LOSS_WARN: 0.10,
        JITTER_DEAD: 250,
        JITTER_UNSTABLE: 120,
        JITTER_WARN: 80,
        RTT_UNSTABLE: 500,
        BAD_SAMPLES_RESTART: 3,
        HISTORY_SIZE: 5,
    };

    function _classify(snapshot) {
        // Hard transport failure — no hysteresis needed
        if (snapshot.transportPhase === 'dead') return 'dead';

        // Desync: SDP stable but transport dead = "connected but no audio" class
        if (snapshot.signalingPhase === 'stable' && snapshot.transportPhase === 'dead') return 'dead';

        if (snapshot.transportPhase === 'unstable') return 'unstable';

        // Media validator already determined track is dead
        if (snapshot.mediaGrade === 'failed') {
            _badCount++;
            return _badCount >= THRESHOLDS.BAD_SAMPLES_RESTART ? 'dead' : 'unstable';
        }

        // Fix 3: one-way audio = unstable immediately (we're sending, receiving nothing)
        if (snapshot.oneWayAudio) {
            _badCount++;
            console.warn('[Health] One-way audio — marking unstable');
            return _badCount >= THRESHOLDS.BAD_SAMPLES_RESTART ? 'dead' : 'unstable';
        }

        // Threshold breaches with hysteresis
        var isDead = snapshot.loss > THRESHOLDS.LOSS_DEAD ||
            snapshot.jitter > THRESHOLDS.JITTER_DEAD;
        var isUnstable = snapshot.loss > THRESHOLDS.LOSS_UNSTABLE ||
            snapshot.jitter > THRESHOLDS.JITTER_UNSTABLE ||
            snapshot.rtt > THRESHOLDS.RTT_UNSTABLE;

        if (isDead) {
            _badCount++;
            return _badCount >= THRESHOLDS.BAD_SAMPLES_RESTART ? 'dead' : 'unstable';
        }
        if (isUnstable) {
            _badCount++;
            return 'unstable';
        }

        // Trend: worsening over last two samples (early warning)
        if (_history.length >= 2) {
            var prev = _history[_history.length - 2];
            if ((snapshot.loss - prev.loss) > 0.08 ||
                (snapshot.jitter - prev.jitter) > 40) {
                return 'degrading';
            }
        }

        _badCount = 0;
        return 'good';
    }

    return {
        reset: function () {
            _history = [];
            _badCount = 0;
            _restartPending = false;
        },

        // Called by statsEngine every 2s
        evaluate: function (snapshot) {
            _history.push(snapshot);
            if (_history.length > THRESHOLDS.HISTORY_SIZE) _history.shift();

            var grade = _classify(snapshot);

            if (grade === 'degrading') {
                LANCHAT.ui.showCallWarning('Connection degrading…');

            } else if (grade === 'unstable') {
                LANCHAT.state.setTransportPhase('unstable');
                LANCHAT.ui.showCallWarning('Unstable — may reconnect');
                var ct = (window.state && window.state.connectionType) || 'unknown';
                LANCHAT.ui.updateConnectionBadge({ type: ct, quality: 'unstable' });

            } else if (grade === 'dead' && !_restartPending) {
                _restartPending = true;
                LANCHAT.state.setTransportPhase('dead');
                console.warn('[Health] Grade=dead — requesting ICE restart');
                LANCHAT.state.logSignal('health_dead', { loss: snapshot.loss, jitter: snapshot.jitter });
                // Delegate to controlPlane — health never restarts ICE directly
                LANCHAT.controlPlane.onHealthDead();

            } else if (grade === 'good') {
                _badCount = 0;
                _restartPending = false;
                if (LANCHAT.state.getTransportPhase() !== 'connected') {
                    LANCHAT.state.setTransportPhase('connected');
                    if (LANCHAT.state.isMediaReady()) {
                        var ct = (window.state && window.state.connectionType) || 'unknown';
                        LANCHAT.ui.setCallStatus('Audio flowing (' + (ct || 'LAN') + ')');
                        LANCHAT.ui.updateConnectionBadge({ type: ct, quality: 'good' });
                    }
                }
            }
        },

        // Called by controlPlane after ICE restart completes (success or failure)
        clearRestartPending: function () {
            _restartPending = false;
        },
    };
}());

// Export for ES6 module imports
export const healthEngine = LANCHAT.health;
