"""
launcher.py — LAN Chat Control Center (GUI layer).

Fix 1: GUI calls ONLY ServiceAPI — zero direct imports of process_manager,
       ngrok_manager, or controller. Swapping the GUI = rewrite this file only.

Fix 2: GUI subscribes to SystemState (process/network) and UIState (logs/buttons)
       separately. No mixed-domain state reads.

Fix 3: Failure isolation is handled entirely in controller.py — the GUI just
       reacts to state events. It never decides what to restart.
"""
import socket
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, scrolledtext, ttk

from config_manager import load_config, save_config_debounced
from controller import ServiceController
from ngrok_manager import NgrokManager
from process_manager import ServerProcess
from service_api import ServiceAPI
from state_tracker import SystemState, UIState

# ── Bootstrap ─────────────────────────────────────────────────────────────────
config    = load_config()
server    = ServerProcess()
ngrok     = NgrokManager()
sys_state = SystemState()
ui_state  = UIState()
ctrl      = ServiceController(sys_state, ui_state, server, ngrok, lambda: config)
api       = ServiceAPI(sys_state, ui_state, server, ngrok, ctrl, lambda: config)

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":      "#1e1e2e",
    "panel":   "#2a2a3e",
    "border":  "#3a3a5e",
    "green":   "#25D366",
    "red":     "#e06c75",
    "orange":  "#f0b429",
    "blue":    "#53bdeb",
    "text":    "#cdd6f4",
    "subtext": "#a6adc8",
    "btn_fg":  "#ffffff",
}

_LOG_COLORS = {
    "error": "red", "exception": "red", "traceback": "red", "critical": "red",
    "warning": "orange", "warn": "orange",
    "started": "green", "running": "green",
    "🟢": "green", "✅": "green",
    "🌐": "blue", "🚀": "blue", "ℹ": "blue",
    "❌": "red", "🛑": "red",
    "⚠": "orange", "🔄": "orange", "🧹": "orange",
}


def _tag_for(line: str) -> str:
    ll = line.lower()
    for keyword, tag in _LOG_COLORS.items():
        if keyword in ll or keyword in line:
            return tag
    return ""


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


# ══════════════════════════════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════════════════════════════

class ControlCenter:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LAN Chat — Control Center")
        self.root.geometry("920x640")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)

        self._build_ui()
        self._wire_events()    # Fix 2: subscribe to split state domains
        self._detect_ip()
        self._start_watchdog() # calls ctrl.sync_state() — Fix 3 entry point

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=C["bg"])
        hdr.pack(fill=tk.X, padx=16, pady=(14, 0))

        tk.Label(hdr, text="LAN Chat  Control Center",
                 font=("Segoe UI", 16, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(hdr, text="⬤  Stopped",
                                   font=("Segoe UI", 10),
                                   bg=C["bg"], fg=C["red"])
        self.status_lbl.pack(side=tk.RIGHT)

        info = tk.Frame(self.root, bg=C["bg"])
        info.pack(fill=tk.X, padx=16, pady=(6, 0))

        self.ip_var  = tk.StringVar(value="Local:   detecting…")
        self.url_var = tk.StringVar(value="Public:  —")

        tk.Label(info, textvariable=self.ip_var,
                 font=("Segoe UI", 9), bg=C["bg"], fg=C["subtext"]).pack(side=tk.LEFT, padx=(0, 24))
        tk.Label(info, textvariable=self.url_var,
                 font=("Segoe UI", 9), bg=C["bg"], fg=C["subtext"]).pack(side=tk.LEFT)

        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X, padx=16, pady=10)

        main = tk.Frame(self.root, bg=C["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self._build_controls(main)
        self._build_log(main)

    def _build_controls(self, parent):
        pnl = tk.Frame(parent, bg=C["panel"], bd=0)
        pnl.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), ipadx=10, ipady=10)

        def section(label):
            tk.Label(pnl, text=label, font=("Segoe UI", 8, "bold"),
                     bg=C["panel"], fg=C["subtext"]).pack(anchor=tk.W, padx=10, pady=(12, 2))

        def btn(label, cmd, color=C["border"]):
            b = tk.Button(pnl, text=label, command=cmd,
                          bg=color, fg=C["btn_fg"],
                          font=("Segoe UI", 9, "bold"),
                          relief=tk.FLAT, cursor="hand2",
                          width=22, pady=6,
                          activebackground=color, activeforeground=C["btn_fg"])
            b.pack(fill=tk.X, padx=10, pady=2)
            return b

        section("SERVER")
        self.btn_lan    = btn("▶  Start  LAN",    self._start_lan,    C["green"])
        self.btn_public = btn("🌐  Start  PUBLIC", self._start_public, C["blue"])
        self.btn_stop   = btn("■  Stop  Server",  self._stop_all,     C["red"])
        self.btn_stop.config(state=tk.DISABLED)

        section("NGROK TUNNEL")
        self.btn_ngrok_start = btn("▶  Start  ngrok", self._start_ngrok)
        self.btn_ngrok_stop  = btn("■  Stop  ngrok",  self._stop_ngrok)
        self.btn_ngrok_stop.config(state=tk.DISABLED)

        section("QUICK ACTIONS")
        btn("🌍  Open in Browser",  self._open_browser)
        self.btn_copy = btn("📋  Copy Public URL", self._copy_url)
        self.btn_copy.config(state=tk.DISABLED)

        section("CONFIG")
        self._build_config_fields(pnl)

        self.auto_ngrok_var   = tk.BooleanVar(value=config.get("AUTO_NGROK", False))
        self.auto_restart_var = tk.BooleanVar(value=config.get("AUTO_RESTART_SERVER", False))

        for var, label in (
            (self.auto_ngrok_var,   "Auto-start ngrok with PUBLIC"),
            (self.auto_restart_var, "Auto-restart on crash"),
        ):
            tk.Checkbutton(pnl, text=label, variable=var,
                           bg=C["panel"], fg=C["text"],
                           selectcolor=C["bg"], activebackground=C["panel"],
                           font=("Segoe UI", 8),
                           command=self._save_config).pack(anchor=tk.W, padx=10, pady=(2, 0))

    def _build_config_fields(self, parent):
        def field(label, key, show=""):
            row = tk.Frame(parent, bg=C["panel"])
            row.pack(fill=tk.X, padx=10, pady=2)
            tk.Label(row, text=label, width=14, anchor=tk.W,
                     bg=C["panel"], fg=C["subtext"],
                     font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var = tk.StringVar(value=config.get(key, ""))
            tk.Entry(row, textvariable=var, show=show,
                     bg=C["bg"], fg=C["text"],
                     insertbackground=C["text"],
                     relief=tk.FLAT, font=("Segoe UI", 8), width=14).pack(
                         side=tk.LEFT, fill=tk.X, expand=True)
            var.trace_add("write", lambda *_: self._save_config())
            return var

        self.srv_pw_var   = field("Server PW",  "SERVER_PASSWORD", show="•")
        self.admin_pw_var = field("Admin PW",   "ADMIN_PASSWORD",  show="•")

    def _build_log(self, parent):
        lf = tk.Frame(parent, bg=C["panel"])
        lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(lf, text="SERVER LOG", font=("Segoe UI", 8, "bold"),
                 bg=C["panel"], fg=C["subtext"]).pack(anchor=tk.W, padx=10, pady=(8, 2))

        self.log_box = scrolledtext.ScrolledText(
            lf, state=tk.DISABLED,
            bg=C["bg"], fg=C["text"],
            font=("Consolas", 8), relief=tk.FLAT, wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        for tag, color in (("green", C["green"]), ("red", C["red"]),
                           ("orange", C["orange"]), ("blue", C["blue"])):
            self.log_box.tag_config(tag, foreground=color)

        br = tk.Frame(lf, bg=C["panel"])
        br.pack(fill=tk.X, padx=6, pady=(0, 6))
        tk.Button(br, text="Clear Log", command=self._clear_log,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 8), relief=tk.FLAT, cursor="hand2").pack(side=tk.RIGHT)

    # ── Fix 2: subscribe to split state domains ───────────────────────────────

    def _wire_events(self):
        def on_main(fn):
            def _w(v):
                self.root.after(0, lambda val=v: fn(val))
            return _w

        # SystemState events (process/network reality)
        sys_state.on("server_running", on_main(self._on_server_running))
        sys_state.on("ngrok_running",  on_main(self._on_ngrok_running))
        sys_state.on("public_url",     on_main(self._on_public_url))

        # UIState events (log lines from any background thread)
        ui_state.on("log", on_main(self._on_log_line))

    def _on_server_running(self, running: bool):
        if running:
            self.status_lbl.config(text="⬤  Running", fg=C["green"])
            self.btn_stop.config(state=tk.NORMAL)
            self.btn_lan.config(state=tk.DISABLED)
            self.btn_public.config(state=tk.DISABLED)
        else:
            self.status_lbl.config(text="⬤  Stopped", fg=C["red"])
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_lan.config(state=tk.NORMAL)
            self.btn_public.config(state=tk.NORMAL)

    def _on_ngrok_running(self, running: bool):
        self.btn_ngrok_start.config(state=tk.DISABLED if running else tk.NORMAL)
        self.btn_ngrok_stop.config(state=tk.NORMAL if running else tk.DISABLED)
        if not running:
            self.btn_copy.config(state=tk.DISABLED)

    def _on_public_url(self, url: str | None):
        self.url_var.set(f"Public:  {url}" if url else "Public:  —")
        self.btn_copy.config(
            state=tk.NORMAL if (url and api.is_ngrok_ready()) else tk.DISABLED)
        if url:
            self._write_log(f"🌍  Public URL: {url}", "green")

    def _on_log_line(self, line: str | None):
        if line:
            self._write_log(line, _tag_for(line))

    # ── Logging ───────────────────────────────────────────────────────────────

    def _write_log(self, msg: str, tag: str = ""):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, msg.rstrip() + "\n", tag)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def _clear_log(self):
        ui_state.clear_log()
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ── IP detection ──────────────────────────────────────────────────────────

    def _detect_ip(self):
        def _run():
            ip = _get_local_ip()
            sys_state.set("local_ip", ip)
            self.root.after(0, lambda: self.ip_var.set(
                f"Local:   http://{ip}:{config.get('PORT', 5000)}"))
        threading.Thread(target=_run, daemon=True).start()

    # ── Config ────────────────────────────────────────────────────────────────

    def _save_config(self):
        config["SERVER_PASSWORD"]     = self.srv_pw_var.get()
        config["ADMIN_PASSWORD"]      = self.admin_pw_var.get()
        config["AUTO_NGROK"]          = self.auto_ngrok_var.get()
        config["AUTO_RESTART_SERVER"] = self.auto_restart_var.get()
        save_config_debounced(config)

    # ── Watchdog — Fix 3 entry point ──────────────────────────────────────────

    def _start_watchdog(self):
        def _loop():
            while True:
                time.sleep(2)
                ctrl.sync_state()   # classify + isolate failures
        threading.Thread(target=_loop, daemon=True).start()

    # ── Fix 1: GUI calls ServiceAPI only — no direct service access ───────────

    def _start_lan(self):
        result = api.start_server("LAN")
        if result.ok:
            ui_state.append_log(f"🟢  LAN server started  (PID {result.data['pid']})")
        else:
            ui_state.append_log(f"❌  {result.message}")

    def _start_public(self):
        result = api.start_server("PUBLIC")
        if result.ok:
            ui_state.append_log(f"🌐  PUBLIC server started  (PID {result.data['pid']})")
        else:
            ui_state.append_log(f"❌  {result.message}")

    def _stop_all(self):
        ui_state.append_log("🧹  Shutting down all services…")
        result = api.stop_all()
        ui_state.append_log(f"✅  {result.message}")

    def _start_ngrok(self):
        result = api.start_ngrok()
        ui_state.append_log(
            f"🚀  {result.message}" if result.ok else f"❌  {result.message}")
        if not result.ok and "not found" in result.message:
            messagebox.showerror("ngrok not found", result.message)

    def _stop_ngrok(self):
        result = api.stop_ngrok()
        ui_state.append_log(f"🛑  {result.message}")

    def _open_browser(self):
        webbrowser.open(api.get_public_url() or api.get_local_url())

    def _copy_url(self):
        if not api.is_ngrok_ready():
            messagebox.showwarning("Not ready", "ngrok URL is not confirmed yet.")
            return
        url = api.get_public_url()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            ui_state.append_log(f"📋  Copied: {url}")
        else:
            messagebox.showwarning("No URL", "Public URL is not available.")

    # ── Window close ──────────────────────────────────────────────────────────

    def on_closing(self):
        if api.is_server_running() or api.is_ngrok_running():
            if messagebox.askokcancel(
                "Quit", "Server / ngrok is still running.\nStop everything and quit?"
            ):
                api.stop_all()
                self.root.destroy()
        else:
            self.root.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app = ControlCenter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
