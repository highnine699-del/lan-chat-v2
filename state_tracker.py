# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
state_tracker.py — Split-domain state for the Control Center.

Fix 2: State is separated into two distinct domains so UI concerns never
       bleed into system concerns and vice versa.

SystemState  — process reality, network addresses, runtime mode
               Written by: ServiceAPI, ServiceController
               Read by:    ServiceAPI, ServiceController, GUI (via events)

UIState      — log buffer, button enable flags, visible tab
               Written by: GUI layer only
               Read by:    GUI layer only

Both are backed by the same EventState engine (single write path + event bus)
so the reactive wiring from the previous iteration is fully preserved.

Usage
-----
    sys_state = SystemState()
    ui_state  = UIState()

    # System domain
    sys_state.on("server_running", lambda v: ...)
    sys_state.set("server_running", True)

    # UI domain
    ui_state.on("log", lambda line: log_box.insert(...))
    ui_state.append_log("🟢 Server started")
    ui_state.set("buttons_enabled", True)
"""
import threading
from collections import deque
from typing import Any, Callable


# ── Generic event-state engine (unchanged from previous iteration) ────────────

class EventState:
    """
    Thread-safe key-value store with per-key change listeners.
    Single write path: set(key, value) — raises KeyError on unknown keys.
    """

    def __init__(self, schema: dict[str, Any]):
        self._data      = dict(schema)
        self._listeners: dict[str, list[Callable]] = {k: [] for k in schema}
        self._lock      = threading.Lock()

    def set(self, key: str, value: Any) -> None:
        if key not in self._data:
            raise KeyError(f"EventState: unknown key {key!r}")
        with self._lock:
            self._data[key] = value
            cbs = list(self._listeners[key])
        for cb in cbs:
            try:
                cb(value)
            except Exception:
                pass

    def get(self, key: str) -> Any:
        with self._lock:
            return self._data[key]

    def on(self, key: str, callback: Callable[[Any], None]) -> None:
        if key not in self._data:
            raise KeyError(f"EventState: unknown key {key!r}")
        with self._lock:
            self._listeners[key].append(callback)

    def off(self, key: str, callback: Callable[[Any], None]) -> None:
        with self._lock:
            try:
                self._listeners[key].remove(callback)
            except ValueError:
                pass

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    # Attribute-style access (reads only — writes route through set())
    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            raise AttributeError(key)
        try:
            return self.get(key)
        except KeyError:
            raise AttributeError(f"no key {key!r}")

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith("_"):
            super().__setattr__(key, value)
        elif hasattr(self, "_data") and key in self._data:
            self.set(key, value)
        else:
            super().__setattr__(key, value)


# ── Domain 1: System state ────────────────────────────────────────────────────
# Owned by ServiceAPI + ServiceController.
# Represents process reality and network addresses.
# GUI subscribes but never writes directly.

_SYSTEM_SCHEMA: dict[str, Any] = {
    "server_running": False,   # bool  — is server.py process alive?
    "ngrok_running":  False,   # bool  — is ngrok process alive?
    "public_url":     None,    # str | None — confirmed HTTPS tunnel URL
    "local_ip":       None,    # str | None — LAN IP address
    "mode":           None,    # None | "LAN" | "PUBLIC"
    "server_pid":     None,    # int | None
}


class SystemState(EventState):
    """
    Process + network reality.
    Written exclusively by ServiceAPI and ServiceController.
    """
    def __init__(self):
        super().__init__(_SYSTEM_SCHEMA)


# ── Domain 2: UI state ────────────────────────────────────────────────────────
# Owned by the GUI layer.
# Represents what the user sees — logs, button states, selected view.
# ServiceAPI writes to the log queue only (via append_log).

_UI_SCHEMA: dict[str, Any] = {
    "log":             None,    # str — latest log line (fires on every append)
    "buttons_enabled": True,    # bool — global enable/disable for action buttons
    "status_text":     "Stopped",  # str — header status label text
    "status_color":    "red",   # str — header status label colour key
}


class UIState(EventState):
    """
    GUI-visible state.
    append_log() is the only cross-layer write (ServiceAPI uses it for
    log lines that originate from background threads).
    """
    def __init__(self):
        super().__init__(_UI_SCHEMA)
        self._log_buffer: deque[str] = deque(maxlen=2000)
        self._buf_lock   = threading.Lock()

    def append_log(self, line: str) -> None:
        """
        Append a line to the log buffer and fire the "log" event.
        Safe to call from any thread — GUI callback must use root.after().
        """
        with self._buf_lock:
            self._log_buffer.append(line)
        self.set("log", line)

    def get_log_buffer(self) -> list[str]:
        """Return a snapshot of all buffered log lines."""
        with self._buf_lock:
            return list(self._log_buffer)

    def clear_log(self) -> None:
        with self._buf_lock:
            self._log_buffer.clear()
        self.set("log", None)
