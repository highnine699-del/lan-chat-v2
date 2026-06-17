# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

"""
process_manager.py — Server subprocess control.

Starts/stops server.py as a child process and streams its stdout.
Never embeds the Flask app — always a separate process.
"""
import os
import sys
import subprocess

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class ServerProcess:
    def __init__(self):
        self.process: subprocess.Popen | None = None

    def start(self, env_vars: dict | None = None) -> int:
        """
        Launch server.py as a subprocess.
        Returns the PID of the new process.
        """
        env = os.environ.copy()
        if env_vars:
            env.update({k: str(v) for k, v in env_vars.items()})

        # Force Python to flush stdout immediately — without this, lines
        # sit in the buffer on Windows and never reach the log panel.
        env["PYTHONUNBUFFERED"] = "1"

        # When running as a PyInstaller exe, __file__ points to the temp
        # extraction folder. Use the exe's own directory instead so we can
        # find server.py, static/, templates/, etc.
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
            # sys.executable is LanChat.exe — find the real Python interpreter.
            # Prefer pythonw.exe (windowless) to avoid a CMD window popping up.
            import shutil
            python_exe = (
                shutil.which("pythonw") or
                shutil.which("python") or
                "python"
            )
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Prefer pythonw.exe alongside the running interpreter (no console window)
            import shutil
            _pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            python_exe = _pythonw if os.path.exists(_pythonw) else (
                shutil.which("pythonw") or sys.executable
            )

        server_path = os.path.join(base_dir, "server.py")

        self.process = subprocess.Popen(
            [python_exe, "-u", server_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=base_dir,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return self.process.pid

    def stop(self) -> None:
        """Terminate the server process and all its children."""
        if not self.process:
            return

        try:
            if _PSUTIL:
                try:
                    parent = psutil.Process(self.process.pid)
                    for child in parent.children(recursive=True):
                        child.terminate()
                    parent.terminate()
                    try:
                        parent.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        parent.kill()
                except psutil.NoSuchProcess:
                    # Process already gone — fall back to subprocess handle
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
            else:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        except Exception:
            pass
        finally:
            self.process = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def read_output(self) -> str | None:
        """Read one line from stdout (non-blocking friendly — call in a thread)."""
        if self.process and self.process.stdout:
            try:
                return self.process.stdout.readline()
            except Exception:
                return None
        return None
