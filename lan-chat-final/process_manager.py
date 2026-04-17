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

        server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

        self.process = subprocess.Popen(
            [sys.executable, server_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return self.process.pid

    def stop(self) -> None:
        """Terminate the server process and all its children."""
        if not self.process:
            return

        try:
            if _PSUTIL:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                try:
                    parent.wait(timeout=5)
                except psutil.TimeoutExpired:
                    parent.kill()
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
