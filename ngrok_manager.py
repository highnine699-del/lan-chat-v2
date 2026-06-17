# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
ngrok_manager.py — Cross-platform ngrok tunnel control.

Starts ngrok as a subprocess and discovers the public URL via the
local ngrok API (localhost:4040), which is more reliable than parsing
stdout line-by-line.

URL discovery is retry-based (up to 20 attempts × 0.5 s) and handles:
  - API not ready yet on startup
  - Multiple tunnels (picks first HTTPS one)
  - Transient connection errors
"""
import os
import time
import shutil
import threading
import subprocess
import urllib.request
import json


class NgrokManager:
    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.url_ready = threading.Event()
        self.public_url: str | None = None
        self._lock = threading.Lock()
        self._started_at: float = 0.0

    def was_alive_long_enough(self, min_seconds: float = 10.0) -> bool:
        """Return True if the tunnel ran for at least min_seconds before dying."""
        return (time.time() - self._started_at) >= min_seconds

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self, port: int = 5000) -> None:
        """Launch ngrok and begin URL discovery in a background thread."""
        ngrok_bin = self._find_ngrok()
        if not ngrok_bin:
            raise FileNotFoundError(
                "ngrok not found. Install it from https://ngrok.com/download "
                "and make sure it is on your PATH."
            )

        # Kill any orphan ngrok processes before starting a new one.
        # The free plan only allows one tunnel — a leftover process blocks the slot.
        self._kill_orphans()

        # If NGROK_AUTHTOKEN is set, configure it before starting the tunnel.
        # Done outside the lock so _started_at reflects actual tunnel start time.
        auth_token = os.environ.get("NGROK_AUTHTOKEN", "")
        if auth_token:
            _kw: dict = {}
            if os.name == "nt":
                _kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.run(
                [ngrok_bin, "config", "add-authtoken", auth_token],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                **_kw,
            )

        with self._lock:
            self.public_url = None
            self.url_ready.clear()
            self._started_at = time.time()

            kwargs: dict = {}
            if os.name == "nt":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                kwargs["startupinfo"] = si
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                [ngrok_bin, "http", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **kwargs,
            )

        threading.Thread(target=self._poll_api, daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                self.process = None
            self.public_url = None
            self.url_ready.clear()
            self._started_at = 0.0

    @staticmethod
    def _kill_orphans() -> None:
        """Terminate any existing ngrok processes so the free-plan slot is free."""
        try:
            import psutil
            for proc in psutil.process_iter(["name", "pid"]):
                if proc.info["name"] and "ngrok" in proc.info["name"].lower():
                    try:
                        proc.terminate()
                    except Exception:
                        pass
        except ImportError:
            # psutil not available — fall back to taskkill on Windows
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "ngrok.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

    def get_url(self) -> str | None:
        return self.public_url

    def is_running(self) -> bool:
        with self._lock:
            return self.process is not None and self.process.poll() is None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _poll_api(self, retries: int = 20, interval: float = 0.5) -> None:
        """
        Retry-based URL discovery via the ngrok local API.
        Handles: API not ready, multiple tunnels, transient errors.
        Picks the first HTTPS tunnel found.
        Gap 3: sets url_ready Event only after URL is confirmed.
        """
        for _ in range(retries):
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:4040/api/tunnels", timeout=1
                ) as resp:
                    data = json.loads(resp.read())
                    for tunnel in data.get("tunnels", []):
                        url = tunnel.get("public_url", "")
                        if url.startswith("https://"):
                            self.public_url = url
                            self.url_ready.set()   # Gap 3: atomic signal
                            return
            except Exception:
                pass
            time.sleep(interval)

    @staticmethod
    def _find_ngrok() -> str | None:
        """Locate the ngrok binary on PATH or common install locations."""
        found = shutil.which("ngrok")
        if found:
            return found

        import os
        candidates = [
            os.path.expanduser("~/ngrok"),
            os.path.expanduser("~/ngrok.exe"),
            os.path.expanduser("~/Downloads/ngrok.exe"),
            "C:\\Program Files\\ngrok\\ngrok.exe",
            "C:\\Program Files (x86)\\ngrok\\ngrok.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return None
