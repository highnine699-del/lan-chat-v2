// ─── LANCHAT.media ────────────────────────────────────────────────────────────
// Validates whether media is actually flowing — the fix for "connected but
// no audio". This is the ONLY place that sets mediaReady = true.
//
// Output grades: 'good' | 'degraded' | 'unstable' | 'failed'
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.media = (function () {
    var _lastBytes = 0;
    var _readyCount = 0;   // consecutive good samples
    var _READY_SAMPLES = 3;   // samples needed to confirm media-ready

    // ── Hard receiver-level check (Fix 1) ─────────────────────────────────────
    // Inspects RTCRtpReceiver objects directly — not stats, not bytes.
    // Returns true only when an audio track is present AND live AND unmuted.
    // This kills "connected but silent" cases before stats even confirm flow.
    function confirmMediaFlow(pc) {
        if (!pc || typeof pc.getReceivers !== 'function') return false;
        var receivers = pc.getReceivers();
        var hasAudio = false;
        var unmuted = false;
        receivers.forEach(function (r) {
            if (r.track && r.track.kind === 'audio') {
                hasAudio = true;
                if (!r.track.muted && r.track.readyState === 'live') {
                    unmuted = true;
                }
            }
        });
        if (!hasAudio) {
            console.warn('[Media] confirmMediaFlow: no audio receiver attached');
        } else if (!unmuted) {
            console.warn('[Media] confirmMediaFlow: audio track present but muted/ended');
        }
        return hasAudio && unmuted;
    }

    return {
        // Reset on call start/end
        reset: function () {
            _lastBytes = 0;
            _readyCount = 0;
            LANCHAT.state.setMediaReady(false);
            LANCHAT.state.setMediaState('idle');
        },

        // Hard receiver check — call this right after transport connects
        // to gate out "connected but no track" before stats polling begins.
        checkReceivers: function (pc) {
            return confirmMediaFlow(pc);
        },

        // Validate a stats snapshot. Returns a grade string.
        // stats = { audioBytes, rtt, jitter, trackActive, pc }
        validate: function (stats) {
            var audioBytes = stats.audioBytes || 0;
            var rtt = stats.rtt || 0;
            var jitter = stats.jitter || 0;
            var trackActive = stats.trackActive !== false;   // default true if not provided
            var pc = stats.pc || (window.state && window.state.peerConnection);

            // Hard failure: track muted by browser
            if (!trackActive) {
                _readyCount = 0;
                if (LANCHAT.state.isMediaReady()) {
                    LANCHAT.state.setMediaReady(false);
                    console.warn('[Media] mediaReady revoked — track muted');
                }
                return 'failed';
            }

            // Hard receiver check: if transport says connected but no live track,
            // fail immediately rather than waiting for stats to time out.
            if (pc && !confirmMediaFlow(pc)) {
                _readyCount = 0;
                if (LANCHAT.state.isMediaReady()) {
                    LANCHAT.state.setMediaReady(false);
                    console.warn('[Media] mediaReady revoked — receiver check failed');
                }
                // Only return failed if we have zero bytes too (track may be
                // briefly muted during negotiation — give stats a chance)
                if (audioBytes === 0) return 'failed';
            }

            var progressing = audioBytes > _lastBytes;
            _lastBytes = audioBytes;

            // No bytes flowing at all (and we've had bytes before = stagnant)
            if (!progressing && audioBytes > 0) {
                _readyCount = 0;
                if (LANCHAT.state.isMediaReady()) {
                    LANCHAT.state.setMediaReady(false);
                    console.warn('[Media] mediaReady revoked — audio stagnant');
                }
                return 'degraded';
            }

            // Bytes flowing — check quality thresholds
            if (progressing) {
                _readyCount++;
                if (_readyCount >= _READY_SAMPLES && !LANCHAT.state.isMediaReady()) {
                    LANCHAT.state.setMediaReady(true);
                    LANCHAT.state.setMediaState('ready');
                    console.log('[Media] mediaReady confirmed after', _readyCount, 'samples');
                    // Tell the UI — only place "✅ Connected" is ever shown
                    LANCHAT.ui.onMediaReady();
                }
            }

            if (rtt > 500 || jitter > 250) return 'unstable';
            if (rtt > 200 || jitter > 80) return 'degraded';
            return 'good';
        },
    };
}());

// Export for ES6 module imports
export const mediaValidator = LANCHAT.media;
