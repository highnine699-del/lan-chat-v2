"""
controller.py — Service orchestration with failure isolation.

Fix 3: Crash classification + isolated restart strategy.

  Before: any crash → restart everything (wrong)
  After:  server dead, ngrok alive → restart server only
          ngrok dead, server alive → restart ngrok only
          both dead               → restart both in order

Restart policy per component:
  - Exponential backoff: 2s, 4s, 8s … capped at 60s
  - Per-component attempt counter (server and ngrok tracked separately)
  - Attempt counter resets on a clean manual start
  - Gives up after MAX_RESTART_ATTEMPTS and emits a log line

sync_state() is the reconciliation entry point — called by the watchdog
every 2 s. It checks PID reality vs in-memory flags and corrects divergence
before deciding whether to trigger a restart.

This module has NO GUI imports. It communicates only through SystemState
and UIState event buses.
"""
from __future__ import annotations

import time
import threading
import logging
from enum import Enum, auto

log = logging.getLogger("controller")


class _Component(Enum):
    SERVER = auto()
    NGROK  = auto()


class ServiceController:
    """
    Orchestrates server + ngrok lifecycle with per-component failure isolation.

    Parameters
    ----------
    sys_state  : SystemState
    ui_state   : UIState
    server     : ServerProcess
    ngrok      : NgrokManager
    get_config : callable → dict
    """

    def __init__(self, sys_state, ui_state, server, ngrok, get_config):
        self._sys      = sys_state
        self._ui       = ui_state
        self._server   = server
        self._ngrok    = ngrok
        self._cfg      = get_config

        self._lock = threading.Lock()

        # Per-component restart tracking
        self._attempts: dict[_Component, int] = {
            _Component.SERVER: 0,
            _Component.NGROK:  0,
        }
        self._last_server_env: dict[str, str] = {}
        self._last_ngrok_port: int = 5000

    # ── Public: record clean starts (resets attempt counters) ─────────────────

    def record_start(self, env: dict[str, str]) -> None:
        with self._lock:
            self._last_server_env = dict(env)
            self._attempts[_Component.SERVER] = 0

    def record_ngrok_start(self, port: int) -> None:
        with self._lock:
            self._last_ngrok_port = port
            self._attempts[_Component.NGROK] = 0

    # ── Fix 3: sync_state — reconcile reality, classify failure ───────────────

    def sync_state(self) -> None:
        """
        Compare actual process state against in-memory flags.
        Corrects divergence and triggers isolated restarts only for the
        component that actually failed.

        Called by the watchdog every 2 s from a background thread.
        """
        server_flag  = self._sys.get("server_running")
        ngrok_flag   = self._sys.get("ngrok_running")
        server_alive = self._server.is_running()
        ngrok_alive  = self._ngrok.is_running()

        # ── Server PID drift (process replaced without us knowing) ────────────
        if server_flag and server_alive:
            real_pid = self._server.process.pid if self._server.process else None
            if real_pid != self._sys.get("server_pid"):
                log.info("sync_state: correcting stale server_pid → %s", real_pid)
                self._sys.set("server_pid", real_pid)

        # ── Classify failures — Fix 3 core logic ─────────────────────────────
        server_crashed = server_flag and not server_alive
        ngrok_crashed  = ngrok_flag  and not ngrok_alive

        if server_crashed:
            log.warning("sync_state: server process died unexpectedly")
            self._sys.set("server_running", False)
            self._sys.set("server_pid",     None)
            self._sys.set("mode",           None)
            self._ui.append_log("❌  Server crashed or stopped unexpectedly.")
            # Restart ONLY the server — ngrok may still be healthy
            self._schedule_restart(_Component.SERVER)

        if ngrok_crashed:
            log.warning("sync_state: ngrok process died unexpectedly")
            self._sys.set("ngrok_running", False)
            self._sys.set("public_url",    None)
            self._ui.append_log("❌  ngrok tunnel dropped unexpectedly.")
            # Restart ONLY ngrok — server is unaffected
            self._schedule_restart(_Component.NGROK)

    # ── Fix 3: isolated restart scheduler ────────────────────────────────────

    def _schedule_restart(self, component: _Component) -> None:
        cfg = self._cfg()
        if not cfg.get("AUTO_RESTART_SERVER", False):
            return

        max_attempts = int(cfg.get("MAX_RESTART_ATTEMPTS", 3))

        with self._lock:
            attempt = self._attempts[component] + 1
            if attempt > max_attempts:
                self._ui.append_log(
                    f"⛔  Auto-restart ({component.name}): "
                    f"reached max attempts ({max_attempts}). Giving up."
                )
                return
            self._attempts[component] = attempt
            # Exponential backoff: 2s, 4s, 8s … capped at 60s
            delay = min(2 ** attempt, 60)

        self._ui.append_log(
            f"🔄  Auto-restart ({component.name}): "
            f"attempt {attempt}/{max_attempts} in {delay} s…"
        )
        threading.Thread(
            target=self._do_restart,
            args=(component, attempt, max_attempts, delay),
            daemon=True,
        ).start()

    def _do_restart(
        self,
        component: _Component,
        attempt: int,
        max_attempts: int,
        delay: float,
    ) -> None:
        time.sleep(delay)

        if component is _Component.SERVER:
            self._restart_server(attempt, max_attempts)
        else:
            self._restart_ngrok(attempt, max_attempts)

    def _restart_server(self, attempt: int, max_attempts: int) -> None:
        with self._lock:
            env = dict(self._last_server_env)
        try:
            pid = self._server.start(env)
            mode = "PUBLIC" if env.get("PUBLIC_MODE") == "true" else "LAN"
            self._sys.set("server_pid",     pid)
            self._sys.set("mode",           mode)
            self._sys.set("server_running", True)
            with self._lock:
                self._attempts[_Component.SERVER] = 0
            self._ui.append_log(
                f"✅  Server restarted (attempt {attempt}/{max_attempts}, PID {pid})."
            )
            # Re-stream logs for the new process
            threading.Thread(target=self._stream_server_logs, daemon=True).start()
        except Exception as exc:
            self._ui.append_log(f"❌  Server restart failed: {exc}")
            self._sys.set("server_running", False)

    def _restart_ngrok(self, attempt: int, max_attempts: int) -> None:
        with self._lock:
            port = self._last_ngrok_port
        try:
            self._ngrok.start(port)
            self._sys.set("ngrok_running", True)
            with self._lock:
                self._attempts[_Component.NGROK] = 0
            self._ui.append_log(
                f"✅  ngrok restarted (attempt {attempt}/{max_attempts})."
            )
            # Wait for URL in background
            threading.Thread(target=self._wait_for_ngrok_url, daemon=True).start()
        except Exception as exc:
            self._ui.append_log(f"❌  ngrok restart failed: {exc}")
            self._sys.set("ngrok_running", False)

    # ── Helpers shared with ServiceAPI ────────────────────────────────────────

    def _stream_server_logs(self) -> None:
        while self._server.is_running():
            line = self._server.read_output()
            if line:
                self._ui.append_log(line.rstrip())

    def _wait_for_ngrok_url(self) -> None:
        ready = self._ngrok.url_ready.wait(timeout=20)
        if ready:
            self._sys.set("public_url", self._ngrok.get_url())
        else:
            self._ui.append_log("⚠  ngrok URL not detected after 20 s.")

    # ── Coordinated shutdown ──────────────────────────────────────────────────

    def shutdown_all(self) -> None:
        """Stop ngrok then server. Resets all system state and attempt counters."""
        if self._ngrok.is_running():
            self._ngrok.stop()
        self._sys.set("ngrok_running", False)
        self._sys.set("public_url",    None)

        if self._server.is_running():
            self._server.stop()
        self._sys.set("server_running", False)
        self._sys.set("server_pid",     None)
        self._sys.set("mode",           None)

        with self._lock:
            self._attempts[_Component.SERVER] = 0
            self._attempts[_Component.NGROK]  = 0
