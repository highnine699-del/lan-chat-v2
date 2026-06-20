# Copyright (c) 2026 ODETAYO JOSIAH INIOLUWA. Licensed under the MIT License - see LICENSE file for details.

# -*- coding: utf-8 -*-
"""
launcher.py — NEXUS Control Center (GUI layer).

Redesigned GUI with:
  - Modern dark card-based layout matching the NEXUS theme
  - Dashboard stat cards (uptime, users, CPU, RAM)
  - Collapsible sidebar with smooth toggle
  - Toast notifications instead of log spam for key events
  - Tabbed bottom panel (Log / Active Users)
  - Cleaner config section with labeled groups
  - Better button hierarchy (primary / secondary / danger)
  - Rounded visual style via canvas-backed frames
  - Status pill indicator (Running / Stopped / Starting)
  - Log auto-scroll lock (pause/resume scrolling)
  - Live uptime in window title bar
  - Keyboard shortcut cheatsheet popup (? button)
  - Public mode: enforces server password, sets TRUSTED_PROXY,
    generates SECRET_KEY, locks ALLOWED_ORIGINS to ngrok URL
"""
import csv
import datetime
import io
import os
import random
import re
import socket
import string
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Optional: winsound for notification sounds (Windows only)
try:
    import winsound as _winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False

# Optional heavy deps — degrade gracefully if missing
try:
    import psutil as _psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

try:
    import qrcode as _qrcode
    from PIL import Image as _PILImage, ImageTk as _ImageTk
    _HAS_QR = True
except ImportError:
    _HAS_QR = False

try:
    import pystray as _pystray
    from PIL import Image as _TrayImage
    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False

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
    # Backgrounds
    "bg":        "#0f0f17",
    "surface":   "#1a1a2e",
    "card":      "#1e1e30",
    "panel":     "#16213e",
    "border":    "#2a2a4a",
    "hover":     "#252540",
    # Accents
    "green":     "#00d26a",
    "green_dim": "#1a3d2b",
    "red":       "#ff4757",
    "red_dim":   "#3d1a1e",
    "orange":    "#ffa502",
    "orange_dim":"#3d2e0a",
    "blue":      "#4fc3f7",
    "blue_dim":  "#0d2a3d",
    "purple":    "#a78bfa",
    "purple_dim":"#1e1a3d",
    # Text
    "text":      "#e2e8f0",
    "subtext":   "#94a3b8",
    "muted":     "#475569",
    "btn_fg":    "#ffffff",
}

_LOG_COLORS = {
    "error": "red", "exception": "red", "traceback": "red", "critical": "red",
    "warning": "orange", "warn": "orange",
    "started": "green", "running": "green", "✅": "green", "✓": "green",
    "❌": "red", "⚠": "orange",
}

_LEVEL_WARN  = re.compile(r"warn|warning", re.I)
_LEVEL_ERROR = re.compile(r"error|exception|traceback|critical", re.I)
_ANSI_RE     = re.compile(r'\x1b\[[0-9;]*m')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _tag_for(line: str) -> str:
    ll = line.lower()
    for keyword, tag in _LOG_COLORS.items():
        if keyword in ll:
            return tag
    return ""


# ── Reusable widget helpers ───────────────────────────────────────────────────

class _Tooltip:
    def __init__(self, widget, text: str):
        self._widget = widget
        self._text   = text
        self._win    = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 6
        y = self._widget.winfo_rooty() + 4
        self._win = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, justify=tk.LEFT,
                 background=C["card"], foreground=C["text"],
                 relief=tk.FLAT, font=("Segoe UI", 8),
                 padx=8, pady=4).pack()

    def _hide(self, _event=None):
        if self._win:
            self._win.destroy()
            self._win = None


def _card(parent, **kw) -> tk.Frame:
    """A surface-colored frame that looks like a card."""
    defaults = dict(bg=C["card"], relief=tk.FLAT, bd=0)
    defaults.update(kw)
    return tk.Frame(parent, **defaults)


def _label(parent, text="", font=("Segoe UI", 9), fg=None, **kw) -> tk.Label:
    return tk.Label(parent, text=text, font=font,
                    fg=fg or C["text"], bg=kw.pop("bg", C["card"]), **kw)


def _btn(parent, text, command, style="secondary", width=0, tip="", **kw) -> tk.Button:
    """
    Styled button.  style = "primary" | "secondary" | "danger" | "ghost"
    """
    styles = {
        "primary":   (C["green"],  C["bg"],    C["green"]),
        "secondary": (C["border"], C["text"],  C["hover"]),
        "danger":    (C["red"],    C["bg"],    C["red_dim"]),
        "ghost":     (C["card"],   C["subtext"], C["hover"]),
        "blue":      (C["blue"],   C["bg"],    C["blue_dim"]),
        "orange":    (C["orange"], C["bg"],    C["orange_dim"]),
    }
    bg, fg, abg = styles.get(style, styles["secondary"])
    b = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
        font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
        cursor="hand2", pady=7, bd=0,
        **({} if not width else {"width": width}),
        **kw,
    )
    if tip:
        _Tooltip(b, tip)
    return b


# ── Toast notification system ─────────────────────────────────────────────────

class _ToastManager:
    """
    Shows brief overlay notifications in the top-right corner.
    Queues multiple toasts and fades them out automatically.
    """
    _COLORS = {
        "success": (C["green"],  C["green_dim"]),
        "error":   (C["red"],    C["red_dim"]),
        "warning": (C["orange"], C["orange_dim"]),
        "info":    (C["blue"],   C["blue_dim"]),
    }

    def __init__(self, root: tk.Tk):
        self._root   = root
        self._queue: list[tk.Toplevel] = []
        self._lock   = threading.Lock()

    def show(self, message: str, kind: str = "info", duration: int = 3000):
        self._root.after(0, lambda: self._create(message, kind, duration))

    def _create(self, message: str, kind: str, duration: int):
        accent, bg = self._COLORS.get(kind, self._COLORS["info"])

        win = tk.Toplevel(self._root)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=bg)

        inner = tk.Frame(win, bg=bg, padx=14, pady=10)
        inner.pack()

        # Accent bar on left
        tk.Frame(inner, bg=accent, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        icons = {"success": "✓", "error": "✕", "warning": "⚠", "info": "ℹ"}
        tk.Label(inner, text=icons.get(kind, "ℹ"),
                 font=("Segoe UI", 11, "bold"),
                 bg=bg, fg=accent).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(inner, text=message,
                 font=("Segoe UI", 9),
                 bg=bg, fg=C["text"],
                 wraplength=260, justify=tk.LEFT).pack(side=tk.LEFT)

        win.update_idletasks()
        self._reposition()

        with self._lock:
            self._queue.append(win)

        self._root.after(duration, lambda: self._dismiss(win))

    def _reposition(self):
        sw = self._root.winfo_screenwidth()
        base_y = 60
        with self._lock:
            for i, w in enumerate(self._queue):
                try:
                    w.update_idletasks()
                    ww = w.winfo_reqwidth()
                    wh = w.winfo_reqheight()
                    x  = sw - ww - 20
                    y  = base_y + i * (wh + 8)
                    w.wm_geometry(f"+{x}+{y}")
                except Exception:
                    pass

    def _dismiss(self, win: tk.Toplevel):
        try:
            win.destroy()
        except Exception:
            pass
        with self._lock:
            if win in self._queue:
                self._queue.remove(win)
        self._root.after(0, self._reposition)


# ── Stat card widget ──────────────────────────────────────────────────────────

class _StatCard(tk.Frame):
    """
    A small dashboard card showing an icon, a big value, and a label.
    """
    def __init__(self, parent, icon: str, label: str, color: str, tooltip: str = "", **kw):
        super().__init__(parent, bg=C["card"], relief=tk.FLAT, bd=0, **kw)
        self._color = color

        top = tk.Frame(self, bg=C["card"])
        top.pack(fill=tk.X, padx=12, pady=(10, 2))

        tk.Label(top, text=icon, font=("Segoe UI", 14),
                 bg=C["card"], fg=color).pack(side=tk.LEFT)

        self._val_var = tk.StringVar(value="—")
        self._val_lbl = tk.Label(self, textvariable=self._val_var,
                 font=("Segoe UI", 15, "bold"),
                 bg=C["card"], fg=C["text"])
        self._val_lbl.pack(anchor=tk.W, padx=12)

        tk.Label(self, text=label,
                 font=("Segoe UI", 7),
                 bg=C["card"], fg=C["subtext"]).pack(anchor=tk.W, padx=12, pady=(0, 10))

        # Bottom accent line
        tk.Frame(self, bg=color, height=2).pack(fill=tk.X, side=tk.BOTTOM)

        if tooltip:
            _Tooltip(self, tooltip)

        self._anim_target: str = ""
        self._anim_current: float = 0.0

    def set(self, value: str):
        """Animate numeric changes; fall back to instant set for non-numeric."""
        if self._val_var.get() == value:
            return
        # Try to animate numeric values
        try:
            target = float(re.sub(r'[^0-9.]', '', value) or "0")
            current_str = re.sub(r'[^0-9.]', '', self._val_var.get() or "0")
            current = float(current_str or "0")
            suffix = re.sub(r'[0-9.]', '', value)
            if target != current:
                self._anim_target = value
                self._anim_current = current
                self._animate_value(target, suffix, steps=8)
                return
        except Exception:
            pass
        self._val_var.set(value)

    def _animate_value(self, target: float, suffix: str, steps: int):
        diff = target - self._anim_current
        if steps <= 0 or abs(diff) < 0.5:
            self._val_var.set(f"{target:.0f}{suffix}" if suffix else f"{target:.0f}")
            return
        self._anim_current += diff / steps
        self._val_var.set(f"{self._anim_current:.0f}{suffix}" if suffix else f"{self._anim_current:.0f}")
        try:
            self._root.after(18, lambda: self._animate_value(target, suffix, steps - 1))
        except Exception:
            self._val_var.set(f"{target:.0f}{suffix}" if suffix else f"{target:.0f}")

    def set_color(self, color: str):
        self._color = color


# ── Main Control Center ───────────────────────────────────────────────────────

class ControlCenter:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NEXUS — Control Center")
        self.root.geometry("1160x740")
        self.root.minsize(900, 600)
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)

        # Window icon — use the NEXUS logo (icon.ico for Windows, icon-192.png fallback)
        _base = (os.path.dirname(sys.executable)
                 if getattr(sys, "frozen", False)
                 else os.path.dirname(os.path.abspath(__file__)))
        try:
            _ico = os.path.join(_base, "static", "icon.ico")
            if os.path.exists(_ico):
                # default= ensures it applies to all future Toplevel windows too
                self.root.iconbitmap(default=_ico)
        except Exception:
            pass
        # PhotoImage fallback (Linux / some Windows configs)
        self._logo_photo: tk.PhotoImage | None = None
        try:
            _png = os.path.join(_base, "static", "icon-192.png")
            if os.path.exists(_png) and _HAS_QR:  # PIL available
                _img = _PILImage.open(_png).resize((32, 32), _PILImage.LANCZOS)
                self._logo_photo = _ImageTk.PhotoImage(_img)
                self.root.iconphoto(True, self._logo_photo)
        except Exception:
            pass

        # Runtime state
        self._start_time: float | None = None
        self._conn_count: int = 0
        self._log_filter  = "ALL"
        self._all_lines: list[tuple[str, str]] = []
        self._search_match_idx = 0
        self._active_users: list[str] = []
        self._conn_history: list[str] = []   # feature: connection history
        self._tray_icon = None
        self._stats_pid: int | None = None
        self._is_restarting: bool = False
        self._sidebar_visible: bool = True
        self._last_log_len: int = 0
        self._log_scroll_locked: bool = False
        self._logo_pulse_state: float = 1.0  # feature: animated logo pulse
        self._logo_canvas: tk.Canvas | None = None
        # Feature extras
        self._broadcast_history: list[str] = []
        self._history_tab_badge: int = 0
        self._unread_joins: int = 0
        self._qr_ngrok_win: tk.Toplevel | None = None  # feature 40: QR auto-refresh
        self._cpu_alert_sent: bool = False
        self._ram_alert_sent: bool = False
        self._cpu_high_since: float | None = None
        self._ram_high_since: float | None = None
        self._last_local_ip: str = ""
        self._log_font_size: int = config.get("LOG_FONT_SIZE", 8)
        self._sidebar_pinned: bool = False
        self._compact_mode: bool = False

        # Feature: window position/size memory
        self._restore_geometry()

        # StringVars
        self.uptime_var    = tk.StringVar(value="—")
        self.conn_var      = tk.StringVar(value="0")
        self.cpu_var       = tk.StringVar(value="—")
        self.ram_var       = tk.StringVar(value="—")
        self.ip_var        = tk.StringVar(value="detecting…")
        self.url_var       = tk.StringVar(value="—")
        self.mode_var      = tk.StringVar(value="")
        self.log_count_var = tk.StringVar(value="0 lines")
        self.statusbar_var = tk.StringVar(value="Ready")

        self._toast = _ToastManager(root)

        self._build_ui()
        self._wire_events()
        self._detect_ip()
        self._start_watchdog()
        self._tick_uptime()
        self._poll_log_buffer()
        # Check for updates 5 seconds after launch (non-blocking)
        self.root.after(5000, self._check_for_updates)
        # Feature 86: smooth window fade-in
        try:
            self.root.attributes("-alpha", 0.0)
            self._fade_in(0)
        except Exception:
            pass
        # Feature 54/55: Windows 11 dark mode + border color
        self._apply_win11_style()
        # Feature 51: restore last tab
        last_tab = config.get("LAST_TAB", "log")
        self.root.after(100, lambda: self._switch_tab(last_tab))

    # ═══════════════════════════════════════════════════════════════════════════
    # UI BUILD
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_titlebar()
        self._build_stat_cards()
        # Feature 20: collapse toggle for stat cards row
        self._build_cards_collapse_btn()

        # ── Body ──────────────────────────────────────────────────────────────
        self._body = tk.Frame(self.root, bg=C["bg"])
        self._body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 0))

        self._sidebar_frame = tk.Frame(self._body, bg=C["bg"])
        self._sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self._build_sidebar(self._sidebar_frame)

        content = tk.Frame(self._body, bg=C["bg"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_log_panel(content)

        self._build_statusbar()
        self._bind_keys()

    # ── Title bar ─────────────────────────────────────────────────────────────

    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=C["surface"], height=52)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=C["surface"])
        left.pack(side=tk.LEFT, padx=16, pady=0, fill=tk.Y)

        # Sidebar toggle
        self._toggle_btn = tk.Button(
            left, text="☰", font=("Segoe UI", 13),
            bg=C["surface"], fg=C["subtext"],
            activebackground=C["hover"], activeforeground=C["text"],
            relief=tk.FLAT, cursor="hand2", bd=0, padx=8,
            command=self._toggle_sidebar)
        self._toggle_btn.pack(side=tk.LEFT, pady=10)

        # NEXUS logo — drawn directly on canvas so it blends with the surface (no box)
        logo_canvas = tk.Canvas(left, width=30, height=30,
                                bg=C["surface"], highlightthickness=0, bd=0)
        logo_canvas.pack(side=tk.LEFT, padx=(8, 6))
        self._draw_logo(logo_canvas, size=30)
        self._logo_canvas = logo_canvas
        self.root.after(100, self._pulse_logo)

        tk.Label(left, text="NEXUS", font=("Segoe UI", 13, "bold"),
                 bg=C["surface"], fg=C["green"]).pack(side=tk.LEFT)
        tk.Label(left, text="Control Center", font=("Segoe UI", 9),
                 bg=C["surface"], fg=C["subtext"]).pack(side=tk.LEFT, padx=(6, 0))

        right = tk.Frame(bar, bg=C["surface"])
        right.pack(side=tk.RIGHT, padx=16, fill=tk.Y)

        # ngrok pill
        self.ngrok_pill = tk.Label(
            right, text="● ngrok off",
            font=("Segoe UI", 8, "bold"),
            bg=C["surface"], fg=C["muted"],
            padx=8, pady=3)
        self.ngrok_pill.pack(side=tk.RIGHT, padx=(8, 0), pady=14)

        # Mode badge
        self.mode_badge = tk.Label(
            right, textvariable=self.mode_var,
            font=("Segoe UI", 8, "bold"),
            bg=C["surface"], fg=C["subtext"],
            padx=8, pady=3)
        self.mode_badge.pack(side=tk.RIGHT, padx=(8, 0), pady=14)

        # Status pill
        self._status_pill = tk.Label(
            right, text="● Stopped",
            font=("Segoe UI", 9, "bold"),
            bg=C["red_dim"], fg=C["red"],
            padx=10, pady=4)
        self._status_pill.pack(side=tk.RIGHT, pady=14)

        # Keyboard shortcuts help button
        tk.Button(
            right, text="?",
            font=("Segoe UI", 10, "bold"),
            bg=C["surface"], fg=C["subtext"],
            activebackground=C["hover"], activeforeground=C["text"],
            relief=tk.FLAT, cursor="hand2", bd=0, padx=8,
            command=self._show_shortcuts).pack(side=tk.RIGHT, pady=14, padx=(0, 4))

    # ── Stat cards row ────────────────────────────────────────────────────────

    @staticmethod
    def _draw_logo(canvas: tk.Canvas, size: int = 30):
        """
        Draw the NEXUS hexagon-network logo directly on a Canvas.
        Scales to any size. No image file — blends with any background.
        """
        import math
        teal   = "#00f5c4"
        white  = "#ffffff"
        # SVG viewBox is 200x200 (ignoring text area), center at 100,96
        # We map that to our canvas size
        vw, vh = 200, 192   # effective viewport
        cx, cy = 100, 96    # center in SVG coords

        def sx(x): return (x / vw) * size
        def sy(y): return (y / vh) * size

        # Outer hexagon vertices (from SVG)
        hex_pts = [
            (100, 18), (168, 57), (168, 135),
            (100, 174), (32, 135), (32, 57),
        ]
        # Connection line endpoints (hub-and-spoke + ring)
        hub = (100, 96)
        spokes = [(100,52),(138,74),(138,118),(100,140),(62,118),(62,74)]
        ring_edges = [
            ((100,52),(138,74)), ((138,74),(138,118)),
            ((138,118),(100,140)), ((100,140),(62,118)),
            ((62,118),(62,74)), ((62,74),(100,52)),
        ]

        # Outer hexagon
        pts_flat = []
        for x, y in hex_pts:
            pts_flat += [sx(x), sy(y)]
        canvas.create_polygon(*pts_flat, outline=teal, fill="", width=1)

        # Spoke lines
        for ex, ey in spokes:
            canvas.create_line(sx(hub[0]), sy(hub[1]),
                               sx(ex), sy(ey),
                               fill=teal, width=1)

        # Ring edges
        for (x1,y1),(x2,y2) in ring_edges:
            canvas.create_line(sx(x1), sy(y1), sx(x2), sy(y2),
                               fill=teal, width=1)

        # Outer nodes
        r = max(1.5, size * 0.055)
        for nx, ny in spokes:
            x, y = sx(nx), sy(ny)
            canvas.create_oval(x-r, y-r, x+r, y+r, fill=teal, outline="")

        # Center node
        cr = max(2, size * 0.075)
        hx, hy = sx(hub[0]), sy(hub[1])
        canvas.create_oval(hx-cr, hy-cr, hx+cr, hy+cr, fill=teal, outline="")
        wr = max(1, size * 0.04)
        canvas.create_oval(hx-wr, hy-wr, hx+wr, hy+wr, fill=white, outline="")

    def _build_stat_cards(self):
        row = tk.Frame(self.root, bg=C["bg"])
        row.pack(fill=tk.X, padx=12, pady=(8, 4))

        # Collapse toggle button (feature 20)
        self._cards_visible = True
        self._cards_row = row

        self._card_uptime = _StatCard(row, "⏱", "UPTIME",       C["blue"],   tooltip="Server uptime since last start")
        self._card_users  = _StatCard(row, "👥", "ACTIVE USERS", C["green"],  tooltip="Currently connected users")
        self._card_cpu    = _StatCard(row, "⚙", "CPU",          C["purple"], tooltip="Server process CPU usage")
        self._card_ram    = _StatCard(row, "💾", "RAM",          C["orange"], tooltip="Server process RAM usage (MB)")

        for card in (self._card_uptime, self._card_users,
                     self._card_cpu, self._card_ram):
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=2)

        # Keep StringVar bindings in sync
        self.uptime_var.trace_add("write", lambda *_: self._card_uptime.set(self.uptime_var.get()))
        self.conn_var.trace_add("write",   lambda *_: self._card_users.set(self.conn_var.get()))
        self.cpu_var.trace_add("write",    lambda *_: self._card_cpu.set(self.cpu_var.get()))
        self.ram_var.trace_add("write",    lambda *_: self._card_ram.set(self.ram_var.get()))

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        outer = tk.Frame(parent, bg=C["surface"], width=220)
        outer.pack(fill=tk.Y)
        outer.pack_propagate(False)
        self._sidebar_inner = outer

        canvas = tk.Canvas(outer, bg=C["surface"], highlightthickness=0, width=220)
        sb = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        pnl = tk.Frame(canvas, bg=C["surface"])
        _win = canvas.create_window((0, 0), window=pnl, anchor="nw")

        def _on_resize(e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            w = canvas.winfo_width()
            if w > 1:
                canvas.itemconfig(_win, width=w)
        pnl.bind("<Configure>", _on_resize)
        canvas.bind("<Configure>", _on_resize)

        def _wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _wheel)
        pnl.bind("<MouseWheel>", _wheel)

        self._build_server_section(pnl)
        self._build_ngrok_section(pnl)
        self._build_quick_section(pnl)
        self._build_config_section(pnl)

        pnl.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _section_header(self, parent, text: str):
        f = tk.Frame(parent, bg=C["surface"])
        f.pack(fill=tk.X, padx=10, pady=(14, 4))
        tk.Frame(f, bg=C["border"], height=1).pack(fill=tk.X, pady=(0, 4))
        tk.Label(f, text=text, font=("Segoe UI", 7, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor=tk.W)

    def _sidebar_btn(self, parent, text, cmd, style="secondary", tip="") -> tk.Button:
        b = _btn(parent, text, cmd, style=style, tip=tip)
        b.configure(bg=C["surface"] if style == "secondary" else b.cget("bg"),
                    activebackground=C["hover"] if style == "secondary" else b.cget("activebackground"))
        b.pack(fill=tk.X, padx=10, pady=2)
        return b

    def _build_server_section(self, pnl):
        self._section_header(pnl, "SERVER")
        self.btn_lan     = self._sidebar_btn(pnl, "▶  Start LAN",    self._start_lan,    "primary", "Ctrl+L")
        self.btn_public  = self._sidebar_btn(pnl, "▶  Start PUBLIC", self._start_public, "blue",    "Ctrl+P")
        self.btn_restart = self._sidebar_btn(pnl, "↺  Restart",      self._restart_server, "orange", "F5")
        self.btn_stop    = self._sidebar_btn(pnl, "■  Stop",         self._stop_all,     "danger",  "Esc")
        # Feature 8: reconnect button (shown when stopped)
        self.btn_reconnect = self._sidebar_btn(pnl, "↺  Reconnect",  self._reconnect_server, "orange", "Start fresh")
        self.btn_restart.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_reconnect.config(state=tk.DISABLED)

    def _build_ngrok_section(self, pnl):
        self._section_header(pnl, "NGROK TUNNEL")
        self.btn_ngrok_start = self._sidebar_btn(pnl, "▶  Start ngrok", self._start_ngrok)
        self.btn_ngrok_stop  = self._sidebar_btn(pnl, "■  Stop ngrok",  self._stop_ngrok, "danger")
        self.btn_ngrok_stop.config(state=tk.DISABLED)

    def _build_quick_section(self, pnl):
        self._section_header(pnl, "QUICK ACTIONS")
        self._sidebar_btn(pnl, "🌐  Open in Browser",     self._open_browser)
        self.btn_copy = self._sidebar_btn(pnl, "📋  Copy Public URL", self._copy_url)
        self.btn_copy.config(state=tk.DISABLED)
        self._sidebar_btn(pnl, "⬛  QR — LAN URL",        self._show_qr_lan)
        self.btn_qr_ngrok_side = self._sidebar_btn(pnl, "⬛  QR — Public URL", self._show_qr_ngrok)
        self.btn_qr_ngrok_side.config(state=tk.DISABLED)
        # Feature 71: ping button
        self._sidebar_btn(pnl, "⚡  Ping Server",         self._ping_server)

        self._section_header(pnl, "BROADCAST")
        self._build_broadcast_panel(pnl)

        self._section_header(pnl, "SETUP")
        self._sidebar_btn(pnl, "⚙  Install Dependencies",   self._install_deps)
        self._sidebar_btn(pnl, "📌  Create Desktop Shortcut", self._create_shortcut)
        # Feature 14: always-on-top toggle
        self._sidebar_btn(pnl, "📌  Always on Top",          self._toggle_always_on_top)
        # Feature 37: compact mode toggle
        self._sidebar_btn(pnl, "⊡  Compact Mode",            self._toggle_compact_mode)
        if _HAS_TRAY:
            self._sidebar_btn(pnl, "🔽  Minimize to Tray", self._minimize_to_tray)

    def _build_broadcast_panel(self, parent):
        """Server message broadcast — sends an announcement to all connected users."""
        f = tk.Frame(parent, bg=C["surface"])
        f.pack(fill=tk.X, padx=10, pady=2)

        self._broadcast_var = tk.StringVar()
        entry_row = tk.Frame(f, bg=C["surface"])
        entry_row.pack(fill=tk.X, pady=(0, 2))

        self._broadcast_entry = tk.Entry(
            entry_row, textvariable=self._broadcast_var,
            bg=C["card"], fg=C["text"],
            insertbackground=C["text"],
            relief=tk.FLAT, font=("Segoe UI", 8),
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["blue"])
        self._broadcast_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._broadcast_entry.bind("<Return>", lambda _: self._send_broadcast())

        # Feature 22: history dropdown button
        tk.Button(entry_row, text="▾", font=("Segoe UI", 8),
                  bg=C["card"], fg=C["subtext"],
                  relief=tk.FLAT, cursor="hand2", padx=4,
                  command=self._show_broadcast_history).pack(side=tk.LEFT, padx=(2, 0))

        # Feature 52: char counter
        self._broadcast_counter = tk.Label(f, text="200", font=("Segoe UI", 7),
                                           bg=C["surface"], fg=C["muted"])
        self._broadcast_counter.pack(anchor=tk.E)
        self._broadcast_var.trace_add("write", self._update_broadcast_counter)

        tk.Button(f, text="📢  Send to All Users",
                  command=self._send_broadcast,
                  bg=C["purple_dim"], fg=C["purple"],
                  font=("Segoe UI", 8, "bold"),
                  relief=tk.FLAT, cursor="hand2",
                  pady=5, activebackground=C["purple_dim"],
                  activeforeground=C["purple"]).pack(fill=tk.X)

    def _build_config_section(self, pnl):
        self._section_header(pnl, "CONFIG")

        def field_with_gen(parent, label, key, show="", width=10, gen=False):
            row = tk.Frame(parent, bg=C["surface"])
            row.pack(fill=tk.X, padx=10, pady=2)
            tk.Label(row, text=label, width=12, anchor=tk.W,
                     bg=C["surface"], fg=C["subtext"],
                     font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(config.get(key, "")))
            e = tk.Entry(row, textvariable=var, show=show,
                         bg=C["card"], fg=C["text"],
                         insertbackground=C["text"],
                         relief=tk.FLAT, font=("Segoe UI", 8),
                         width=width, highlightthickness=1,
                         highlightbackground=C["border"],
                         highlightcolor=C["blue"])
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if gen:
                # Feature 15: password generator button
                tk.Button(row, text="🎲", font=("Segoe UI", 8),
                          bg=C["card"], fg=C["subtext"],
                          relief=tk.FLAT, cursor="hand2", padx=3,
                          command=lambda v=var: v.set(self._gen_password())).pack(side=tk.LEFT, padx=(2, 0))
            var.trace_add("write", lambda *_: self._save_config())
            return var

        def field(parent, label, key, show="", width=10):
            return field_with_gen(parent, label, key, show=show, width=width, gen=False)

        self.srv_pw_var      = field_with_gen(pnl, "Server PW",   "SERVER_PASSWORD", show="*", gen=True)
        self.admin_pw_var    = field_with_gen(pnl, "Admin PW",    "ADMIN_PASSWORD",  show="*", gen=True)
        self.port_var        = field(pnl, "Port",        "PORT",            width=6)
        self.max_restart_var = field(pnl, "Max Restarts","MAX_RESTART_ATTEMPTS", width=4)
        self.ngrok_token_var = field(pnl, "ngrok Token", "NGROK_AUTH_TOKEN", show="*")
        self.port_var.trace_add("write", lambda *_: self._refresh_local_url())

        # URL display row
        url_row = tk.Frame(pnl, bg=C["surface"])
        url_row.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(url_row, text="Local", font=("Segoe UI", 7, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor=tk.W)
        self.ip_lbl = tk.Label(url_row, textvariable=self.ip_var,
                               font=("Segoe UI", 8), bg=C["surface"],
                               fg=C["blue"], cursor="hand2", wraplength=190)
        self.ip_lbl.pack(anchor=tk.W)
        self.ip_lbl.bind("<Button-1>", lambda _: self._open_browser())

        url_row2 = tk.Frame(pnl, bg=C["surface"])
        url_row2.pack(fill=tk.X, padx=10, pady=(4, 2))
        tk.Label(url_row2, text="Public", font=("Segoe UI", 7, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(anchor=tk.W)
        self.url_lbl = tk.Label(url_row2, textvariable=self.url_var,
                                font=("Segoe UI", 8), bg=C["surface"],
                                fg=C["subtext"], cursor="hand2", wraplength=190)
        self.url_lbl.pack(anchor=tk.W)
        self.url_lbl.bind("<Button-1>", lambda _: self._open_browser())

        # Toggles
        self._section_header(pnl, "BEHAVIOUR")
        self.auto_ngrok_var         = tk.BooleanVar(value=config.get("AUTO_NGROK", False))
        self.auto_restart_var       = tk.BooleanVar(value=config.get("AUTO_RESTART_SERVER", False))
        self.auto_browser_lan_var   = tk.BooleanVar(value=config.get("AUTO_OPEN_BROWSER_LAN", True))
        self.auto_browser_ngrok_var = tk.BooleanVar(value=config.get("AUTO_OPEN_BROWSER_NGROK", True))

        for var, label in (
            (self.auto_ngrok_var,         "Auto-start ngrok (PUBLIC)"),
            (self.auto_restart_var,        "Auto-restart on crash"),
            (self.auto_browser_lan_var,    "Open browser on LAN start"),
            (self.auto_browser_ngrok_var,  "Open browser on ngrok ready"),
        ):
            tk.Checkbutton(pnl, text=label, variable=var,
                           bg=C["surface"], fg=C["text"],
                           selectcolor=C["bg"],
                           activebackground=C["surface"],
                           activeforeground=C["text"],
                           font=("Segoe UI", 8),
                           command=self._save_config).pack(anchor=tk.W, padx=10, pady=1)

        # Feature 18: auto-copy public URL toggle
        self.auto_copy_url_var = tk.BooleanVar(value=config.get("AUTO_COPY_URL", False))
        tk.Checkbutton(pnl, text="Auto-copy public URL",
                       variable=self.auto_copy_url_var,
                       bg=C["surface"], fg=C["text"],
                       selectcolor=C["bg"],
                       activebackground=C["surface"],
                       activeforeground=C["text"],
                       font=("Segoe UI", 8),
                       command=self._save_config).pack(anchor=tk.W, padx=10, pady=1)

        # Feature 9: Config import/export buttons
        self._section_header(pnl, "CONFIG FILE")
        cfg_row = tk.Frame(pnl, bg=C["surface"])
        cfg_row.pack(fill=tk.X, padx=10, pady=2)
        tk.Button(cfg_row, text="Export Config", command=self._export_config,
                  bg=C["border"], fg=C["text"], font=("Segoe UI", 8),
                  relief=tk.FLAT, cursor="hand2", padx=6, pady=3).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(cfg_row, text="Import Config", command=self._import_config,
                  bg=C["border"], fg=C["text"], font=("Segoe UI", 8),
                  relief=tk.FLAT, cursor="hand2", padx=6, pady=3).pack(side=tk.LEFT)

        tk.Frame(pnl, bg=C["surface"], height=16).pack()

    # ── Log panel ─────────────────────────────────────────────────────────────

    def _build_log_panel(self, parent):
        # ── URL bar above log ──────────────────────────────────────────────
        url_bar = tk.Frame(parent, bg=C["surface"], height=36)
        url_bar.pack(fill=tk.X, pady=(0, 6))
        url_bar.pack_propagate(False)

        tk.Label(url_bar, text="LAN:", font=("Segoe UI", 8, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(side=tk.LEFT, padx=(10, 4), pady=8)
        self._lan_url_lbl = tk.Label(url_bar, textvariable=self.ip_var,
                                     font=("Segoe UI", 8), bg=C["surface"],
                                     fg=C["blue"], cursor="hand2")
        self._lan_url_lbl.pack(side=tk.LEFT, pady=8)
        self._lan_url_lbl.bind("<Button-1>", lambda _: self._open_browser())

        self._btn_qr_lan = tk.Button(url_bar, text="QR", font=("Segoe UI", 7),
                                     bg=C["border"], fg=C["text"], relief=tk.FLAT,
                                     cursor="hand2", padx=5, pady=1,
                                     command=self._show_qr_lan)
        self._btn_qr_lan.pack(side=tk.LEFT, padx=(4, 16), pady=8)

        tk.Label(url_bar, text="Public:", font=("Segoe UI", 8, "bold"),
                 bg=C["surface"], fg=C["muted"]).pack(side=tk.LEFT, padx=(0, 4), pady=8)
        self._pub_url_lbl = tk.Label(url_bar, textvariable=self.url_var,
                                     font=("Segoe UI", 8), bg=C["surface"],
                                     fg=C["subtext"], cursor="hand2")
        self._pub_url_lbl.pack(side=tk.LEFT, pady=8)
        self._pub_url_lbl.bind("<Button-1>", lambda _: self._open_browser())

        self._btn_qr_ngrok = tk.Button(url_bar, text="QR", font=("Segoe UI", 7),
                                       bg=C["border"], fg=C["text"], relief=tk.FLAT,
                                       cursor="hand2", padx=5, pady=1,
                                       state=tk.DISABLED,
                                       command=self._show_qr_ngrok)
        self._btn_qr_ngrok.pack(side=tk.LEFT, padx=(4, 0), pady=8)

        # ── Tabbed panel: Log + Users ──────────────────────────────────────
        tab_bar = tk.Frame(parent, bg=C["bg"])
        tab_bar.pack(fill=tk.X)

        self._tab_content = tk.Frame(parent, bg=C["card"])
        self._tab_content.pack(fill=tk.BOTH, expand=True)

        self._active_tab = tk.StringVar(value="log")
        self._tab_frames: dict[str, tk.Frame] = {}

        def make_tab(key, label):
            btn = tk.Button(tab_bar, text=label,
                            font=("Segoe UI", 8, "bold"),
                            bg=C["card"], fg=C["subtext"],
                            activebackground=C["card"],
                            activeforeground=C["text"],
                            relief=tk.FLAT, cursor="hand2",
                            padx=16, pady=6, bd=0,
                            command=lambda k=key: self._switch_tab(k))
            btn.pack(side=tk.LEFT)
            return btn

        self._tab_btns = {
            "log":     make_tab("log",     "📋  Server Log"),
            "users":   make_tab("users",   "👥  Active Users"),
            "history": make_tab("history", "🕐  History"),
            "rooms":   make_tab("rooms",   "🏠  Rooms"),
        }

        self._build_log_tab()
        self._build_users_tab()
        self._build_history_tab()
        self._build_rooms_tab()
        self._switch_tab("log")

    def _switch_tab(self, key: str):
        self._active_tab.set(key)
        for k, f in self._tab_frames.items():
            if k == key:
                f.pack(fill=tk.BOTH, expand=True)
            else:
                f.pack_forget()
        for k, b in self._tab_btns.items():
            b.config(
                bg=C["surface"] if k == key else C["card"],
                fg=C["text"]    if k == key else C["subtext"],
            )
        # Feature 51: save last tab
        config["LAST_TAB"] = key
        save_config_debounced(config)
        # Clear badge when switching to history
        if key == "history":
            self._history_tab_badge = 0
            self._tab_btns["history"].config(text="🕐  History")

    def _build_log_tab(self):
        frame = tk.Frame(self._tab_content, bg=C["card"])
        self._tab_frames["log"] = frame

        # Log toolbar
        toolbar = tk.Frame(frame, bg=C["card"])
        toolbar.pack(fill=tk.X, padx=8, pady=(6, 4))

        tk.Label(toolbar, textvariable=self.log_count_var,
                 font=("Segoe UI", 7), bg=C["card"],
                 fg=C["muted"]).pack(side=tk.LEFT, padx=(0, 12))

        # Filter buttons
        self._filter_btns: dict[str, tk.Button] = {}
        for level in ("ALL", "INFO", "WARN", "ERROR"):
            b = tk.Button(toolbar, text=level,
                          font=("Segoe UI", 7, "bold"),
                          bg=C["border"], fg=C["subtext"],
                          activebackground=C["hover"],
                          relief=tk.FLAT, cursor="hand2",
                          padx=8, pady=2,
                          command=lambda l=level: self._set_filter(l))
            b.pack(side=tk.LEFT, padx=1)
            self._filter_btns[level] = b

        tk.Button(toolbar, text="Save", command=self._save_log,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  cursor="hand2", padx=8, pady=2).pack(side=tk.RIGHT, padx=(2, 0))
        # Feature 7: CSV export button
        tk.Button(toolbar, text="CSV", command=self._save_log_csv,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  cursor="hand2", padx=8, pady=2).pack(side=tk.RIGHT, padx=(2, 0))
        # Feature 4: Copy All button
        tk.Button(toolbar, text="Copy All", command=self._copy_log_to_clipboard,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  cursor="hand2", padx=8, pady=2).pack(side=tk.RIGHT, padx=(2, 0))
        tk.Button(toolbar, text="Clear", command=self._clear_log,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  cursor="hand2", padx=8, pady=2).pack(side=tk.RIGHT)
        # Feature 32: font size controls
        tk.Button(toolbar, text="A+", command=self._log_font_increase,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  cursor="hand2", padx=6, pady=2).pack(side=tk.RIGHT, padx=(2, 0))
        tk.Button(toolbar, text="A-", command=self._log_font_decrease,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  cursor="hand2", padx=6, pady=2).pack(side=tk.RIGHT, padx=(2, 0))

        # Word-wrap toggle
        self._wrap_var = tk.BooleanVar(value=True)
        self._wrap_btn = tk.Button(
            toolbar, text="⇌ Wrap",
            font=("Segoe UI", 7, "bold"),
            bg=C["border"], fg=C["subtext"],
            activebackground=C["hover"],
            relief=tk.FLAT, cursor="hand2",
            padx=8, pady=2,
            command=self._toggle_wrap)
        self._wrap_btn.pack(side=tk.RIGHT, padx=(2, 2))

        # Scroll-lock toggle
        self._scroll_lock_btn = tk.Button(
            toolbar, text="⏸ Pause",
            font=("Segoe UI", 7, "bold"),
            bg=C["border"], fg=C["subtext"],
            activebackground=C["hover"],
            relief=tk.FLAT, cursor="hand2",
            padx=8, pady=2,
            command=self._toggle_scroll_lock)
        self._scroll_lock_btn.pack(side=tk.RIGHT, padx=(2, 8))

        # Log box
        self.log_box = scrolledtext.ScrolledText(
            frame, state=tk.DISABLED,
            bg=C["bg"], fg=C["text"],
            font=("Consolas", self._log_font_size), relief=tk.FLAT,
            wrap=tk.WORD, insertbackground=C["text"],
            selectbackground=C["border"],
            highlightthickness=0)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))
        # Feature 13: double-click to copy line
        self.log_box.bind("<Double-Button-1>", self._log_double_click_copy)

        for tag, color in (
            ("green",  C["green"]),
            ("red",    C["red"]),
            ("orange", C["orange"]),
            ("blue",   C["blue"]),
            ("purple", C["purple"]),
        ):
            self.log_box.tag_config(tag, foreground=color)

        self._set_filter("ALL")

        # Search bar (hidden until Ctrl+F)
        self._search_frame = tk.Frame(frame, bg=C["card"])
        self._search_var = tk.StringVar()

        tk.Label(self._search_frame, text="Find:", bg=C["card"],
                 fg=C["subtext"], font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(8, 4))
        self._search_entry = tk.Entry(
            self._search_frame, textvariable=self._search_var,
            bg=C["bg"], fg=C["text"], insertbackground=C["text"],
            relief=tk.FLAT, font=("Segoe UI", 8), width=26,
            highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["blue"])
        self._search_entry.pack(side=tk.LEFT)
        self._search_entry.bind("<Return>", lambda _: self._search_next())
        self._search_entry.bind("<Escape>", lambda _: self._hide_search())

        for label, cmd in (("Prev", self._search_prev), ("Next", self._search_next)):
            tk.Button(self._search_frame, text=label, command=cmd,
                      bg=C["border"], fg=C["text"], relief=tk.FLAT,
                      font=("Segoe UI", 7), padx=6, pady=2).pack(side=tk.LEFT, padx=1)
        tk.Button(self._search_frame, text="✕", command=self._hide_search,
                  bg=C["border"], fg=C["text"], relief=tk.FLAT,
                  font=("Segoe UI", 7), padx=6, pady=2).pack(side=tk.LEFT, padx=(1, 8))

    def _build_users_tab(self):
        frame = tk.Frame(self._tab_content, bg=C["card"])
        self._tab_frames["users"] = frame

        hdr = tk.Frame(frame, bg=C["card"])
        hdr.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(hdr, text="Connected Users", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        self._users_count_lbl = tk.Label(hdr, text="0 online",
                                         font=("Segoe UI", 8),
                                         bg=C["card"], fg=C["subtext"])
        self._users_count_lbl.pack(side=tk.RIGHT)

        self._users_box = tk.Listbox(
            frame, bg=C["bg"], fg=C["text"],
            font=("Segoe UI", 10), relief=tk.FLAT,
            selectbackground=C["border"], activestyle="none",
            highlightthickness=0, borderwidth=0)
        self._users_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Feature 5: right-click context menu for kick
        self._users_ctx_menu = tk.Menu(self._users_box, tearoff=0,
                                       bg=C["card"], fg=C["text"],
                                       activebackground=C["hover"],
                                       activeforeground=C["text"],
                                       relief=tk.FLAT)
        self._users_ctx_menu.add_command(label="Kick User", command=self._kick_selected_user)
        self._users_box.bind("<Button-3>", self._show_users_context_menu)

    def _build_history_tab(self):
        """Connection history — timestamped join/leave events."""
        frame = tk.Frame(self._tab_content, bg=C["card"])
        self._tab_frames["history"] = frame

        hdr = tk.Frame(frame, bg=C["card"])
        hdr.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(hdr, text="Connection History", font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Button(hdr, text="Clear", command=self._clear_history,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 7), relief=tk.FLAT,
                  cursor="hand2", padx=6, pady=2).pack(side=tk.RIGHT)

        self._history_box = scrolledtext.ScrolledText(
            frame, state=tk.DISABLED,
            bg=C["bg"], fg=C["text"],
            font=("Consolas", 8), relief=tk.FLAT,
            wrap=tk.WORD, highlightthickness=0)
        self._history_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._history_box.tag_config("join", foreground=C["green"])
        self._history_box.tag_config("leave", foreground=C["orange"])

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=C["surface"], height=28)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        sb.pack_propagate(False)
        # Feature 38: health pulse dot
        self._health_dot = tk.Label(sb, text="●", font=("Segoe UI", 9),
                                    bg=C["surface"], fg=C["muted"])
        self._health_dot.pack(side=tk.LEFT, padx=(8, 2), pady=4)
        self._pulse_health_dot()

        lbl = tk.Label(sb, textvariable=self.statusbar_var,
                 font=("Segoe UI", 7), bg=C["surface"],
                 fg=C["muted"], anchor=tk.W,
                 wraplength=1100, justify=tk.LEFT, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(2, 10), pady=4)
        # Feature 24: click status bar to copy
        lbl.bind("<Button-1>", lambda _: self._copy_status_to_clipboard())

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def _bind_keys(self):
        self.root.bind("<F5>",        lambda _: self._restart_server())
        self.root.bind("<Control-l>", lambda _: self._start_lan())
        self.root.bind("<Control-L>", lambda _: self._start_lan())
        self.root.bind("<Control-p>", lambda _: self._start_public())
        self.root.bind("<Control-P>", lambda _: self._start_public())
        self.root.bind("<Escape>",    lambda _: self._stop_all_confirm())
        self.root.bind("<Control-f>", lambda _: self._show_search())
        self.root.bind("<Control-F>", lambda _: self._show_search())
        # Feature 11: Ctrl+B focuses broadcast entry
        self.root.bind("<Control-b>", lambda _: self._focus_broadcast())
        self.root.bind("<Control-B>", lambda _: self._focus_broadcast())
        # Feature 34: Ctrl+Q opens quick settings panel
        self.root.bind("<Control-q>", lambda _: self._show_quick_settings())
        self.root.bind("<Control-Q>", lambda _: self._show_quick_settings())
        # Feature 66: Ctrl+Enter also sends broadcast
        self.root.bind("<Control-Return>", lambda _: self._send_broadcast())

    # ── Sidebar toggle ────────────────────────────────────────────────────────

    def _toggle_sidebar(self):
        if self._sidebar_visible:
            self._sidebar_frame.pack_forget()
            self._sidebar_visible = False
            self._toggle_btn.config(fg=C["blue"])
        else:
            # Re-pack before the content frame (first child of _body)
            children = self._body.winfo_children()
            if children:
                self._sidebar_frame.pack(side=tk.LEFT, fill=tk.Y,
                                         padx=(0, 8),
                                         before=children[0])
            else:
                self._sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
            self._sidebar_visible = True
            self._toggle_btn.config(fg=C["subtext"])

    # ═══════════════════════════════════════════════════════════════════════════
    # UPTIME TICKER
    # ═══════════════════════════════════════════════════════════════════════════

    def _tick_uptime(self):
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            h, rem = divmod(elapsed, 3600)
            m, s   = divmod(rem, 60)
            uptime = f"{h:02d}:{m:02d}:{s:02d}"
            self.uptime_var.set(uptime)
            mode = sys_state.get("mode") or ""
            self.root.title(f"NEXUS — Control Center  |  ▶ {mode}  {uptime}")
        else:
            self.uptime_var.set("—")
            self.root.title("NEXUS — Control Center")
        self.root.after(1000, self._tick_uptime)

    # ═══════════════════════════════════════════════════════════════════════════
    # LOG FILTER
    # ═══════════════════════════════════════════════════════════════════════════

    def _set_filter(self, level: str):
        self._log_filter = level
        for lv, b in self._filter_btns.items():
            active = lv == level
            b.config(
                bg=C["blue"]    if active else C["border"],
                fg=C["btn_fg"]  if active else C["subtext"],
            )
        self._redraw_log()

    def _line_passes_filter(self, text: str, tag: str) -> bool:
        if self._log_filter == "ALL":
            return True
        if self._log_filter == "ERROR":
            return tag == "red" or bool(_LEVEL_ERROR.search(text))
        if self._log_filter == "WARN":
            return tag in ("red", "orange") or bool(_LEVEL_WARN.search(text))
        return not re.search(r'"(GET|POST|HEAD) /', text)

    def _redraw_log(self):
        if not hasattr(self, "log_box"):
            return
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        for text, tag in self._all_lines:
            if self._line_passes_filter(text, tag):
                self.log_box.insert(tk.END, text + "\n", tag)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ═══════════════════════════════════════════════════════════════════════════
    # LOG SEARCH
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_search(self):
        self._search_frame.pack(fill=tk.X, padx=6, pady=(2, 4))
        self._search_entry.focus_set()

    def _hide_search(self):
        self._search_frame.pack_forget()
        self.log_box.tag_remove("found", "1.0", tk.END)

    # ── Scroll lock ───────────────────────────────────────────────────────────

    def _toggle_scroll_lock(self):
        self._log_scroll_locked = not self._log_scroll_locked
        if self._log_scroll_locked:
            self._scroll_lock_btn.config(
                text="▶ Resume",
                bg=C["orange_dim"], fg=C["orange"])
        else:
            self._scroll_lock_btn.config(
                text="⏸ Pause",
                bg=C["border"], fg=C["subtext"])
            # Jump to bottom when resuming
            self.log_box.see(tk.END)

    # ── Keyboard shortcuts popup ──────────────────────────────────────────────

    def _show_shortcuts(self):
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Keyboard Shortcuts",
                 font=("Segoe UI", 12, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(padx=24, pady=(20, 4))
        tk.Label(win, text="All shortcuts work when the main window is focused.",
                 font=("Segoe UI", 8),
                 bg=C["bg"], fg=C["subtext"]).pack(padx=24, pady=(0, 12))

        shortcuts = [
            ("SERVER",       None),
            ("Ctrl + L",     "Start server in LAN mode"),
            ("Ctrl + P",     "Start server in PUBLIC mode"),
            ("F5",           "Restart server (same mode)"),
            ("Esc",          "Stop server + ngrok (with confirm)"),
            ("LOG",          None),
            ("Ctrl + F",     "Open log search bar"),
            ("Enter",        "Find next match (search bar)"),
            ("Escape",       "Close search bar"),
            ("WINDOW",       None),
            ("?  button",    "Show this help popup"),
            ("☰  button",    "Toggle sidebar visibility"),
        ]

        card = tk.Frame(win, bg=C["card"], padx=20, pady=12)
        card.pack(fill=tk.X, padx=20, pady=(0, 8))

        for key, desc in shortcuts:
            if desc is None:
                # Section header
                tk.Label(card, text=key,
                         font=("Segoe UI", 7, "bold"),
                         bg=C["card"], fg=C["muted"],
                         anchor=tk.W).pack(fill=tk.X, pady=(10, 2))
                tk.Frame(card, bg=C["border"], height=1).pack(fill=tk.X, pady=(0, 4))
            else:
                row = tk.Frame(card, bg=C["card"])
                row.pack(fill=tk.X, pady=2)
                tk.Label(row, text=key, width=14, anchor=tk.W,
                         font=("Consolas", 9, "bold"),
                         bg=C["card"], fg=C["blue"]).pack(side=tk.LEFT)
                tk.Label(row, text=desc, anchor=tk.W,
                         font=("Segoe UI", 9),
                         bg=C["card"], fg=C["text"]).pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(win, text="Close", command=win.destroy,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 9), relief=tk.FLAT,
                  cursor="hand2", padx=20, pady=6).pack(pady=(4, 20))

    def _search_next(self):
        self._do_search(forward=True)

    def _search_prev(self):
        self._do_search(forward=False)

    def _do_search(self, forward: bool):
        term = self._search_var.get()
        if not term:
            return
        self.log_box.tag_remove("found", "1.0", tk.END)
        self.log_box.tag_config("found", background=C["orange"], foreground=C["bg"])
        start = "1.0"
        positions = []
        while True:
            pos = self.log_box.search(term, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(term)}c"
            positions.append((pos, end))
            start = end
        if not positions:
            return
        if forward:
            self._search_match_idx = (self._search_match_idx + 1) % len(positions)
        else:
            self._search_match_idx = (self._search_match_idx - 1) % len(positions)
        pos, end = positions[self._search_match_idx]
        self.log_box.tag_add("found", pos, end)
        self.log_box.see(pos)

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE / CLEAR LOG
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_log(self):
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"lanchat_log_{ts}.txt",
        )
        if not path:
            return
        try:
            mode    = sys_state.get("mode") or "—"
            port    = config.get("PORT", 5000)
            ip      = sys_state.get("local_ip") or "—"
            pub_url = sys_state.get("public_url") or "—"
            uptime  = self.uptime_var.get() or "—"
            header  = (
                f"NEXUS Control Center — Server Log Export\n"
                f"{'─' * 50}\n"
                f"Exported : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Mode     : {mode}\n"
                f"Local URL: http://{ip}:{port}\n"
                f"Public   : {pub_url}\n"
                f"Uptime   : {uptime}\n"
                f"{'─' * 50}\n\n"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(header)
                f.write(self.log_box.get("1.0", tk.END))
            self._toast.show(f"Log saved: {os.path.basename(path)}", "success")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def _clear_log(self):
        self._all_lines.clear()
        ui_state.clear_log()
        self._last_log_len = 0
        self.log_count_var.set("0 lines")
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)

    def _write_log(self, msg: str, tag: str = ""):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, msg.rstrip() + "\n", tag)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT WIRING
    # ═══════════════════════════════════════════════════════════════════════════

    def _wire_events(self):
        def on_main(fn):
            def _w(v):
                self.root.after(0, lambda val=v: fn(val))
            return _w

        sys_state.on("server_running", on_main(self._on_server_running))
        sys_state.on("ngrok_running",  on_main(self._on_ngrok_running))
        sys_state.on("public_url",     on_main(self._on_public_url))
        sys_state.on("mode",           on_main(self._on_mode_change))
        ui_state.on("log",             on_main(self._on_log_line))

    def _poll_log_buffer(self):
        try:
            buf = ui_state.get_log_buffer()
            new_lines = buf[self._last_log_len:]
            if new_lines:
                self.log_box.config(state=tk.NORMAL)
                for line in new_lines:
                    if not line:
                        continue
                    line = _strip_ansi(line)
                    ts   = datetime.datetime.now().strftime("%H:%M:%S")
                    text = f"[{ts}] {line.rstrip()}"
                    tag  = _tag_for(line)
                    self._track_connections(line)
                    self._all_lines.append((text, tag))
                    if self._line_passes_filter(text, tag):
                        self.log_box.insert(tk.END, text + "\n", tag)
                    ll = line.lower()
                    if tag in ("red", "orange") or "error" in ll or "warn" in ll:
                        self._set_status(line.rstrip())
                if not self._log_scroll_locked:
                    self.log_box.see(tk.END)
                self.log_box.config(state=tk.DISABLED)
                self._last_log_len = len(buf)
                self.log_count_var.set(f"{len(self._all_lines)} lines")
                # Feature 47: log auto-rotate when > 2000 lines
                if len(self._all_lines) > 2000:
                    self._rotate_log()
        except Exception as e:
            try:
                self.log_box.config(state=tk.NORMAL)
                self.log_box.insert(tk.END, f"[POLL ERROR] {e}\n", "red")
                self.log_box.config(state=tk.DISABLED)
            except Exception:
                pass
        self.root.after(250, self._poll_log_buffer)

    def _on_log_line(self, line: str | None):
        pass  # guaranteed fallback is _poll_log_buffer

    def _on_server_running(self, running: bool):
        if running:
            self._start_time = time.time()
            self._conn_count = 0
            self.conn_var.set("0")
            self._status_pill.config(text="● Running",
                                     bg=C["green_dim"], fg=C["green"])
            self.btn_stop.config(state=tk.NORMAL)
            self.btn_restart.config(state=tk.NORMAL)
            self.btn_reconnect.config(state=tk.DISABLED)
            self.btn_lan.config(state=tk.DISABLED)
            self.btn_public.config(state=tk.DISABLED)
            mode = sys_state.get("mode") or ""
            self._update_mode_badge(mode)
            self._stats_pid = sys_state.get("server_pid")
            self._start_stats_poll()
            if not self._is_restarting:
                if mode == "LAN" and config.get("AUTO_OPEN_BROWSER_LAN", True):
                    self.root.after(1500, self._open_browser)
                elif mode == "PUBLIC" and not config.get("AUTO_NGROK", False):
                    if config.get("AUTO_OPEN_BROWSER_LAN", True):
                        self.root.after(1500, self._open_browser)
            self._is_restarting = False
            self._set_status("Server started")
            self._toast.show("Server is running", "success")
            self.log_box.config(state=tk.NORMAL)
            self.log_box.insert(
                tk.END,
                f"[{datetime.datetime.now().strftime('%H:%M:%S')}]"
                f" ── Server started (PID {sys_state.get('server_pid')}) ──\n",
                "green")
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
            self.log_count_var.set("1 lines")
            # Feature 3: save last used mode
            if mode:
                config["LAST_MODE"] = mode
                save_config_debounced(config)
        else:
            was_running = self._start_time is not None
            # Feature 39: auto-save log on crash
            if was_running:
                self._auto_save_crash_log()
            self._start_time = None
            self.uptime_var.set("—")
            self.conn_var.set("0")
            self.cpu_var.set("—")
            self.ram_var.set("—")
            self._stats_pid = None
            self._status_pill.config(text="● Stopped",
                                     bg=C["red_dim"], fg=C["red"])
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_restart.config(state=tk.DISABLED)
            self.btn_reconnect.config(state=tk.NORMAL)
            self.btn_lan.config(state=tk.NORMAL)
            self.btn_public.config(state=tk.NORMAL)
            self.mode_var.set("")
            self._active_users.clear()
            self._refresh_users_box()
            self._set_status("Server stopped")
            self._toast.show("Server stopped", "warning")
            # Feature 6: error sound on stop
            self._play_sound("error")

    def _on_ngrok_running(self, running: bool):
        self.ngrok_pill.config(
            text="● ngrok on" if running else "● ngrok off",
            fg=C["green"] if running else C["muted"])
        self.btn_ngrok_start.config(state=tk.DISABLED if running else tk.NORMAL)
        self.btn_ngrok_stop.config(state=tk.NORMAL if running else tk.DISABLED)
        if not running:
            self.btn_copy.config(state=tk.DISABLED)
            self._btn_qr_ngrok.config(state=tk.DISABLED)
            self.btn_qr_ngrok_side.config(state=tk.DISABLED)
        self._set_status("ngrok " + ("started" if running else "stopped"))
        if running:
            self._toast.show("ngrok tunnel started", "info")

    def _on_public_url(self, url: str | None):
        self.url_var.set(url if url else "—")
        self._pub_url_lbl.config(fg=C["blue"] if url else C["subtext"])
        self.url_lbl.config(fg=C["blue"] if url else C["subtext"])
        ready = bool(url and api.is_ngrok_ready())
        self.btn_copy.config(state=tk.NORMAL if ready else tk.DISABLED)
        self._btn_qr_ngrok.config(state=tk.NORMAL if ready else tk.DISABLED)
        self.btn_qr_ngrok_side.config(state=tk.NORMAL if ready else tk.DISABLED)
        if url:
            self._set_status(f"Public URL ready: {url}")
            self._toast.show("Public URL ready", "success")
            if config.get("AUTO_OPEN_BROWSER_NGROK", True):
                self.root.after(0, lambda: webbrowser.open(url))
            # Feature 18: auto-copy public URL
            if config.get("AUTO_COPY_URL", False):
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(url)
                except Exception:
                    pass
            # Feature 40: update open QR window
            self._refresh_qr_ngrok_window(url)

    def _on_mode_change(self, mode: str | None):
        self._update_mode_badge(mode)

    def _update_mode_badge(self, mode: str | None):
        if mode == "LAN":
            self.mode_var.set("[ LAN ]")
            self.mode_badge.config(fg=C["green"])
        elif mode == "PUBLIC":
            self.mode_var.set("[ PUBLIC ]")
            self.mode_badge.config(fg=C["blue"])
        else:
            self.mode_var.set("")
            self.mode_badge.config(fg=C["subtext"])
        # Feature 26/76: flash mode badge background briefly
        if mode:
            flash_color = C["green_dim"] if mode == "LAN" else C["blue_dim"]
            self.mode_badge.config(bg=flash_color)
            self.root.after(400, lambda: self.mode_badge.config(bg=C["surface"]))
            # Animate font scale up then back
            self._animate_mode_badge_font(14, 8)

    # ═══════════════════════════════════════════════════════════════════════════
    # CONNECTION TRACKING
    # ═══════════════════════════════════════════════════════════════════════════

    def _track_connections(self, line: str):
        ll = line.lower()
        session_m = re.search(r'actor=(\S+)\s+handler=(join|disconnect)', line, re.I)
        if session_m:
            name    = session_m.group(1).strip("'\"")
            handler = session_m.group(2).lower()
            if handler == 'join':
                self._conn_count = max(0, self._conn_count + 1)
                if name and name not in self._active_users:
                    self._active_users.append(name)
                self._refresh_users_box()
                self._log_history(f"{name} joined", "join")
                self._on_user_join(name)
            elif handler == 'disconnect':
                self._conn_count = max(0, self._conn_count - 1)
                if name in self._active_users:
                    self._active_users.remove(name)
                self._refresh_users_box()
                self._log_history(f"{name} left", "leave")
            self.conn_var.set(str(self._conn_count))
            return

        join_m  = re.search(r'(\S+)\s+joined', line, re.I)
        leave_m = re.search(r'(\S+)\s+(?:left|disconnected)', line, re.I)
        if join_m and "ngrok" not in ll:
            name = join_m.group(1).strip("'\"")
            self._conn_count = max(0, self._conn_count + 1)
            if name and name not in self._active_users:
                self._active_users.append(name)
            self._refresh_users_box()
            self._log_history(f"{name} joined", "join")
            self._on_user_join(name)
        elif leave_m:
            name = leave_m.group(1).strip("'\"")
            self._conn_count = max(0, self._conn_count - 1)
            if name in self._active_users:
                self._active_users.remove(name)
            self._refresh_users_box()
            self._log_history(f"{name} left", "leave")
        self.conn_var.set(str(self._conn_count))

    def _refresh_users_box(self):
        if not hasattr(self, "_users_box"):
            return
        self._users_box.delete(0, tk.END)
        for u in self._active_users:
            self._users_box.insert(tk.END, f"  ●  {u}")
        count = len(self._active_users) or self._conn_count
        self._users_count_lbl.config(text=f"{count} online")
        self.conn_var.set(str(count))

    # ═══════════════════════════════════════════════════════════════════════════
    # IP / URL DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_ip(self):
        def _run():
            ip = _get_local_ip()
            sys_state.set("local_ip", ip)
            self.root.after(0, self._refresh_local_url)
        threading.Thread(target=_run, daemon=True).start()

    def _refresh_local_url(self):
        ip = sys_state.get("local_ip") or "detecting…"
        try:
            port = int(self.port_var.get())
        except (ValueError, AttributeError):
            port = config.get("PORT", 5000)
        self.ip_var.set(f"http://{ip}:{port}")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIG SAVE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_config(self):
        config["SERVER_PASSWORD"]         = self.srv_pw_var.get()
        config["ADMIN_PASSWORD"]          = self.admin_pw_var.get()
        config["NGROK_AUTH_TOKEN"]        = self.ngrok_token_var.get()
        config["AUTO_NGROK"]              = self.auto_ngrok_var.get()
        config["AUTO_RESTART_SERVER"]     = self.auto_restart_var.get()
        config["AUTO_OPEN_BROWSER_LAN"]   = self.auto_browser_lan_var.get()
        config["AUTO_OPEN_BROWSER_NGROK"] = self.auto_browser_ngrok_var.get()
        config["AUTO_OPEN_BROWSER"] = (
            self.auto_browser_lan_var.get() or self.auto_browser_ngrok_var.get()
        )
        # Feature 18: auto-copy URL
        if hasattr(self, "auto_copy_url_var"):
            config["AUTO_COPY_URL"] = self.auto_copy_url_var.get()
        # Feature 50: persist log font size
        config["LOG_FONT_SIZE"] = self._log_font_size
        try:
            config["PORT"] = int(self.port_var.get())
        except ValueError:
            pass
        try:
            config["MAX_RESTART_ATTEMPTS"] = int(self.max_restart_var.get())
        except ValueError:
            pass
        save_config_debounced(config)

    # ═══════════════════════════════════════════════════════════════════════════
    # WATCHDOG
    # ═══════════════════════════════════════════════════════════════════════════

    def _start_watchdog(self):
        def _loop():
            while True:
                time.sleep(2)
                ctrl.sync_state()
                # Feature 62: detect local IP change
                try:
                    new_ip = _get_local_ip()
                    if self._last_local_ip and new_ip != self._last_local_ip and api.is_server_running():
                        self._last_local_ip = new_ip
                        sys_state.set("local_ip", new_ip)
                        mode = sys_state.get("mode") or "LAN"
                        self.root.after(0, lambda: self._toast.show(
                            f"IP changed to {new_ip} — restarting server", "warning"))
                        self.root.after(500, self._restart_server)
                    elif not self._last_local_ip:
                        self._last_local_ip = new_ip
                except Exception:
                    pass
        threading.Thread(target=_loop, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # SERVICE CALLS
    # ═══════════════════════════════════════════════════════════════════════════

    def _start_lan(self):
        # Feature 16: port conflict detection
        if self._check_port_conflict():
            return
        self._status_pill.config(text="◌ Starting…",
                                 bg=C["orange_dim"], fg=C["orange"])
        result = api.start_server("LAN")
        if result.ok:
            ui_state.append_log(f"LAN server started (PID {result.data['pid']})")
        else:
            ui_state.append_log(f"ERROR: {result.message}")
            self._set_status(f"Error: {result.message}")
            self._toast.show(result.message, "error")
            self._status_pill.config(text="● Stopped",
                                     bg=C["red_dim"], fg=C["red"])

    def _start_public(self):
        # Enforce server password — PUBLIC mode without a password blocks everyone
        pw = self.srv_pw_var.get().strip()
        if not pw:
            messagebox.showwarning(
                "Server Password Required",
                "PUBLIC mode requires a server password.\n\n"
                "Set one in the Config panel (Server PW field) before starting."
            )
            self._toast.show("Set a server password first", "warning")
            return
        # Feature 16: port conflict detection
        if self._check_port_conflict():
            return

        self._status_pill.config(text="◌ Starting…",
                                 bg=C["orange_dim"], fg=C["orange"])
        result = api.start_server("PUBLIC")
        if result.ok:
            ui_state.append_log(f"PUBLIC server started (PID {result.data['pid']})")
            ui_state.append_log(
                "🔒  Security: TRUSTED_PROXY=true, rate limits tightened, "
                "upload cap 10 MB, SVG blocked, HSTS enabled"
            )
        else:
            ui_state.append_log(f"ERROR: {result.message}")
            self._set_status(f"Error: {result.message}")
            self._toast.show(result.message, "error")
            self._status_pill.config(text="● Stopped",
                                     bg=C["red_dim"], fg=C["red"])

    def _stop_all(self):
        ui_state.append_log("Shutting down all services…")
        result = api.stop_all()
        ui_state.append_log(result.message)
        self._set_status("Stopped")

    def _stop_all_confirm(self):
        if not api.is_server_running() and not api.is_ngrok_running():
            return
        if messagebox.askokcancel("Stop server?",
                                  "Stop the server and ngrok?\n(Esc was pressed)"):
            self._stop_all()

    def _start_ngrok(self):
        # Apply auth token if set
        token = config.get("NGROK_AUTH_TOKEN", "").strip()
        if token:
            os.environ["NGROK_AUTHTOKEN"] = token
        result = api.start_ngrok()
        ui_state.append_log(result.message)
        if not result.ok and "not found" in result.message:
            messagebox.showerror("ngrok not found", result.message)
            self._toast.show("ngrok not found on PATH", "error")

    def _stop_ngrok(self):
        result = api.stop_ngrok()
        ui_state.append_log(result.message)

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
            self._toast.show("Public URL copied!", "success")
        else:
            messagebox.showwarning("No URL", "Public URL is not available.")

    def _restart_server(self):
        if not api.is_server_running():
            return
        mode = sys_state.get("mode") or "LAN"
        ui_state.append_log(f"Restarting server ({mode} mode)…")
        self._set_status("Restarting…")
        self._status_pill.config(text="◌ Restarting…",
                                 bg=C["orange_dim"], fg=C["orange"])
        self._is_restarting = True

        def _do():
            # Feature 2: only restart Flask, keep ngrok alive
            api.stop_server()
            time.sleep(1.2)
            result = api.start_server(mode)
            ui_state.append_log(result.message)

        threading.Thread(target=_do, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # INSTALL DEPS
    # ═══════════════════════════════════════════════════════════════════════════

    def _install_deps(self):
        ui_state.append_log("Installing dependencies…")
        base = (os.path.dirname(sys.executable)
                if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))

        def _run():
            steps = [
                ([sys.executable, "-m", "pip", "install",
                  "flask", "flask-socketio", "flask-cors",
                  "psutil", "qrcode[pil]", "pystray", "--quiet"], "pip install"),
                ([sys.executable, os.path.join(base, "download_assets.py")],  "download_assets"),
                ([sys.executable, os.path.join(base, "generate_icons.py")],   "generate_icons"),
            ]
            for cmd, label in steps:
                ui_state.append_log(f"  → {label}…")
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=base)
                    if result.returncode == 0:
                        ui_state.append_log(f"  ✓ {label} done")
                    else:
                        err = (result.stderr or result.stdout or "").strip()
                        ui_state.append_log(f"  ✗ {label} failed: {err[:200]}")
                except Exception as exc:
                    ui_state.append_log(f"  ✗ {label} error: {exc}")
            ui_state.append_log("Setup complete. Restart the Control Center to activate new packages.")
            self._toast.show("Dependencies installed", "success")

        threading.Thread(target=_run, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # DESKTOP SHORTCUT
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_shortcut(self):
        base = (os.path.dirname(sys.executable)
                if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))
        ps1 = os.path.join(base, "create-gui-shortcut.ps1")
        if not os.path.exists(ps1):
            messagebox.showerror("Not found", f"Script not found:\n{ps1}")
            return
        ui_state.append_log("Creating desktop shortcut…")

        def _run():
            try:
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass",
                     "-NonInteractive", "-File", ps1],
                    capture_output=True, text=True, cwd=base)
                out = ((result.stdout or "") + (result.stderr or "")).strip()
                for line in out.splitlines():
                    if line.strip():
                        ui_state.append_log(f"  {line.strip()}")
                if result.returncode == 0:
                    ui_state.append_log("✓ Shortcut created on Desktop.")
                    self._toast.show("Desktop shortcut created", "success")
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Shortcut created",
                        "Shortcut 'NEXUS Control Center' added to your Desktop.\n\n"
                        "To pin to taskbar:\n  Right-click the shortcut → Pin to taskbar"))
                else:
                    ui_state.append_log(f"  ✗ Shortcut creation failed (exit {result.returncode})")
            except FileNotFoundError:
                ui_state.append_log("  ✗ PowerShell not found.")
            except Exception as exc:
                ui_state.append_log(f"  ✗ Error: {exc}")

        threading.Thread(target=_run, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # QR CODES
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_qr(self, url: str, title: str):
        if not url:
            messagebox.showinfo("QR Code", "No URL available yet.")
            return
        if not _HAS_QR:
            messagebox.showinfo(
                "QR Code",
                f"Install qrcode + Pillow to enable QR codes:\n\n"
                f"  pip install qrcode[pil]\n\nURL: {url}")
            return

        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=C["bg"])
        win.resizable(False, False)

        qr = _qrcode.QRCode(box_size=6, border=3,
                             error_correction=_qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(url)
        qr.make(fit=True)
        img   = qr.make_image(fill_color="black", back_color="white")
        photo = _ImageTk.PhotoImage(img)

        tk.Label(win, image=photo, bg="white").pack(padx=16, pady=(16, 8))
        lbl = tk.Label(win, text=url, font=("Segoe UI", 9),
                       bg=C["bg"], fg=C["blue"],
                       wraplength=300, cursor="hand2")
        lbl.pack(padx=16)
        lbl.bind("<Button-1>", lambda _: webbrowser.open(url))
        tk.Label(win, text="Scan to open on any device",
                 font=("Segoe UI", 8), bg=C["bg"],
                 fg=C["subtext"]).pack(pady=(2, 4))

        def _copy():
            win.clipboard_clear()
            win.clipboard_append(url)
            self._toast.show("URL copied!", "success")

        tk.Button(win, text="Copy URL", command=_copy,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 8), relief=tk.FLAT,
                  cursor="hand2", padx=10, pady=4).pack(pady=(0, 16))

        win._photo = photo
        win.grab_set()
        return win

    def _show_qr_lan(self):
        self._show_qr(api.get_local_url(), "QR — LAN URL")

    def _show_qr_ngrok(self):
        url = api.get_public_url()
        if not url:
            messagebox.showinfo("QR Code", "ngrok URL not available yet.")
            return
        win = self._show_qr(url, "QR — Public (ngrok) URL")
        self._qr_ngrok_win = win

    # ═══════════════════════════════════════════════════════════════════════════
    # LIVE STATS (CPU / RAM)
    # ═══════════════════════════════════════════════════════════════════════════

    def _start_stats_poll(self):
        if not _HAS_PSUTIL:
            return
        self._cpu_alert_sent = False
        self._ram_alert_sent = False
        self._cpu_high_since = None
        self._ram_high_since = None

        def _poll():
            while self._stats_pid and api.is_server_running():
                try:
                    proc = _psutil.Process(self._stats_pid)
                    cpu  = proc.cpu_percent(interval=1)
                    mem  = proc.memory_info().rss / (1024 * 1024)
                    self.root.after(0, lambda c=cpu, m=mem: (
                        self.cpu_var.set(f"{c:.1f}%"),
                        self.ram_var.set(f"{m:.0f} MB"),
                    ))
                    # Feature 56: CPU/RAM alert
                    now = time.time()
                    if cpu > 80:
                        if self._cpu_high_since is None:
                            self._cpu_high_since = now
                        elif now - self._cpu_high_since >= 10 and not self._cpu_alert_sent:
                            self._cpu_alert_sent = True
                            self.root.after(0, lambda: self._toast.show(
                                f"High CPU: {cpu:.1f}% for 10s", "warning"))
                    else:
                        self._cpu_high_since = None
                    if mem > 500:
                        if self._ram_high_since is None:
                            self._ram_high_since = now
                        elif now - self._ram_high_since >= 10 and not self._ram_alert_sent:
                            self._ram_alert_sent = True
                            self.root.after(0, lambda: self._toast.show(
                                f"High RAM: {mem:.0f} MB for 10s", "warning"))
                    else:
                        self._ram_high_since = None
                except Exception:
                    break

        threading.Thread(target=_poll, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # STATUS BAR
    # ═══════════════════════════════════════════════════════════════════════════

    def _set_status(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.statusbar_var.set(f"[{ts}]  {msg}")

    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM TRAY
    # ═══════════════════════════════════════════════════════════════════════════

    def _minimize_to_tray(self):
        if not _HAS_TRAY:
            return
        self.root.withdraw()

        def _restore(icon, item):
            icon.stop()
            self._tray_icon = None
            self.root.after(0, self.root.deiconify)

        def _quit(icon, item):
            icon.stop()
            self._tray_icon = None
            self.root.after(0, self.on_closing)

        _base = (os.path.dirname(sys.executable)
                 if getattr(sys, "frozen", False)
                 else os.path.dirname(__file__))
        _icon_path = os.path.join(_base, "static", "icon-192.png")
        try:
            img = _TrayImage.open(_icon_path).resize((64, 64), _TrayImage.LANCZOS).convert("RGBA")
        except Exception:
            img = _TrayImage.new("RGBA", (64, 64), color=(0, 210, 106))

        menu = _pystray.Menu(
            _pystray.MenuItem("Open NEXUS Control Center", _restore, default=True),
            _pystray.MenuItem("Quit", _quit),
        )
        self._tray_icon = _pystray.Icon("NEXUS", img, "NEXUS Control Center", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # ANIMATED LOGO PULSE
    # ═══════════════════════════════════════════════════════════════════════════

    def _pulse_logo(self):
        """Gently pulse the center node of the logo by cycling its brightness."""
        if not self._logo_canvas:
            return
        try:
            # Oscillate between dim teal and bright teal
            import math
            t = time.time()
            # 0.0 → 1.0 sine wave, period ~2.5s
            v = (math.sin(t * 2.5) + 1) / 2   # 0..1
            # Interpolate between #007a62 (dim) and #00f5c4 (bright)
            r = int(0x00 + v * (0x00 - 0x00))
            g = int(0x7a + v * (0xf5 - 0x7a))
            b = int(0x62 + v * (0xc4 - 0x62))
            color = f"#{r:02x}{g:02x}{b:02x}"
            # Update the center node (last two ovals drawn = center + white dot)
            items = self._logo_canvas.find_all()
            if len(items) >= 2:
                self._logo_canvas.itemconfig(items[-2], fill=color)
            # Feature 59: animate one spoke line by cycling its color
            # Spoke lines start after the outer hexagon polygon (index 0)
            # There are 6 spoke lines at indices 1..6
            spoke_idx = int(t * 2) % 6 + 1  # cycle through spokes
            if len(items) > spoke_idx:
                # Alternate spoke color between teal and a lighter shade
                sv = (math.sin(t * 4 + spoke_idx) + 1) / 2
                sr = int(0x00)
                sg = int(0x7a + sv * (0xf5 - 0x7a))
                sb_val = int(0x62 + sv * (0xc4 - 0x62))
                spoke_color = f"#{sr:02x}{sg:02x}{sb_val:02x}"
                self._logo_canvas.itemconfig(items[spoke_idx], fill=spoke_color)
        except Exception:
            pass
        self.root.after(50, self._pulse_logo)

    # ═══════════════════════════════════════════════════════════════════════════
    # WINDOW GEOMETRY MEMORY
    # ═══════════════════════════════════════════════════════════════════════════

    def _restore_geometry(self):
        """Restore window size and position from config."""
        geom = config.get("WINDOW_GEOMETRY", "")
        if geom:
            try:
                # Validate geometry has reasonable dimensions before applying
                import re as _re
                m = _re.match(r'(\d+)x(\d+)', geom)
                if m:
                    w, h = int(m.group(1)), int(m.group(2))
                    if w >= 900 and h >= 600:
                        self.root.geometry(geom)
            except Exception:
                pass
        self.root.bind("<Configure>", self._on_window_configure)

    def _on_window_configure(self, event=None):
        """Save geometry on resize/move (debounced via after)."""
        if event and event.widget is self.root:
            if hasattr(self, "_geom_save_id"):
                self.root.after_cancel(self._geom_save_id)
            self._geom_save_id = self.root.after(
                800, self._persist_geometry)

    def _persist_geometry(self):
        geom = self.root.geometry()
        if geom and geom != "1x1+0+0":
            config["WINDOW_GEOMETRY"] = geom
            save_config_debounced(config)

    # ═══════════════════════════════════════════════════════════════════════════
    # CONNECTION HISTORY
    # ═══════════════════════════════════════════════════════════════════════════

    def _log_history(self, msg: str, kind: str = "join"):
        """Append a timestamped entry to the connection history tab."""
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        icon = "→" if kind == "join" else "←"
        text = f"[{ts}]  {icon}  {msg}\n"
        self._conn_history.append(text)
        if hasattr(self, "_history_box"):
            self._history_box.config(state=tk.NORMAL)
            self._history_box.insert(tk.END, text, kind)
            self._history_box.see(tk.END)
            self._history_box.config(state=tk.DISABLED)

    def _clear_history(self):
        self._conn_history.clear()
        if hasattr(self, "_history_box"):
            self._history_box.config(state=tk.NORMAL)
            self._history_box.delete("1.0", tk.END)
            self._history_box.config(state=tk.DISABLED)

    # ═══════════════════════════════════════════════════════════════════════════
    # SERVER MESSAGE BROADCAST
    # ═══════════════════════════════════════════════════════════════════════════

    def _send_broadcast(self):
        msg = self._broadcast_var.get().strip()
        if not msg:
            return
        if not api.is_server_running():
            self._toast.show("Server is not running", "warning")
            return
        admin_pw = config.get("ADMIN_PASSWORD", "").strip()
        if not admin_pw:
            self._toast.show("Set an Admin PW in config to use broadcast", "warning")
            return
        # Feature 22: save to broadcast history
        if msg not in self._broadcast_history:
            self._broadcast_history.insert(0, msg)
            self._broadcast_history = self._broadcast_history[:10]

        def _do():
            try:
                import urllib.request, json as _json
                port = config.get("PORT", 5000)
                url  = f"http://127.0.0.1:{port}/admin/broadcast"
                body = _json.dumps({"message": msg}).encode()
                req  = urllib.request.Request(
                    url, data=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Admin-Key":  admin_pw,
                    },
                    method="POST")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp.read()
                self.root.after(0, lambda: (
                    self._broadcast_var.set(""),
                    self._toast.show(f"Broadcast sent: {msg[:40]}", "success"),
                    ui_state.append_log(f"📢 Broadcast sent: {msg}"),
                ))
            except Exception as exc:
                self.root.after(0, lambda e=exc: (
                    self._toast.show(f"Broadcast failed: {e}", "error"),
                    ui_state.append_log(f"❌ Broadcast error: {e}"),
                ))

        threading.Thread(target=_do, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # LOG WORD-WRAP TOGGLE
    # ═══════════════════════════════════════════════════════════════════════════

    def _toggle_wrap(self):
        if not hasattr(self, "log_box"):
            return
        self._wrap_var.set(not self._wrap_var.get())
        if self._wrap_var.get():
            self.log_box.config(wrap=tk.WORD)
            self._wrap_btn.config(text="⇌ Wrap", fg=C["subtext"], bg=C["border"])
        else:
            self.log_box.config(wrap=tk.NONE)
            self._wrap_btn.config(text="⇌ NoWrap", fg=C["blue"], bg=C["blue_dim"])

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTO-UPDATE CHECKER
    # ═══════════════════════════════════════════════════════════════════════════

    _CURRENT_VERSION = "v1.1"
    _GITHUB_RELEASES = "https://api.github.com/repos/odetayojosiah/lan-chat/releases/latest"

    def _check_for_updates(self):
        """Check GitHub releases for a newer version. Runs in background."""
        def _do():
            try:
                import urllib.request, json as _json
                req = urllib.request.Request(
                    self._GITHUB_RELEASES,
                    headers={"User-Agent": "LanChat-ControlCenter/1.1"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = _json.loads(resp.read())
                latest = data.get("tag_name", "")
                if latest and latest != self._CURRENT_VERSION:
                    url = data.get("html_url", "")
                    self.root.after(0, lambda: self._show_update_toast(latest, url))
            except Exception:
                pass  # silently ignore — no internet, wrong repo, etc.

        threading.Thread(target=_do, daemon=True).start()

    def _show_update_toast(self, version: str, url: str):
        self._toast.show(f"Update available: {version}", "info")
        ui_state.append_log(
            f"🔔 Update available: {version}  —  {url or 'check GitHub'}")

    # ═══════════════════════════════════════════════════════════════════════════
    # WINDOW CLOSE
    # ═══════════════════════════════════════════════════════════════════════════

    def on_closing(self):
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        if api.is_server_running() or api.is_ngrok_running():
            if messagebox.askokcancel(
                "Quit", "Server / ngrok is still running.\nStop everything and quit?"
            ):
                api.stop_all()
                self.root.destroy()
        else:
            self.root.destroy()


# ── Feature method implementations (injected before entry point) ──────────────

import json as _json_mod
import csv as _csv_mod

def _build_rooms_tab(self):
    frame = tk.Frame(self._tab_content, bg=C["card"])
    self._tab_frames["rooms"] = frame
    hdr = tk.Frame(frame, bg=C["card"])
    hdr.pack(fill=tk.X, padx=10, pady=(8, 4))
    tk.Label(hdr, text="Active Rooms", font=("Segoe UI", 9, "bold"),
             bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
    tk.Button(hdr, text="↺ Refresh", command=lambda: self._rooms_poll(force=True),
              bg=C["border"], fg=C["text"], font=("Segoe UI", 7),
              relief=tk.FLAT, cursor="hand2", padx=6, pady=2).pack(side=tk.RIGHT)
    self._rooms_box = scrolledtext.ScrolledText(
        frame, state=tk.DISABLED, bg=C["bg"], fg=C["text"],
        font=("Consolas", 8), relief=tk.FLAT, wrap=tk.WORD, highlightthickness=0)
    self._rooms_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
    self._rooms_box.tag_config("frozen", foreground=C["orange"])
    self._rooms_box.tag_config("active", foreground=C["green"])

def _rooms_poll(self, force=False):
    if not api.is_server_running():
        return
    def _do():
        try:
            port = config.get("PORT", 5000)
            admin_pw = config.get("ADMIN_PASSWORD", "")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/analytics",
                headers={"X-Admin-Key": admin_pw})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json_mod.loads(resp.read())
            self.root.after(0, lambda d=data: self._update_rooms_display(d))
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()
    if api.is_server_running():
        self.root.after(5000, self._rooms_poll)

def _update_rooms_display(self, data):
    if not hasattr(self, "_rooms_box"):
        return
    self._rooms_box.config(state=tk.NORMAL)
    self._rooms_box.delete("1.0", tk.END)
    rooms = data.get("rooms", {})
    if not rooms:
        self._rooms_box.insert(tk.END, "No active rooms.\n", "")
    else:
        for rid, info in rooms.items():
            frozen = info.get("is_frozen", False)
            members = len(info.get("members", []))
            tag = "frozen" if frozen else "active"
            status = "❄ FROZEN" if frozen else "● active"
            self._rooms_box.insert(tk.END,
                f"  {rid}  —  {members} members  [{status}]\n", tag)
    self._rooms_box.config(state=tk.DISABLED)

def _build_cards_collapse_btn(self):
    # Store reference to cards row for collapse/expand
    self._cards_visible = True
    # The collapse button sits inside the cards row itself (right side)
    self._cards_collapse_btn = tk.Button(
        self._cards_row, text="▲", font=("Segoe UI", 7),
        bg=C["bg"], fg=C["muted"], relief=tk.FLAT,
        cursor="hand2", padx=4, pady=1,
        command=self._toggle_cards)
    self._cards_collapse_btn.pack(side=tk.RIGHT, padx=(0, 4))

def _toggle_cards(self):
    if self._cards_visible:
        # Hide all stat cards but keep the row (with the button)
        for card in (self._card_uptime, self._card_users,
                     self._card_cpu, self._card_ram):
            card.pack_forget()
        self._cards_visible = False
        self._cards_collapse_btn.config(text="▼")
    else:
        for card in (self._card_uptime, self._card_users,
                     self._card_cpu, self._card_ram):
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=2)
        self._cards_visible = True
        self._cards_collapse_btn.config(text="▲")

def _reconnect_server(self):
    mode = config.get("LAST_MODE", "LAN")
    if self._check_port_conflict():
        return
    self._status_pill.config(text="◌ Starting…", bg=C["orange_dim"], fg=C["orange"])
    result = api.start_server(mode)
    if result.ok:
        ui_state.append_log(f"{mode} server started (PID {result.data['pid']})")
    else:
        ui_state.append_log(f"ERROR: {result.message}")
        self._toast.show(result.message, "error")
        self._status_pill.config(text="● Stopped", bg=C["red_dim"], fg=C["red"])

def _kick_selected_user(self):
    sel = self._users_box.curselection()
    if not sel:
        return
    name = self._users_box.get(sel[0]).strip().lstrip("●● ").strip()
    admin_pw = config.get("ADMIN_PASSWORD", "").strip()
    if not admin_pw:
        self._toast.show("Set Admin PW to kick users", "warning")
        return
    def _do():
        try:
            port = config.get("PORT", 5000)
            body = _json_mod.dumps({"target": name}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/admin/kick",
                data=body,
                headers={"Content-Type": "application/json", "X-Admin-Key": admin_pw},
                method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
            self.root.after(0, lambda: self._toast.show(f"Kicked: {name}", "success"))
        except Exception as e:
            self.root.after(0, lambda err=e: self._toast.show(f"Kick failed: {err}", "error"))
    threading.Thread(target=_do, daemon=True).start()

def _show_users_context_menu(self, event):
    idx = self._users_box.nearest(event.y)
    if idx >= 0:
        self._users_box.selection_clear(0, tk.END)
        self._users_box.selection_set(idx)
    try:
        self._users_ctx_menu.tk_popup(event.x_root, event.y_root)
    finally:
        self._users_ctx_menu.grab_release()

def _ping_server(self):
    if not api.is_server_running():
        self._toast.show("Server is not running", "warning")
        return
    def _do():
        try:
            port = config.get("PORT", 5000)
            start = time.time()
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5):
                pass
            ms = int((time.time() - start) * 1000)
            color = "success" if ms < 100 else "warning" if ms < 500 else "error"
            self.root.after(0, lambda: self._toast.show(f"Ping: {ms}ms", color))
        except Exception as e:
            self.root.after(0, lambda err=e: self._toast.show(f"Ping failed: {err}", "error"))
    threading.Thread(target=_do, daemon=True).start()

def _save_log_csv(self):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=f"lanchat_log_{ts}.csv")
    if not path:
        return
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = _csv_mod.writer(f)
            writer.writerow(["timestamp", "level", "message"])
            for text, tag in self._all_lines:
                m = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*(.*)', text)
                if m:
                    ts_val, msg = m.group(1), m.group(2)
                else:
                    ts_val, msg = "", text
                level = {"red": "ERROR", "orange": "WARN", "green": "INFO"}.get(tag, "INFO")
                writer.writerow([ts_val, level, msg])
        self._toast.show(f"CSV saved: {os.path.basename(path)}", "success")
    except Exception as e:
        messagebox.showerror("Save failed", str(e))

def _copy_log_to_clipboard(self):
    content = self.log_box.get("1.0", tk.END)
    self.root.clipboard_clear()
    self.root.clipboard_append(content)
    self._toast.show("Log copied to clipboard", "success")

def _log_font_increase(self):
    self._log_font_size = min(14, self._log_font_size + 1)
    self.log_box.config(font=("Consolas", self._log_font_size))
    config["LOG_FONT_SIZE"] = self._log_font_size
    save_config_debounced(config)

def _log_font_decrease(self):
    self._log_font_size = max(7, self._log_font_size - 1)
    self.log_box.config(font=("Consolas", self._log_font_size))
    config["LOG_FONT_SIZE"] = self._log_font_size
    save_config_debounced(config)

def _log_double_click_copy(self, event):
    try:
        idx = self.log_box.index(f"@{event.x},{event.y}")
        line_start = f"{idx.split('.')[0]}.0"
        line_end   = f"{idx.split('.')[0]}.end"
        text = self.log_box.get(line_start, line_end)
        if text.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(text.strip())
            self._toast.show("Line copied", "info", duration=1500)
    except Exception:
        pass

def _copy_status_to_clipboard(self):
    text = self.statusbar_var.get()
    self.root.clipboard_clear()
    self.root.clipboard_append(text)
    self._toast.show("Status copied", "info", duration=1500)

def _pulse_health_dot(self):
    if not hasattr(self, "_health_dot"):
        return
    running = api.is_server_running()
    if running:
        current = self._health_dot.cget("fg")
        self._health_dot.config(fg=C["green"] if current == C["muted"] else C["muted"])
        self.root.after(1000, self._pulse_health_dot)
    else:
        self._health_dot.config(fg=C["muted"])
        self.root.after(2000, self._pulse_health_dot)

def _focus_broadcast(self):
    if hasattr(self, "_broadcast_entry"):
        self._broadcast_entry.focus_set()

def _show_quick_settings(self):
    win = tk.Toplevel(self.root)
    win.title("Quick Settings")
    win.configure(bg=C["bg"])
    win.resizable(False, False)
    win.grab_set()
    tk.Label(win, text="Quick Settings", font=("Segoe UI", 11, "bold"),
             bg=C["bg"], fg=C["text"]).pack(padx=20, pady=(16, 8))
    card = tk.Frame(win, bg=C["card"], padx=16, pady=12)
    card.pack(fill=tk.X, padx=16, pady=(0, 8))
    for var, label in (
        (self.auto_restart_var,       "Auto-restart on crash"),
        (self.auto_ngrok_var,         "Auto-start ngrok (PUBLIC)"),
        (self.auto_browser_lan_var,   "Open browser on LAN start"),
        (self.auto_browser_ngrok_var, "Open browser on ngrok ready"),
    ):
        tk.Checkbutton(card, text=label, variable=var,
                       bg=C["card"], fg=C["text"],
                       selectcolor=C["bg"],
                       activebackground=C["card"],
                       font=("Segoe UI", 9),
                       command=self._save_config).pack(anchor=tk.W, pady=3)
    tk.Button(win, text="Close", command=win.destroy,
              bg=C["border"], fg=C["text"], font=("Segoe UI", 9),
              relief=tk.FLAT, cursor="hand2", padx=20, pady=6).pack(pady=(0, 16))

def _show_broadcast_history(self):
    if not self._broadcast_history:
        self._toast.show("No broadcast history yet", "info")
        return
    win = tk.Toplevel(self.root)
    win.title("Broadcast History")
    win.configure(bg=C["bg"])
    win.resizable(False, False)
    win.grab_set()
    tk.Label(win, text="Recent Broadcasts", font=("Segoe UI", 10, "bold"),
             bg=C["bg"], fg=C["text"]).pack(padx=16, pady=(12, 6))
    for msg in reversed(self._broadcast_history[-10:]):
        row = tk.Frame(win, bg=C["card"])
        row.pack(fill=tk.X, padx=12, pady=2)
        tk.Label(row, text=msg, font=("Segoe UI", 8), bg=C["card"],
                 fg=C["text"], anchor=tk.W, wraplength=280).pack(side=tk.LEFT, padx=8, pady=4, fill=tk.X, expand=True)
        tk.Button(row, text="↺", font=("Segoe UI", 8),
                  bg=C["border"], fg=C["text"], relief=tk.FLAT,
                  cursor="hand2", padx=4,
                  command=lambda m=msg, w=win: (
                      self._broadcast_var.set(m), w.destroy()
                  )).pack(side=tk.RIGHT, padx=4)
    tk.Button(win, text="Close", command=win.destroy,
              bg=C["border"], fg=C["text"], font=("Segoe UI", 9),
              relief=tk.FLAT, cursor="hand2", padx=16, pady=5).pack(pady=(6, 12))

def _update_broadcast_counter(self, *_):
    if not hasattr(self, "_broadcast_counter"):
        return
    remaining = 200 - len(self._broadcast_var.get())
    color = C["red"] if remaining < 20 else C["muted"]
    self._broadcast_counter.config(text=str(remaining), fg=color)

def _export_config(self):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        initialfile=f"nexus_config_{ts}.json")
    if not path:
        return
    try:
        safe = {k: v for k, v in config.items()
                if k not in ("SERVER_PASSWORD", "ADMIN_PASSWORD", "NGROK_AUTH_TOKEN")}
        with open(path, "w", encoding="utf-8") as f:
            _json_mod.dump(safe, f, indent=2)
        self._toast.show("Config exported", "success")
    except Exception as e:
        messagebox.showerror("Export failed", str(e))

def _import_config(self):
    path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = _json_mod.load(f)
        config.update(data)
        save_config_debounced(config)
        self._toast.show("Config imported — restart to apply all changes", "success")
    except Exception as e:
        messagebox.showerror("Import failed", str(e))

def _gen_password(self):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(chars, k=12))

def _toggle_always_on_top(self):
    current = bool(self.root.attributes("-topmost"))
    self.root.attributes("-topmost", not current)
    state = "ON" if not current else "OFF"
    self._toast.show(f"Always on top: {state}", "info")

def _toggle_compact_mode(self):
    self._compact_mode = not self._compact_mode
    # Adjust stat card padding
    for card in (self._card_uptime, self._card_users, self._card_cpu, self._card_ram):
        card.config(ipady=0 if self._compact_mode else 2)
    self._toast.show(f"Compact mode: {'ON' if self._compact_mode else 'OFF'}", "info")

def _apply_win11_style(self):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        if not hwnd:
            hwnd = self.root.winfo_id()
        # Dark mode title bar
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value), ctypes.sizeof(value))
        # Teal border color (0x00BGR format)
        DWMWA_BORDER_COLOR = 34
        # #00f5c4 → BGR = 0x00C4F500
        border_color = ctypes.c_int(0x00C4F500)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR,
            ctypes.byref(border_color), ctypes.sizeof(border_color))
        # Mica effect (Windows 11 22H2+)
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        mica = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(mica), ctypes.sizeof(mica))
    except Exception:
        pass

def _fade_in(self, step: int):
    alpha = min(1.0, step * 0.1)
    try:
        self.root.attributes("-alpha", alpha)
        if alpha < 1.0:
            self.root.after(20, lambda: self._fade_in(step + 1))
    except Exception:
        pass

def _flash_taskbar(self):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = self.root.winfo_id()
        fi = ctypes.create_string_buffer(28)
        ctypes.memset(fi, 0, 28)
        import struct
        struct.pack_into("IIIII", fi, 0, 28, 3, 3, 0, 0)
        ctypes.windll.user32.FlashWindowEx(hwnd, fi)
    except Exception:
        pass

def _auto_save_crash_log(self):
    try:
        base = (os.path.dirname(sys.executable)
                if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(base, f"crash_log_{ts}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"NEXUS Control Center — Crash Log\n")
            f.write(f"Time: {datetime.datetime.now()}\n")
            f.write("─" * 50 + "\n\n")
            f.write(self.log_box.get("1.0", tk.END))
        ui_state.append_log(f"⚠ Crash log saved: {os.path.basename(path)}")
        self._toast.show(f"Crash log saved: {os.path.basename(path)}", "warning")
    except Exception:
        pass

def _check_port_conflict(self) -> bool:
    try:
        port = int(self.port_var.get())
    except (ValueError, AttributeError):
        port = config.get("PORT", 5000)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        if result == 0:
            self._toast.show(f"Port {port} is already in use!", "error")
            ui_state.append_log(f"❌ Port {port} is already in use — cannot start server.")
            return True
    except Exception:
        pass
    return False

# Inject all methods into ControlCenter
ControlCenter._build_rooms_tab         = _build_rooms_tab
ControlCenter._rooms_poll              = _rooms_poll
ControlCenter._update_rooms_display    = _update_rooms_display
ControlCenter._build_cards_collapse_btn = _build_cards_collapse_btn
ControlCenter._toggle_cards            = _toggle_cards
ControlCenter._reconnect_server        = _reconnect_server
ControlCenter._kick_selected_user      = _kick_selected_user
ControlCenter._show_users_context_menu = _show_users_context_menu
ControlCenter._ping_server             = _ping_server
ControlCenter._save_log_csv            = _save_log_csv
ControlCenter._copy_log_to_clipboard   = _copy_log_to_clipboard
ControlCenter._log_font_increase       = _log_font_increase
ControlCenter._log_font_decrease       = _log_font_decrease
ControlCenter._log_double_click_copy   = _log_double_click_copy
ControlCenter._copy_status_to_clipboard = _copy_status_to_clipboard
ControlCenter._pulse_health_dot        = _pulse_health_dot
ControlCenter._focus_broadcast         = _focus_broadcast
ControlCenter._show_quick_settings     = _show_quick_settings
ControlCenter._show_broadcast_history  = _show_broadcast_history
ControlCenter._update_broadcast_counter = _update_broadcast_counter
ControlCenter._export_config           = _export_config
ControlCenter._import_config           = _import_config
ControlCenter._gen_password            = _gen_password
ControlCenter._toggle_always_on_top    = _toggle_always_on_top
ControlCenter._toggle_compact_mode     = _toggle_compact_mode
ControlCenter._apply_win11_style       = _apply_win11_style
ControlCenter._fade_in                 = _fade_in
ControlCenter._flash_taskbar           = _flash_taskbar
ControlCenter._auto_save_crash_log     = _auto_save_crash_log
ControlCenter._check_port_conflict     = _check_port_conflict


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        # Must be set BEFORE tk.Tk() so Windows assigns the correct taskbar icon
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "LanChat.ControlCenter.1")
        except Exception:
            pass
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "LanChat.ControlCenter.Mutex")
        if ctypes.windll.kernel32.GetLastError() == 183:
            _hwnd = ctypes.windll.user32.FindWindowW(None, "NEXUS \u2014 Control Center")
            if _hwnd:
                ctypes.windll.user32.ShowWindow(_hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(_hwnd)
            sys.exit(0)

    root = tk.Tk()
    app  = ControlCenter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
