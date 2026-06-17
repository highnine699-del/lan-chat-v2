// ─── LANCHAT.signal ───────────────────────────────────────────────────────────
// Signal transport layer. ALL webrtc_signal emits go through here.
// Enforces routing rules:
//   offer/answer → direct emit
//   ice          → queued (20ms drain, max 2 per tick)
//   end/reject   → bypass queue, direct emit
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.signal = (function () {
    var _queue = [];
    var _drainTimer = null;
    var _DRAIN_MS = 20;
    var _MAX_PER_TICK = 2;
    var _WARN_PENDING = 8;

    function _rawEmit(payload) {
        var sock = window.state && window.state.socket;
        if (!sock) { console.warn('[Signal] No socket — dropping', payload.type); return; }
        LANCHAT.state.incPending();
        // Fix 4: log every outbound signal to the timeline
        LANCHAT.state.logSignal('signal_out', { type: payload.type, to: payload.to });
        sock.emit('webrtc_signal', payload);
        setTimeout(function () {
            LANCHAT.state.decPending();
            LANCHAT.state.ackSignal();
        }, 500);
        if (LANCHAT.state.getPending() > _WARN_PENDING) {
            console.warn('[Signal] Backpressure: pending =', LANCHAT.state.getPending());
        }
    }

    function _drainQueue() {
        _drainTimer = null;
        var sent = 0;
        while (_queue.length && sent < _MAX_PER_TICK) {
            _rawEmit(_queue.shift());
            sent++;
        }
        if (_queue.length) {
            _drainTimer = setTimeout(_drainQueue, _DRAIN_MS);
        }
    }

    return {
        // Emit a signal. Routing rules applied here.
        emit: function (payload) {
            var type = payload.type;

            // end/reject bypass everything — must arrive immediately
            if (type === 'end' || type === 'reject') {
                _rawEmit(payload);
                return;
            }

            // offer/answer are direct — ordering matters for SDP exchange
            if (type === 'offer' || type === 'answer') {
                _rawEmit(payload);
                return;
            }

            // ice candidates are queued and drained in batches
            _queue.push(payload);
            if (!_drainTimer) {
                _drainTimer = setTimeout(_drainQueue, _DRAIN_MS);
            }
        },

        // Drain and discard queue (called on endCall)
        drain: function () {
            if (_drainTimer) { clearTimeout(_drainTimer); _drainTimer = null; }
            var dropped = _queue.length;
            _queue = [];
            if (dropped) console.log('[Signal] Drained', dropped, 'queued signals on teardown');
        },
    };
}());

// Export for ES6 module imports
export const signalEmit = LANCHAT.signal;
