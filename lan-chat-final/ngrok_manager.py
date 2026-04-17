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
        # Gap 3: ready event — set only when URL is confirmed, never before
        self.url_ready = threading.Event()
        self.public_url: str | None = None
        self._lock = threading.Lock()

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self, port: int = 5000) -> None:
        """Launch ngrok and begin URL discovery in a background thread."""
        ngrok_bin = self._find_ngrok()
        if not ngrok_bin:
            raise FileNotFoundError(
                "ngrok not found. Install it from https://ngrok.com/download "
                "and make sure it is on your PATH."
            )

        with self._lock:
            self.public_url = None
            self.url_ready.clear()   # Gap 3: reset before each start
            self.process = subprocess.Popen(
                [ngrok_bin, "http", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
            self.url_ready.clear()   # Gap 3: reset on stop

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
