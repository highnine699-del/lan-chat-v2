// ─── LANCHAT.ui (call layer) ──────────────────────────────────────────────────
// ALL call-related DOM mutations go through here.
// No other module may touch call UI elements directly.
// Reads from LANCHAT.state and LANCHAT.webrtc.stats — never from app.js state.
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

// ── Event bus ─────────────────────────────────────────────────────────────────
// Single event channel for all LANCHAT UI events.
// Modules dispatch; UI layer listens. No polling, no desync.
LANCHAT.events = LANCHAT.events || new EventTarget();

LANCHAT.ui = (function () {
    var _warningTimer = null;
    var _badgeThrottleTimer = null;   // throttle badge updates to max 1 per 2.5s
    var _pendingBadgeOpts = null;     // last opts waiting to be applied

    // ── Internal: map connection type + health grade → system mood ────────────
    // Mood drives the global --accent CSS variable via data-mood on <body>.
    // 'idle' resets to default LAN green (no active call).
    function _moodFromState(type, quality) {
        if (quality === 'dead') return 'failed';
        if (quality === 'unstable') return 'unstable';
        if (type === 'TURN') return 'TURN';
        if (type === 'STUN') return 'STUN';
        if (type === 'LAN') return 'LAN';
        return 'connecting'; // establishing / unknown path
    }

    // ── Internal: truth-state status text ─────────────────────────────────────
    // Rhythm variation: rotate between equivalent phrasings so the UI feels
    // alive rather than mechanically perfect. Meaning never changes — only cadence.
    var _statusVariants = {
        connecting: ['Connecting…', 'Linking…'],
        reconnecting: ['Recovering…', 'Stabilizing…'],
        connected: ['Connected', 'Stable'],
    };
    var _statusCounters = { connecting: 0, reconnecting: 0, connected: 0 };

    function _nextVariant(key) {
        var variants = _statusVariants[key];
        var idx = _statusCounters[key] % variants.length;
        _statusCounters[key]++;
        return variants[idx];
    }

    function _statusText(type, quality, extra) {
        if (quality === 'dead') return _nextVariant('reconnecting');
        if (quality === 'unstable') return 'Connection unstable' + (extra ? ' — ' + extra : '');
        if (type === 'TURN') return _nextVariant('connected') + ' (relayed)';
        if (type === 'STUN') return _nextVariant('connected') + ' (STUN)';
        if (type === 'LAN') return _nextVariant('connected') + ' (direct)';
        return _nextVariant('connecting');
    }

    return {
        // ── 🎯 System Mood Layer ──────────────────────────────────────────────
        // Delegates to LANCHAT.mood (moodEngine.js) — the single source of truth.
        // Everything that uses var(--accent) reacts automatically.
        setMood: function (mood) {
            if (window.LANCHAT && LANCHAT.mood) {
                LANCHAT.mood.set(mood);
            } else {
                // Fallback if moodEngine not yet loaded
                document.body.setAttribute('data-mood', mood);
                if (LANCHAT.events) {
                    LANCHAT.events.dispatchEvent(new CustomEvent('ui:mood', { detail: { mood: mood } }));
                }
            }
        },

        // Reset mood to idle when no call is active
        clearMood: function () {
            if (window.LANCHAT && LANCHAT.mood) {
                LANCHAT.mood.reset();
            } else {
                document.body.removeAttribute('data-mood');
            }
        },

        // ── Status text — human language only ────────────────────────────────
        setCallStatus: function (text) {
            var el = document.getElementById('call-status');
            if (!el) return;
            requestAnimationFrame(function () { el.textContent = text; });
        },

        // ── Transient warning (auto-clears after 5s) ──────────────────────────
        showCallWarning: function (text) {
            var el = document.getElementById('call-status');
            if (!el || el.dataset.warning) return;
            el.dataset.warning = '1';
            var prev = el.textContent;
            el.textContent = text;
            el.style.color = '#f97316';
            _warningTimer = setTimeout(function () {
                el.textContent = prev;
                el.style.color = '';
                delete el.dataset.warning;
                _warningTimer = null;
            }, 5000);
        },

        clearWarning: function () {
            if (_warningTimer) { clearTimeout(_warningTimer); _warningTimer = null; }
            var el = document.getElementById('call-status');
            if (el) { el.style.color = ''; delete el.dataset.warning; }
        },

        // ── Called by mediaValidator when audio is confirmed ──────────────────
        // This is the ONLY place a "connected" status is ever shown.
        onMediaReady: function () {
            this.clearWarning();
            var ct = (window.state && window.state.connectionType) || '';
            this.setCallStatus(_nextVariant('connected'));
            this.updateConnectionBadge({ type: ct || 'LAN', quality: 'good' });
            console.log('[UI] Media ready — connection type:', ct || 'unknown');
        },

        // ── Reconnecting state ────────────────────────────────────────────────
        onReconnecting: function () {
            this.setCallStatus(_nextVariant('reconnecting'));
            this.updateConnectionBadge({ type: null, quality: 'unstable' });
            this.setMood('reconnecting');
            LANCHAT.events.dispatchEvent(new CustomEvent('call:state', {
                detail: { state: 'reconnecting' }
            }));
        },

        // ── Real connection status badge ──────────────────────────────────────
        // Throttled to max 1 update per 2.5s — prevents rapid text swapping.
        // All DOM writes are batched in a single rAF frame.
        // Human language only — no ICE jargon shown to users.
        updateConnectionBadge: function (opts) {
            // Store latest opts — always use the most recent when the timer fires
            _pendingBadgeOpts = opts;

            if (_badgeThrottleTimer) return; // already scheduled

            _badgeThrottleTimer = setTimeout(function () {
                _badgeThrottleTimer = null;
                var o = _pendingBadgeOpts;
                _pendingBadgeOpts = null;
                if (!o) return;

                requestAnimationFrame(function () {
                    var type = (o && o.type) || 'unknown';
                    var quality = (o && o.quality) || 'good';

                    var badge = document.getElementById('connection-badge');
                    if (!badge) return;

                    // Human language only — rhythm variants keep it feeling alive
                    var label;
                    if (quality === 'dead') {
                        label = _nextVariant('reconnecting');
                    } else if (quality === 'unstable') {
                        label = _nextVariant('reconnecting');
                    } else if (quality === 'good' || type === 'LAN' || type === 'STUN' || type === 'TURN') {
                        label = _nextVariant('connected');
                    } else {
                        label = _nextVariant('connecting');
                    }

                    badge.textContent = label;
                    badge.dataset.quality = quality;
                    badge.dataset.type = type;

                    // Drive the system mood from connection state
                    var mood = _moodFromState(type, quality);
                    LANCHAT.ui.setMood(mood);

                    // Dispatch on event bus
                    LANCHAT.events.dispatchEvent(new CustomEvent('call:state', {
                        detail: { state: quality === 'good' ? type : quality, type: type, quality: quality }
                    }));
                });
            }, 2500);
        },

        // ── Call overlay helpers ──────────────────────────────────────────────
        showOverlay: function () {
            var el = document.getElementById('call-overlay');
            if (el) {
                el.classList.add('active');
                document.body.classList.add('call-active');
            }
        },

        hideOverlay: function () {
            var el = document.getElementById('call-overlay');
            if (el) {
                el.classList.remove('active');
                document.body.classList.remove('call-active');
                this.clearMood();
            }
        },

        setCallerInfo: function (name, color) {
            var avatar = document.getElementById('call-avatar');
            var nameEl = document.getElementById('call-name');
            if (avatar) {
                avatar.textContent = name ? name[0].toUpperCase() : '?';
                avatar.style.background = color || '#1a3a5c';
            }
            if (nameEl) nameEl.textContent = name || '';
        },

        showControls: function () {
            var actions = document.getElementById('call-action-buttons');
            var controls = document.getElementById('call-control-buttons');
            if (actions) actions.style.display = 'none';
            if (controls) controls.style.display = 'flex';
        },

        showIncomingActions: function () {
            var actions = document.getElementById('call-action-buttons');
            var controls = document.getElementById('call-control-buttons');
            if (actions) actions.style.display = 'flex';
            if (controls) controls.style.display = 'none';
        },

        setVideoMode: function (isVideo) {
            var pip = document.getElementById('call-video-pip');
            var camBtn = document.getElementById('cam-btn');
            if (pip) pip.style.display = isVideo ? 'block' : 'none';
            if (camBtn) camBtn.style.display = isVideo ? 'flex' : 'none';
        },
    };
}());

// ── Event bus listener: call:state → mood ─────────────────────────────────────
// Any module can dispatch 'call:state' and the UI layer will react.
LANCHAT.events.addEventListener('call:state', function (e) {
    var s = e.detail && e.detail.state;
    if (!s) return;
    // Map call states to moods — only the 7 allowed moods
    var moodMap = {
        'LAN': 'LAN',
        'STUN': 'STUN',
        'TURN': 'TURN',
        'connecting': 'connecting',
        'unstable': 'unstable',
        'reconnecting': 'reconnecting',
        'dead': 'failed',
        'failed': 'failed',
    };
    var mood = moodMap[s];
    if (mood) LANCHAT.ui.setMood(mood);
});

// Export for ES6 module imports
export const callUI = LANCHAT.ui;
