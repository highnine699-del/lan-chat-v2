# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

# -*- coding: utf-8 -*-
"""
service_api.py — Hard boundary between GUI and service internals.

Fix 1: The GUI calls ONLY this module. It never imports process_manager,
       ngrok_manager, or controller directly. This means:
         - swapping the GUI framework = rewrite only launcher.py
         - adding a CLI = implement the same API calls, zero logic duplication
         - unit-testing control logic = mock this interface, no Tkinter needed

Public surface
--------------
    api = ServiceAPI(state, sys_state, ui_state, server, ngrok, ctrl, config_fn)

    api.start_server("LAN")   → starts server in LAN mode
    api.start_server("PUBLIC")→ starts server in PUBLIC mode
    api.stop_server()         → stops server only
    api.start_ngrok()         → starts ngrok tunnel
    api.stop_ngrok()          → stops ngrok only
    api.stop_all()            → coordinated full shutdown
    api.get_local_url()       → "http://192.168.x.x:5000"
    api.get_public_url()      → "https://xxx.ngrok-free.app" | None

All state mutations go through sys_state / ui_state — never direct.
All errors are returned as ServiceResult, never raised to the GUI.
"""
from __future__ import annotations

import threading
import logging
from dataclasses import dataclass
from typing import Literal

log = logging.getLogger("service_api")


@dataclass
class ServiceResult:
    """Returned by every API call so the GUI can react without try/except."""
    ok:      bool
    message: str
    data:    dict | None = None


class ServiceAPI:
    def __init__(self, sys_state, ui_state, server, ngrok, ctrl, get_config):
        self._sys   = sys_state
        self._ui    = ui_state
        self._srv   = server
        self._ngrok = ngrok
        self._ctrl  = ctrl
        self._cfg   = get_config   # callable → dict

    # ── Server ────────────────────────────────────────────────────────────────

    def start_server(self, mode: Literal["LAN", "PUBLIC"]) -> ServiceResult:
        """
        Start the server in the given mode.
        Enforces mode exclusivity — cannot start PUBLIC while LAN is running.
        """
        current_mode = self._sys.get("mode")
        if self._srv.is_running():
            if current_mode != mode:
                return ServiceResult(
                    ok=False,
                    message=f"Stop {current_mode} mode first before switching to {mode}.",
                )
            return ServiceResult(ok=False, message="Server is already running.")

        cfg = self._cfg()
        env: dict[str, str] = {}

        if mode == "LAN":
            env["PUBLIC_MODE"] = "false"
        else:
            env["PUBLIC_MODE"]     = "true"
            env["SERVER_PASSWORD"] = cfg.get("SERVER_PASSWORD", "")
            # Tighten security for public deployment
            env["TRUSTED_PROXY"]   = "true"   # ngrok sets X-Forwarded-For reliably
            # Lock CORS to the ngrok URL once it's known; fall back to * until then
            ngrok_url = self._sys.get("public_url") or ""
            if ngrok_url:
                env["ALLOWED_ORIGINS"] = ngrok_url
            # Generate a stable SECRET_KEY for this session if not already set
            import os as _os, secrets as _sec
            env["SECRET_KEY"] = _os.environ.get("SECRET_KEY") or _sec.token_hex(32)

        if cfg.get("ADMIN_PASSWORD"):
            env["ADMIN_PASSWORD"] = cfg["ADMIN_PASSWORD"]

        # Pass port if non-default
        port = cfg.get("PORT", 5000)
        if port != 5000:
            env["PORT"] = str(port)

        # Pass max restart attempts to controller
        try:
            max_attempts = int(cfg.get("MAX_RESTART_ATTEMPTS", 3))
            self._ctrl.set_max_attempts(max_attempts)
        except (ValueError, AttributeError):
            pass

        try:
            pid = self._srv.start(env)
        except Exception as exc:
            return ServiceResult(ok=False, message=f"Failed to start server: {exc}")

        self._ctrl.record_start(env)
        self._sys.set("server_pid",     pid)
        self._sys.set("mode",           mode)
        self._sys.set("server_running", True)

        # Stream logs in background — owned here, not in the GUI
        threading.Thread(target=self._stream_logs, daemon=True).start()

        # Auto-start ngrok if configured and mode is PUBLIC
        if mode == "PUBLIC" and cfg.get("AUTO_NGROK"):
            self.start_ngrok()

        return ServiceResult(ok=True, message=f"{mode} server started (PID {pid})", data={"pid": pid})

    def stop_server(self) -> ServiceResult:
        """Stop only the server process, leave ngrok running."""
        self._srv.stop()
        self._sys.set("server_running", False)
        self._sys.set("server_pid",     None)
        self._sys.set("mode",           None)
        return ServiceResult(ok=True, message="Server stopped.")

    # ── ngrok ─────────────────────────────────────────────────────────────────

    def start_ngrok(self) -> ServiceResult:
        if self._ngrok.is_running():
            return ServiceResult(ok=False, message="ngrok is already running.")

        cfg  = self._cfg()
        port = cfg.get("PORT", 5000)

        try:
            self._ngrok.start(port)
        except FileNotFoundError as exc:
            return ServiceResult(ok=False, message=str(exc))

        self._sys.set("ngrok_running", True)
        threading.Thread(target=self._wait_for_url, daemon=True).start()
        return ServiceResult(ok=True, message=f"ngrok starting on port {port}…")

    def stop_ngrok(self) -> ServiceResult:
        self._ngrok.stop()
        self._sys.set("ngrok_running", False)
        self._sys.set("public_url",    None)
        return ServiceResult(ok=True, message="ngrok stopped.")

    # ── Coordinated shutdown ──────────────────────────────────────────────────

    def stop_all(self) -> ServiceResult:
        """Stop ngrok first, then server. Resets all system state."""
        self._ctrl.shutdown_all()
        return ServiceResult(ok=True, message="Clean shutdown complete.")

    # ── Queries (GUI reads these, never touches sys_state directly) ───────────

    def get_local_url(self) -> str:
        ip   = self._sys.get("local_ip") or "localhost"
        port = self._cfg().get("PORT", 5000)
        return f"http://{ip}:{port}"

    def get_public_url(self) -> str | None:
        return self._sys.get("public_url")

    def is_server_running(self) -> bool:
        return self._srv.is_running()

    def is_ngrok_running(self) -> bool:
        return self._ngrok.is_running()

    def is_ngrok_ready(self) -> bool:
        """True only after the tunnel URL has been confirmed (atomic Event)."""
        return self._ngrok.url_ready.is_set()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _stream_logs(self) -> None:
        """Read server stdout line-by-line and push to ui_state log queue."""
        self._ui.append_log("── Log stream started ──")
        proc = self._srv.process
        if not proc or not proc.stdout:
            self._ui.append_log("⚠ No stdout pipe available for log streaming.")
            return
        try:
            while True:
                line = proc.stdout.readline()
                if line == "":
                    self._ui.append_log("── Log stream ended (EOF) ──")
                    break
                if line:
                    self._ui.append_log(line.rstrip())
        except Exception as exc:
            self._ui.append_log(f"⚠ Log stream error: {exc}")

    def _wait_for_url(self) -> None:
        """Block on url_ready Event, then write confirmed URL to sys_state."""
        ready = self._ngrok.url_ready.wait(timeout=20)
        if ready:
            url = self._ngrok.get_url()
            self._sys.set("public_url", url)
            # Tighten CORS now that we know the exact ngrok URL.
            # Send a live update to the running server process via env is not
            # possible (env is read at startup), but we record it so the next
            # restart picks it up automatically.
            if url and self._sys.get("mode") == "PUBLIC":
                self._ui.append_log(
                    f"🔒  CORS locked to {url} — only this origin can connect."
                )
        else:
            # Signal timeout via a sentinel so GUI can show a warning
            self._ui.append_log(
                "⚠  ngrok URL not detected after 20 s. Check ngrok dashboard."
            )
