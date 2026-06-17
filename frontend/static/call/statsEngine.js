// ─── LANCHAT.stats ────────────────────────────────────────────────────────────
// Polls RTCPeerConnection.getStats() every 2s and feeds results to:
//   - LANCHAT.media.validate()  → mediaReady gate
//   - LANCHAT.health.evaluate() → ICE restart / warning decisions
//
// This module ONLY reads stats and routes them. It never restarts ICE,
// never modifies DOM, never changes callPhase.
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.stats = (function () {
    var _interval = null;
    var _POLL_MS = 2000;
    var _lastInboundBytes = 0;   // Fix 3: one-way audio tracking
    var _lastOutboundBytes = 0;

    // ── Fix 3: One-way audio detection ────────────────────────────────────────
    // Returns { inbound, outbound, oneWay } from the current stats map.
    // oneWay = true means we're sending but receiving nothing — silent remote.
    function _detectOneWayAudio(statsMap) {
        var inbound = 0;
        var outbound = 0;
        statsMap.forEach(function (r) {
            if (r.type === 'inbound-rtp' && r.kind === 'audio') {
                inbound += r.bytesReceived || 0;
            }
            if (r.type === 'outbound-rtp' && r.kind === 'audio') {
                outbound += r.bytesSent || 0;
            }
        });
        return {
            inbound: inbound,
            outbound: outbound,
            oneWay: inbound === 0 && outbound > 0,
        };
    }

    // ── Mood update from connection type ──────────────────────────────────────
    // Called every stats tick. Maps the detected ICE path to a system mood.
    // Does NOT override connecting/reconnecting/failed — those are set by
    // controlPlane and the call lifecycle. Only fires when a path is known.
    function _updateConnectionMood(type) {
        if (!window.LANCHAT || !LANCHAT.mood) return;
        // Don't override terminal or transitional moods set by controlPlane
        var cur = LANCHAT.mood.current;
        if (cur === 'connecting' || cur === 'reconnecting' || cur === 'failed') return;

        switch (type) {
            case 'LAN': LANCHAT.mood.set('LAN'); break;
            case 'STUN': LANCHAT.mood.set('STUN'); break;
            case 'TURN': LANCHAT.mood.set('TURN'); break;
            default:
                // 'unknown' during early ICE — stay in connecting if already there
                if (cur !== 'connecting') LANCHAT.mood.set('unstable');
        }
    }

    async function _poll() {
        var pc = window.state && window.state.peerConnection;
        if (!pc || window.state.callState !== 'connected') return;

        try {
            var reports = await pc.getStats();
            var audioStats = null;
            var candidatePair = null;

            reports.forEach(function (r) {
                if (r.type === 'inbound-rtp' && r.kind === 'audio') audioStats = r;
                if (r.type === 'candidate-pair' && r.state === 'succeeded') candidatePair = r;
            });

            // Build snapshot
            var audioBytes = audioStats ? (audioStats.bytesReceived || 0) : 0;
            var packetsLost = audioStats ? (audioStats.packetsLost || 0) : 0;
            var packetsRcvd = audioStats ? (audioStats.packetsReceived || 1) : 1;
            var jitterMs = audioStats ? Math.round((audioStats.jitter || 0) * 1000) : 0;
            var rttMs = candidatePair
                ? Math.round((candidatePair.currentRoundTripTime || 0) * 1000) : 0;
            var lossRate = packetsLost / (packetsLost + packetsRcvd);

            // Inbound audio track mute state
            var audioTrack = pc.getReceivers
                ? (pc.getReceivers().find(function (r) { return r.track && r.track.kind === 'audio'; }) || {}).track
                : null;
            var trackActive = audioTrack ? !audioTrack.muted : true;

            // ── Fix 2: ICE candidate type logging ─────────────────────────────
            // Log the exact path (host/srflx/relay) on the succeeded pair.
            // This tells you definitively: LAN, STUN, or TURN.
            var connectionType = 'unknown';
            if (candidatePair) {
                var localCand = null;
                var remoteCand = null;
                reports.forEach(function (r) {
                    if (r.id === candidatePair.localCandidateId) localCand = r;
                    if (r.id === candidatePair.remoteCandidateId) remoteCand = r;
                });
                if (localCand) {
                    connectionType = localCand.candidateType === 'relay' ? 'TURN'
                        : localCand.candidateType === 'srflx' ? 'STUN'
                            : localCand.candidateType === 'host' ? 'LAN'
                                : 'unknown';
                    // Log full ICE path so you can see exactly what's being used
                    console.log('[ICE PATH]', {
                        localType: localCand.candidateType,
                        remoteType: remoteCand ? remoteCand.candidateType : 'unknown',
                        protocol: localCand.protocol,
                        rtt: candidatePair.currentRoundTripTime,
                    });
                }
            }

            // Publish to LANCHAT.webrtc.stats for UI reads
            LANCHAT.webrtc = LANCHAT.webrtc || {};
            LANCHAT.webrtc.stats = {
                audioBytes: audioBytes,
                rtt: rttMs,
                jitter: jitterMs,
                loss: lossRate,
                trackActive: trackActive,
                connectionType: connectionType,
                ts: Date.now(),
            };

            if (window.state) window.state.connectionType = connectionType;

            // ── Mood update from stats tick ────────────────────────────────────
            // Drive the system mood from the live connection type every poll cycle.
            // Only fires during an active call — controlPlane owns connecting/failed.
            _updateConnectionMood(connectionType);

            // ── Fix 3: One-way audio detection ────────────────────────────────
            var audioFlow = _detectOneWayAudio(reports);
            if (audioFlow.oneWay) {
                // Inbound bytes haven't moved but we're sending — remote is silent
                console.warn('[Stats] One-way audio detected — sending but receiving nothing', {
                    outbound: audioFlow.outbound,
                    inbound: audioFlow.inbound,
                });
                LANCHAT.state.logSignal('one_way_audio', {
                    outbound: audioFlow.outbound,
                    inbound: audioFlow.inbound,
                });
            }
            _lastInboundBytes = audioFlow.inbound;
            _lastOutboundBytes = audioFlow.outbound;

            // Route to media validator (mediaReady gate)
            // Pass pc so mediaValidator can run the hard receiver check (Fix 1)
            var mediaGrade = LANCHAT.media.validate({
                audioBytes: audioBytes,
                rtt: rttMs,
                jitter: jitterMs,
                trackActive: trackActive,
                pc: pc,
            });

            // If one-way audio, force mediaGrade to unstable so health engine acts
            if (audioFlow.oneWay && mediaGrade === 'good') {
                mediaGrade = 'unstable';
            }

            // Route to health engine (ICE restart / warning decisions)
            LANCHAT.health.evaluate({
                mediaGrade: mediaGrade,
                loss: lossRate,
                jitter: jitterMs,
                rtt: rttMs,
                trackActive: trackActive,
                oneWayAudio: audioFlow.oneWay,
                transportPhase: LANCHAT.state.getTransportPhase(),
                signalingPhase: LANCHAT.state.getSignalingPhase(),
            });

            // Update transport phase from live PC state
            var iceState = pc.iceConnectionState;
            var connState = pc.connectionState;
            if (connState === 'connected' && (iceState === 'connected' || iceState === 'completed')) {
                if (LANCHAT.state.getTransportPhase() !== 'degrading' &&
                    LANCHAT.state.getTransportPhase() !== 'unstable') {
                    LANCHAT.state.setTransportPhase('connected');
                }
            } else if (connState === 'failed' || iceState === 'failed') {
                LANCHAT.state.setTransportPhase('dead');
            } else if (iceState === 'disconnected') {
                LANCHAT.state.setTransportPhase('unstable');
            }

        } catch (err) {
            console.warn('[Stats] getStats error:', err.message);
        }
    }

    return {
        start: function () {
            if (_interval) clearInterval(_interval);
            _lastInboundBytes = 0;
            _lastOutboundBytes = 0;
            _interval = setInterval(_poll, _POLL_MS);
            console.log('[Stats] Monitoring started');
        },

        stop: function () {
            if (_interval) {
                clearInterval(_interval);
                _interval = null;
                console.log('[Stats] Monitoring stopped');
            }
        },
    };
}());

// Export for ES6 module imports
export const statsEngine = LANCHAT.stats;
