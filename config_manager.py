# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
config_manager.py — Persistent runtime configuration for the Control Center.

Stores user preferences (passwords, auto-ngrok flag, etc.) in a JSON file
so they survive restarts. Completely separate from config.py, which holds
server-side constants.

save_config_debounced() coalesces rapid keystrokes into a single write
after a 1-second idle period, preventing partial writes and disk churn.

SECURITY NOTE: launcher_config.json stores passwords in plaintext on disk.
Keep this file private and do not commit it to version control.
It is listed in .gitignore. On shared machines, restrict file permissions:
  chmod 600 launcher_config.json   (Linux/macOS)
"""
import json
import os
import sys
import threading

_CONFIG_FILE = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__)),
    "launcher_config.json"
)

DEFAULT: dict = {
    "SERVER_PASSWORD":      "",
    "ADMIN_PASSWORD":       "",
    "NGROK_AUTH_TOKEN":     "",
    "AUTO_NGROK":           False,
    "PORT":                 5000,
    "AUTO_RESTART_SERVER":  False,
    "MAX_RESTART_ATTEMPTS": 3,
    "AUTO_OPEN_BROWSER":    True,
    "AUTO_OPEN_BROWSER_LAN":   True,
    "AUTO_OPEN_BROWSER_NGROK": True,
    "WINDOW_GEOMETRY":      "",
}

# Fields that must NEVER be written to disk — kept in memory only.
# Passwords on disk are a security risk on shared machines.
_SENSITIVE_FIELDS = {"SERVER_PASSWORD", "ADMIN_PASSWORD", "NGROK_AUTH_TOKEN"}


def _strip_sensitive(cfg: dict) -> dict:
    """Return a copy of cfg with sensitive fields removed before disk write."""
    return {k: v for k, v in cfg.items() if k not in _SENSITIVE_FIELDS}

_save_timer: threading.Timer | None = None
_timer_lock = threading.Lock()


def load_config() -> dict:
    if not os.path.exists(_CONFIG_FILE):
        save_config(DEFAULT)
        return dict(DEFAULT)
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT)


def save_config(cfg: dict) -> None:
    """Write config to disk immediately (atomic via temp file).
    Sensitive fields (passwords) are never written to disk.
    """
    tmp = _CONFIG_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_strip_sensitive(cfg), f, indent=2)
        os.replace(tmp, _CONFIG_FILE)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass


def save_config_debounced(cfg: dict, delay: float = 1.0) -> None:
    """
    Schedule a config save after *delay* seconds of inactivity.
    Cancels any pending save before scheduling a new one, so rapid
    keystrokes collapse into a single disk write.
    """
    global _save_timer
    with _timer_lock:
        if _save_timer is not None:
            _save_timer.cancel()
        # Snapshot the config dict so mutations after this call don't affect the write
        snapshot = dict(cfg)
        _save_timer = threading.Timer(delay, lambda: save_config(snapshot))
        _save_timer.daemon = True
        _save_timer.start()
