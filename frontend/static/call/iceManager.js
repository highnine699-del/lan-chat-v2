// ─── LANCHAT.ice ──────────────────────────────────────────────────────────────
// Owns all ICE candidate buffering and flushing.
// The SDP gate rule: inbound candidates are buffered until remote description
// is set. Outbound candidates are buffered until local description is set.
// Only controlPlane.js may call flush — never call it directly from signal code.
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.ice = (function () {
    var _inbound = [];   // candidates received before remote SDP was set
    var _outbound = [];   // candidates gathered before local SDP was set

    return {
        // ── Inbound (received from peer via signaling) ─────────────────────────
        bufferInbound: function (candidate) {
            _inbound.push(candidate);
            console.log('[ICE] Buffered inbound candidate (total:', _inbound.length + ')');
        },

        flushInbound: function (pc) {
            if (!pc || !_inbound.length) return;
            console.log('[ICE] Flushing', _inbound.length, 'inbound candidates');
            var batch = _inbound.splice(0);
            batch.forEach(function (c) {
                pc.addIceCandidate(new RTCIceCandidate(c)).catch(function (err) {
                    console.warn('[ICE] addIceCandidate error (may be normal):', err.message);
                });
            });
        },

        // ── Outbound (gathered locally, held until SDP is ready) ──────────────
        bufferOutbound: function (candidate, to) {
            _outbound.push({ candidate: candidate, to: to });
            console.log('[ICE] Buffered outbound candidate (total:', _outbound.length + ')');
        },

        flushOutbound: function () {
            if (!_outbound.length) return;
            console.log('[ICE] Flushing', _outbound.length, 'outbound candidates');
            var batch = _outbound.splice(0);
            batch.forEach(function (item) {
                LANCHAT.signal.emit({
                    to: item.to,
                    type: 'ice',
                    candidate: item.candidate,
                });
            });
        },

        // ── Drain both buffers (called on endCall) ─────────────────────────────
        drain: function () {
            var dropped = _inbound.length + _outbound.length;
            _inbound = [];
            _outbound = [];
            if (dropped) console.log('[ICE] Drained', dropped, 'buffered candidates on teardown');
        },

        // ── Role-aware ICE restart ─────────────────────────────────────────────
        // restartIce() only works when called by the OFFERER.
        // The ANSWERER must create a new offer with iceRestart:true.
        // controlPlane.js calls this — never call it from health/stats code.
        restart: async function (pc) {
            var role = LANCHAT.state.getCallRole();
            var target = LANCHAT.state.getCallTarget();
            var callType = LANCHAT.state.getCallType();

            if (!pc || !target) {
                console.warn('[ICE] restart() called with no active connection');
                return;
            }

            if (role === 'offerer') {
                console.log('[ICE] Restart: offerer path — calling restartIce()');
                pc.restartIce();
            } else {
                // Answerer must re-negotiate with iceRestart:true
                console.log('[ICE] Restart: answerer path — creating new offer with iceRestart:true');
                try {
                    var offer = await pc.createOffer({ iceRestart: true });
                    await pc.setLocalDescription(offer);
                    LANCHAT.state.setSignalingPhase('have_offer');
                    LANCHAT.signal.emit({
                        to: target,
                        type: 'offer',
                        sdp: offer,
                        callType: callType,
                        iceRestart: true,
                    });
                    console.log('[ICE] Restart offer sent (answerer role)');
                } catch (err) {
                    console.error('[ICE] Restart offer failed:', err.message);
                }
            }
        },
    };
}());

// Export for ES6 module imports
export const iceManager = LANCHAT.ice;
