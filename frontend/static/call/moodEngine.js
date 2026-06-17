// ─── LANCHAT.mood — Central Mood Engine ──────────────────────────────────────
// Single source of truth for the UI "emotion system".
//
// Allowed moods (non-negotiable):
//   idle        — socket connected, no call. Invisible background mode.
//   connecting  — call initiated. Calm anticipation.
//   LAN         — call on local network. Stable, invisible.
//   STUN        — call via STUN. Stable, invisible.
//   TURN        — call via relay. Warm, slightly notable.
//   unstable    — degraded connection. Soft tension.
//   reconnecting — ICE restart in progress. Soft tension, slightly faster.
//   failed      — unrecoverable failure. Quiet stop, not alarm.
//
// Emotional rule: users should FEEL transitions, not read them.
// Stable states (LAN/STUN/idle) = invisible. Active states = felt.
// ─────────────────────────────────────────────────────────────────────────────
window.LANCHAT = window.LANCHAT || {};

LANCHAT.mood = (function () {
    var _current = 'idle';
    var _listeners = new Set();

    // Valid moods — anything outside this list is rejected
    var _VALID = new Set(['idle', 'connecting', 'LAN', 'STUN', 'TURN', 'unstable', 'reconnecting', 'failed']);

    return {
        get current() { return _current; },

        // ── Set mood ──────────────────────────────────────────────────────────
        // Validates, deduplicates, applies data-mood to <body>, notifies listeners.
        set: function (newMood, meta) {
            if (!_VALID.has(newMood)) {
                console.warn('[Mood] Unknown mood ignored:', newMood);
                return;
            }
            if (_current === newMood) return;

            var prev = _current;
            _current = newMood;

            // Drive the global CSS variable system
            document.body.setAttribute('data-mood', newMood);

            // Notify all listeners
            _listeners.forEach(function (fn) {
                try { fn(newMood, prev, meta || {}); } catch (e) { /* listener errors are isolated */ }
            });

            // Dispatch on LANCHAT event bus so any module can react without coupling
            if (window.LANCHAT && LANCHAT.events) {
                LANCHAT.events.dispatchEvent(new CustomEvent('ui:mood', {
                    detail: { mood: newMood, prev: prev, meta: meta || {} }
                }));
            }

            console.log('[Mood]', prev, '→', newMood, meta ? JSON.stringify(meta) : '');
        },

        // ── Subscribe to mood changes ─────────────────────────────────────────
        // fn(newMood, prevMood, meta) — called synchronously on every change.
        onChange: function (fn) {
            _listeners.add(fn);
        },

        // ── Remove a listener ─────────────────────────────────────────────────
        offChange: function (fn) {
            _listeners.delete(fn);
        },

        // ── Reset to idle (call ended, socket connected) ──────────────────────
        reset: function () {
            this.set('idle');
        },
    };
}());

// Export for ES6 module imports
export const moodEngine = LANCHAT.mood;
