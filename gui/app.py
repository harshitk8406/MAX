"""
MAX 2.0 — Stark Industries HUD
Full Iron Man aesthetic: dark background, cyan neon glows, arc reactor animation,
circular gauges, chat log, quick-action grid. Pure tkinter — no extra deps.
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import math
import time
import datetime
import json
import os
import psutil

from core.logger import log

# ── Stark Colour Palette ──────────────────────────────────────────────────────
C = {
    "void":        "#000810",   # Deepest black
    "bg":          "#020D1A",   # Main background
    "panel":       "#041225",   # Panel fill
    "border":      "#0A2A45",   # Panel border
    "glow_bright": "#00E5FF",   # Bright cyan (primary neon)
    "glow_mid":    "#00B8D4",   # Medium cyan
    "glow_dim":    "#005F73",   # Dim cyan
    "arc_core":    "#60EFFF",   # Arc reactor core
    "arc_ring1":   "#00E5FF",
    "arc_ring2":   "#0099BB",
    "teal":        "#00FFC8",   # Accent teal
    "gold":        "#FFD700",   # Alert / status gold
    "red":         "#FF3A3A",   # Error / warning red
    "text_hi":     "#E0F7FA",   # High-contrast text
    "text_lo":     "#4DD0E1",   # Dim label text
    "text_mute":   "#1A4A5A",   # Very muted text
    "user_bg":     "#061A2E",
    "max_bg":   "#030F1E",
}

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

USER_NAME      = _cfg["user"]["name"]
ASSISTANT_NAME = _cfg["user"].get("assistant_name", "M.A.X")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: draw a neon glow arc on a canvas
# ─────────────────────────────────────────────────────────────────────────────

def _glow_arc(canvas, cx, cy, r, start, extent, color, width=2, layers=3):
    """Draw a neon-glowing arc with multiple layered strokes."""
    for i in range(layers, 0, -1):
        alpha_w = width + (layers - i) * 3
        # Fade the outer layers
        canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=start, extent=extent,
            style="arc", outline=color,
            width=alpha_w
        )


def _glow_oval(canvas, cx, cy, r, color, width=2, layers=3):
    _glow_arc(canvas, cx, cy, r, 0, 359, color, width, layers)


# ─────────────────────────────────────────────────────────────────────────────
# Arc Reactor Widget
# ─────────────────────────────────────────────────────────────────────────────

class ArcReactor:
    """Animated arc reactor — the centrepiece of the HUD."""

    SIZE = 220

    def __init__(self, parent):
        self.size = self.SIZE
        self.cx = self.cy = self.SIZE // 2
        self._angle   = 0.0
        self._pulse   = 0.0
        self._state   = "idle"
        self._running = True

        self.canvas = tk.Canvas(parent, width=self.SIZE, height=self.SIZE,
                                bg=C["bg"], highlightthickness=0)
        self._draw()

    def widget(self):
        return self.canvas

    def set_state(self, state: str):
        self._state = state

    def start(self):
        self._tick()

    def _tick(self):
        if not self._running:
            return
        self._angle += 2.5 if self._state == "thinking" else 1.0
        self._pulse = math.sin(time.time() * 3) * 0.5 + 0.5
        self._draw()
        self.canvas.after(40, self._tick)

    def _draw(self):
        c = self.canvas
        c.delete("all")
        cx, cy, r = self.cx, self.cy, self.cx - 4

        state_color = {
            "idle":      C["glow_dim"],
            "listening": C["glow_bright"],
            "thinking":  C["gold"],
            "speaking":  C["teal"],
        }.get(self._state, C["glow_dim"])

        # ── Outer decorative rings ──────────────────────────────────────────
        _glow_oval(c, cx, cy, r - 2, C["border"], 1, 1)

        # Spinning segmented outer ring
        seg_count = 24
        for i in range(seg_count):
            a = math.radians(self._angle + i * (360 / seg_count))
            bright = (i % 4 == 0)
            col    = state_color if bright else C["glow_dim"]
            start_deg = self._angle + i * (360 / seg_count)
            _glow_arc(c, cx, cy, r - 2, start_deg, 10, col, 2, 1)

        # Middle ring — static
        _glow_oval(c, cx, cy, r - 18, C["glow_dim"], 1, 1)

        # Slowly counter-rotating inner ring segments
        inner_r = r - 30
        for i in range(8):
            start_d = -self._angle * 0.7 + i * 45
            col = state_color if i % 2 == 0 else C["glow_dim"]
            _glow_arc(c, cx, cy, inner_r, start_d, 30, col, 3, 2)

        # ── Core glow ───────────────────────────────────────────────────────
        core_r    = 28 + self._pulse * 6
        glow_intensity = int(self._pulse * 30)

        # Outer core glow layers
        for layer_r in [core_r + 20, core_r + 12, core_r + 6, core_r]:
            alpha = max(20, int(40 - (core_r + 20 - layer_r) * 3))
            c.create_oval(cx - layer_r, cy - layer_r,
                          cx + layer_r, cy + layer_r,
                          fill="", outline=state_color, width=1)

        # Core fill
        c.create_oval(cx - core_r, cy - core_r,
                      cx + core_r, cy + core_r,
                      fill=C["void"], outline=C["arc_core"], width=2)
        c.create_oval(cx - core_r + 6, cy - core_r + 6,
                      cx + core_r - 6, cy + core_r - 6,
                      fill=C["arc_core"], outline="")

        # Core text / state
        state_label = {"idle": "STANDBY", "listening": "ACTIVE",
                       "thinking": "THINKING", "speaking": "SPEAKING"}.get(self._state, "STANDBY")
        c.create_text(cx, cy + r - 22, text=state_label,
                      fill=state_color, font=("Courier New", 7, "bold"))

        # ── Stark branding below reactor ────────────────────────────────────
        c.create_text(cx, cy + r + 8, text="STARK  INDUSTRIES",
                      fill=C["glow_dim"], font=("Courier New", 7, "bold"))


# ─────────────────────────────────────────────────────────────────────────────
# Circular Gauge Widget
# ─────────────────────────────────────────────────────────────────────────────

class CircularGauge:
    """Compact arc gauge with label and value, Iron Man style."""

    def __init__(self, parent, label: str, size=100, color=None):
        self._label = label
        self._value = 0.0
        self._color = color or C["glow_bright"]
        self._size  = size
        self.canvas = tk.Canvas(parent, width=size, height=size,
                                bg=C["panel"], highlightthickness=0)
        self._draw()

    def widget(self):
        return self.canvas

    def set_value(self, pct: float):
        """pct: 0.0 – 100.0"""
        self._value = max(0.0, min(100.0, pct))
        self._draw()

    def _draw(self):
        c   = self.canvas
        c.delete("all")
        sz  = self._size
        cx = cy = sz // 2
        r   = sz // 2 - 8

        # Background arc
        _glow_arc(c, cx, cy, r, 140, 260, C["border"], 6, 1)
        # Value arc
        extent = self._value / 100 * 260
        if extent > 1:
            col = self._color
            if self._value > 80:
                col = C["gold"]
            if self._value > 90:
                col = C["red"]
            _glow_arc(c, cx, cy, r, 140, extent, col, 6, 2)

        # Value text
        c.create_text(cx, cy - 6, text=f"{int(self._value)}%",
                      fill=C["text_hi"], font=("Courier New", int(sz * 0.13), "bold"))
        c.create_text(cx, cy + 10, text=self._label,
                      fill=C["text_lo"], font=("Courier New", int(sz * 0.09)))


# ─────────────────────────────────────────────────────────────────────────────
# Scanning Line Animation
# ─────────────────────────────────────────────────────────────────────────────

class ScanLine:
    """Horizontal scan line that sweeps down the chat panel — pure ambiance."""

    def __init__(self, canvas, width, height):
        self._c  = canvas
        self._w  = width
        self._h  = height
        self._y  = 0
        self._id = None

    def start(self):
        self._tick()

    def _tick(self):
        if self._id:
            try:
                self._c.delete(self._id)
            except Exception:
                pass
        self._y = (self._y + 2) % self._h
        try:
            self._id = self._c.create_line(
                0, self._y, self._w, self._y,
                fill=C["glow_dim"], width=1
            )
        except Exception:
            pass
        self._c.after(60, self._tick)


# ─────────────────────────────────────────────────────────────────────────────
# Main HUD Window
# ─────────────────────────────────────────────────────────────────────────────

class MaxGUI:
    """Full Iron Man HUD: arc reactor + gauges + chat + quick actions."""

    W, H = 1400, 820

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("M.A.X — Stark Industries HUD")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(True, True)
        self.root.configure(bg=C["void"])
        self.root.attributes("-alpha", 0.97)

        self._state = "idle"
        self._history = []

        # Callback hooks (filled in by main.py)
        self.on_text_submit     = None
        self.on_listen_click    = None
        self.on_quick_action    = None

        self._build_fonts()
        self._build_layout()
        self._start_clock()
        self._start_sys_monitor()

    # ── Fonts ─────────────────────────────────────────────────────────────────

    def _build_fonts(self):
        self.f_title   = tkfont.Font(family="Courier New", size=11, weight="bold")
        self.f_label   = tkfont.Font(family="Courier New", size=9)
        self.f_small   = tkfont.Font(family="Courier New", size=8)
        self.f_chat    = tkfont.Font(family="Courier New", size=10)
        self.f_brand   = tkfont.Font(family="Courier New", size=14, weight="bold")
        self.f_clock   = tkfont.Font(family="Courier New", size=22, weight="bold")
        self.f_btn     = tkfont.Font(family="Courier New", size=8, weight="bold")

    # ── Top HUD Banner ────────────────────────────────────────────────────────

    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=C["panel"], height=38)
        bar.pack(fill="x", padx=0, pady=0)

        # Left: STARK brand
        tk.Label(bar, text="◈  STARK  INDUSTRIES  ◈",
                 bg=C["panel"], fg=C["glow_bright"], font=self.f_brand).pack(side="left", padx=16, pady=6)

        # Centre: system title
        tk.Label(bar, text="M.A.X  —  Machine Autonomous eXpert",
                 bg=C["panel"], fg=C["text_lo"], font=self.f_label).pack(side="left", expand=True)

        # Right: live clock
        self._clock_lbl = tk.Label(bar, text="--:--:--",
                                   bg=C["panel"], fg=C["glow_bright"], font=self.f_clock)
        self._clock_lbl.pack(side="right", padx=16)

        # Separator line
        sep = tk.Canvas(parent, height=2, bg=C["void"], highlightthickness=0)
        sep.pack(fill="x")
        sep.create_line(0, 1, 5000, 1, fill=C["glow_bright"], width=1)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Top banner
        self._build_topbar(self.root)

        # Three-column body
        body = tk.Frame(self.root, bg=C["void"])
        body.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        # LEFT panel (230px)
        left = self._panel(body, width=230)
        left.pack(side="left", fill="y", padx=(0, 3))
        self._build_left(left)

        # CENTRE panel (fills remaining)
        centre = self._panel(body)
        centre.pack(side="left", fill="both", expand=True, padx=3)
        self._build_centre(centre)

        # RIGHT panel (230px)
        right = self._panel(body, width=230)
        right.pack(side="right", fill="y", padx=(3, 0))
        self._build_right(right)

    def _panel(self, parent, width=None):
        kwargs = dict(bg=C["panel"], bd=0, relief="flat",
                      highlightbackground=C["glow_dim"], highlightthickness=1)
        if width:
            kwargs["width"] = width
        f = tk.Frame(parent, **kwargs)
        return f

    def _section_header(self, parent, text):
        tk.Label(parent, text=f"  ◆  {text}  ◆",
                 bg=C["panel"], fg=C["glow_bright"], font=self.f_title).pack(
            fill="x", pady=(10, 2))
        tk.Canvas(parent, height=1, bg=C["panel"],
                  highlightthickness=0).pack(fill="x", padx=12)

    # ── LEFT Panel ────────────────────────────────────────────────────────────

    def _build_left(self, parent):
        self._section_header(parent, "SYSTEM METRICS")

        gauge_frame = tk.Frame(parent, bg=C["panel"])
        gauge_frame.pack(pady=6)

        # CPU gauge
        cf = tk.Frame(gauge_frame, bg=C["panel"])
        cf.pack(side="left", padx=4)
        self._cpu_gauge = CircularGauge(cf, "CPU", 100, C["glow_bright"])
        self._cpu_gauge.widget().pack()

        # RAM gauge
        rf = tk.Frame(gauge_frame, bg=C["panel"])
        rf.pack(side="left", padx=4)
        self._ram_gauge = CircularGauge(rf, "RAM", 100, C["teal"])
        self._ram_gauge.widget().pack()

        # Battery
        self._section_header(parent, "POWER CELL")
        self._bat_gauge = CircularGauge(parent, "ENERGY", 100, C["gold"])
        self._bat_gauge.widget().pack(pady=4)

        # Network / Disk info
        self._section_header(parent, "STORAGE")
        self._disk_lbl = tk.Label(parent, text="Disk: --", bg=C["panel"],
                                  fg=C["text_lo"], font=self.f_small, justify="left")
        self._disk_lbl.pack(anchor="w", padx=12, pady=2)

        self._net_lbl = tk.Label(parent, text="Net: --", bg=C["panel"],
                                 fg=C["text_lo"], font=self.f_small, justify="left")
        self._net_lbl.pack(anchor="w", padx=12, pady=2)

        # Date
        self._section_header(parent, "STARDATE")
        self._date_lbl = tk.Label(parent, text="--", bg=C["panel"],
                                  fg=C["glow_bright"], font=self.f_label, justify="center")
        self._date_lbl.pack(pady=4)

        # Status bar at bottom
        tk.Frame(parent, height=1, bg=C["glow_dim"]).pack(fill="x", side="bottom", pady=4)
        self._status_lbl = tk.Label(parent, text="● ONLINE",
                                    bg=C["panel"], fg=C["teal"], font=self.f_small)
        self._status_lbl.pack(side="bottom", pady=4)

    # ── CENTRE Panel ─────────────────────────────────────────────────────────

    def _build_centre(self, parent):
        # Arc reactor at top centre
        reactor_frame = tk.Frame(parent, bg=C["panel"])
        reactor_frame.pack(pady=8)
        self._reactor = ArcReactor(reactor_frame)
        self._reactor.widget().pack()

        # Chat log
        self._section_header(parent, "COMMUNICATION LOG")

        chat_outer = tk.Frame(parent, bg=C["border"], bd=0)
        chat_outer.pack(fill="both", expand=True, padx=8, pady=4)

        self._chat_canvas = tk.Canvas(chat_outer, bg=C["max_bg"],
                                      highlightthickness=0)
        scroll = tk.Scrollbar(chat_outer, orient="vertical",
                              command=self._chat_canvas.yview,
                              bg=C["panel"], troughcolor=C["void"])
        self._chat_canvas.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        self._chat_canvas.pack(side="left", fill="both", expand=True)

        self._chat_frame = tk.Frame(self._chat_canvas, bg=C["max_bg"])
        self._chat_window = self._chat_canvas.create_window(
            (0, 0), window=self._chat_frame, anchor="nw")
        self._chat_frame.bind("<Configure>", self._on_chat_resize)
        self._chat_canvas.bind("<Configure>", self._on_canvas_resize)

        # Input bar
        self._build_input(parent)

        # Quick actions
        self._build_quick_actions(parent)

    def _build_input(self, parent):
        bar = tk.Frame(parent, bg=C["panel"], pady=4)
        bar.pack(fill="x", padx=8)

        tk.Label(bar, text="►", bg=C["panel"], fg=C["glow_bright"],
                 font=self.f_title).pack(side="left", padx=(4, 2))

        self._input_var = tk.StringVar()
        entry = tk.Entry(bar, textvariable=self._input_var,
                         bg=C["void"], fg=C["glow_bright"],
                         insertbackground=C["glow_bright"],
                         font=self.f_chat, relief="flat", bd=4,
                         highlightthickness=1,
                         highlightbackground=C["glow_dim"],
                         highlightcolor=C["glow_bright"])
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.bind("<Return>", self._on_submit)

        mic_btn = tk.Button(bar, text="🎤", command=self._on_mic,
                            bg=C["glow_dim"], fg=C["void"],
                            activebackground=C["glow_bright"],
                            relief="flat", padx=10, pady=4,
                            cursor="hand2", font=self.f_title)
        mic_btn.pack(side="left", padx=(4, 0))

        send_btn = tk.Button(bar, text="SEND ▶", command=self._on_submit,
                             bg=C["glow_dim"], fg=C["void"],
                             activebackground=C["glow_bright"],
                             relief="flat", padx=10, pady=4,
                             cursor="hand2", font=self.f_btn)
        send_btn.pack(side="left", padx=(4, 0))

    def _build_quick_actions(self, parent):
        self._section_header(parent, "QUICK COMMANDS")
        grid = tk.Frame(parent, bg=C["panel"])
        grid.pack(fill="x", padx=8, pady=(0, 6))

        ACTIONS = [
            ("⏰ REMINDERS",  "get_reminders"),
            ("📰 NEWS",        "news"),
            ("🌤 WEATHER",     "weather"),
            ("🖥 CPU STATUS",  "cpu_status"),
            ("💊 BRIEFING",    "morning_briefing"),
            ("📷 SCREENSHOT",  "take_screenshot"),
        ]
        for i, (label, intent) in enumerate(ACTIONS):
            col = i % 3
            row = i // 3
            btn = tk.Button(grid, text=label, font=self.f_btn,
                            bg=C["border"], fg=C["glow_bright"],
                            activebackground=C["glow_dim"],
                            activeforeground=C["void"],
                            relief="flat", padx=4, pady=5,
                            cursor="hand2", bd=0,
                            highlightthickness=1,
                            highlightbackground=C["glow_dim"],
                            command=lambda x=intent: self._on_quick(x))
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            grid.grid_columnconfigure(col, weight=1)

            # Hover glow effect
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C["glow_dim"], fg=C["void"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=C["border"], fg=C["glow_bright"]))

    # ── RIGHT Panel ───────────────────────────────────────────────────────────

    def _build_right(self, parent):
        self._section_header(parent, "ACTIVITY LOG")

        log_outer = tk.Frame(parent, bg=C["border"])
        log_outer.pack(fill="both", expand=True, padx=8, pady=4)

        self._log_text = tk.Text(log_outer, bg=C["void"],
                                 fg=C["text_lo"], font=self.f_small,
                                 relief="flat", state="disabled",
                                 wrap="word", bd=0,
                                 highlightthickness=0)
        self._log_text.pack(fill="both", expand=True, padx=2, pady=2)
        self._log_text.tag_config("ts",   foreground=C["glow_dim"])
        self._log_text.tag_config("cmd",  foreground=C["glow_bright"])
        self._log_text.tag_config("resp", foreground=C["text_lo"])

        # Reminders section
        self._section_header(parent, "PENDING REMINDERS")
        self._reminder_lbl = tk.Label(parent, text="No pending reminders",
                                      bg=C["panel"], fg=C["text_lo"],
                                      font=self.f_small, justify="left",
                                      wraplength=200)
        self._reminder_lbl.pack(anchor="w", padx=12, pady=4)

        # System signals
        self._section_header(parent, "SYS SIGNALS")
        self._signals_canvas = tk.Canvas(parent, height=60, bg=C["panel"],
                                         highlightthickness=0)
        self._signals_canvas.pack(fill="x", padx=8, pady=4)
        self._signal_t = 0
        self._draw_signals()

        # Bottom status
        tk.Frame(parent, height=1, bg=C["glow_dim"]).pack(fill="x", pady=4)
        ver_lbl = tk.Label(parent, text="v2.0  ·  CLASSIFIED",
                           bg=C["panel"], fg=C["text_mute"], font=self.f_small)
        ver_lbl.pack(pady=4)

    # ── Chat methods ──────────────────────────────────────────────────────────

    def _on_chat_resize(self, event):
        self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self._chat_canvas.itemconfig(self._chat_window, width=event.width)

    def add_user_message(self, text: str):
        self.root.after(0, self._add_msg, text, "user")

    def add_max_message(self, text: str):
        self.root.after(0, self._add_msg, text, "max")

    def _add_msg(self, text: str, sender: str):
        frame = tk.Frame(self._chat_frame, bg=C["max_bg"], pady=3)
        frame.pack(fill="x", padx=4)

        if sender == "user":
            prefix = f"[ {USER_NAME.upper()} ] ►"
            lbl_col = C["teal"]
            bg_col  = C["user_bg"]
        else:
            prefix = f"[ {ASSISTANT_NAME} ] ◉"
            lbl_col = C["glow_bright"]
            bg_col  = C["max_bg"]

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        header = tk.Frame(frame, bg=bg_col)
        header.pack(fill="x")
        tk.Label(header, text=prefix, bg=bg_col, fg=lbl_col,
                 font=self.f_small).pack(side="left", padx=(6, 0))
        tk.Label(header, text=ts, bg=bg_col, fg=C["text_mute"],
                 font=self.f_small).pack(side="right", padx=6)

        bubble = tk.Frame(frame, bg=bg_col, padx=10, pady=6,
                          highlightthickness=1,
                          highlightbackground=C["border"])
        bubble.pack(fill="x", padx=4, pady=(0, 2))
        tk.Label(bubble, text=text, bg=bg_col, fg=C["text_hi"],
                 font=self.f_chat, justify="left", wraplength=480,
                 anchor="w").pack(fill="x")

        # Also log to activity panel
        self._log_activity(sender, text[:60] + ("…" if len(text) > 60 else ""))

        self.root.after(50, self._scroll_chat)

    def _scroll_chat(self):
        self._chat_canvas.yview_moveto(1.0)

    def _log_activity(self, sender: str, text: str):
        ts = datetime.datetime.now().strftime("%H:%M")
        try:
            self._log_text.config(state="normal")
            self._log_text.insert("end", f"[{ts}] ", "ts")
            tag = "cmd" if sender == "user" else "resp"
            self._log_text.insert("end", f"{text}\n", tag)
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        except Exception:
            pass

    # ── State & Notification ──────────────────────────────────────────────────

    def set_state(self, state: str):
        self._state = state
        self._reactor.set_state(state)
        labels = {"idle": "● STANDBY", "listening": "◉ LISTENING",
                  "thinking": "◈ PROCESSING", "speaking": "▶ SPEAKING"}
        col = {"idle": C["glow_dim"], "listening": C["glow_bright"],
               "thinking": C["gold"], "speaking": C["teal"]}.get(state, C["text_lo"])
        try:
            self._status_lbl.config(text=labels.get(state, "ONLINE"), fg=col)
        except Exception:
            pass

    def show_notification(self, text: str, duration_ms: int = 3000):
        try:
            self._status_lbl.config(text=f"⚡ {text}", fg=C["gold"])
            self.root.after(duration_ms, lambda: self._status_lbl.config(
                text="● STANDBY", fg=C["glow_dim"]))
        except Exception:
            pass

    # ── Input handlers ────────────────────────────────────────────────────────

    def _on_submit(self, event=None):
        text = self._input_var.get().strip()
        if text and self.on_text_submit:
            self._input_var.set("")
            self.add_user_message(text)
            threading.Thread(target=self.on_text_submit, args=(text,), daemon=True).start()

    def _on_mic(self):
        if self.on_listen_click:
            threading.Thread(target=self.on_listen_click, daemon=True).start()

    def _on_quick(self, intent: str):
        if self.on_quick_action:
            threading.Thread(target=self.on_quick_action, args=(intent,), daemon=True).start()

    # ── Signals animation (right panel) ──────────────────────────────────────

    def _draw_signals(self):
        try:
            c = self._signals_canvas
            c.delete("all")
            w = c.winfo_width() or 200
            h = 60
            pts = []
            for x in range(0, w, 3):
                y = h // 2 + math.sin((x + self._signal_t) * 0.12) * 12 \
                           + math.sin((x + self._signal_t) * 0.27) * 6
                pts.extend([x, y])
            if len(pts) >= 4:
                c.create_line(*pts, fill=C["glow_bright"], width=1, smooth=True)
            self._signal_t += 4
            c.after(80, self._draw_signals)
        except Exception:
            pass

    # ── Live Clock ────────────────────────────────────────────────────────────

    def _start_clock(self):
        def _tick():
            now = datetime.datetime.now()
            try:
                self._clock_lbl.config(text=now.strftime("%H:%M:%S"))
                self._date_lbl.config(text=now.strftime("%A\n%d %B %Y"))
            except Exception:
                pass
            self.root.after(1000, _tick)
        self.root.after(0, _tick)

    # ── System Monitor ────────────────────────────────────────────────────────

    def _start_sys_monitor(self):
        def _update():
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                self._cpu_gauge.set_value(cpu)
                self._ram_gauge.set_value(ram)

                bat = psutil.sensors_battery()
                if bat:
                    self._bat_gauge.set_value(bat.percent)

                du = psutil.disk_usage("/")
                self._disk_lbl.config(
                    text=f"Disk: {du.percent:.0f}% used\n"
                         f"Free: {du.free // (1024**3)} GB")

                ni = psutil.net_io_counters()
                self._net_lbl.config(
                    text=f"▲ {ni.bytes_sent // 1024} KB\n"
                         f"▼ {ni.bytes_recv // 1024} KB")
            except Exception:
                pass
            self.root.after(3000, _update)

        self.root.after(500, _update)

    # ── Reminder Panel ────────────────────────────────────────────────────────

    def update_reminders(self, items: list):
        def _do():
            try:
                if items:
                    text = "\n".join(f"◆ {it}" for it in items[:5])
                else:
                    text = "No pending reminders"
                self._reminder_lbl.config(text=text)
            except Exception:
                pass
        self.root.after(0, _do)

    # ── Callback Registration ─────────────────────────────────────────────────

    def register(self, event: str, callback):
        """
        Wire main.py callbacks into the GUI.
        Supported events:
          'on_query'          → called with text when user submits input
          'on_listen_trigger' → called when mic button clicked
          'on_quick_action'   → called with intent name for quick-action buttons
          'on_close'          → called when the window is closed
        """
        if event == "on_query":
            self.on_text_submit = callback
        elif event == "on_listen_trigger":
            self.on_listen_click = callback
        elif event == "on_quick_action":
            self.on_quick_action = callback
        elif event == "on_close":
            def _close():
                callback()
                self.root.destroy()
            self.root.protocol("WM_DELETE_WINDOW", _close)

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self, on_ready=None):
        """Start the GUI mainloop. Blocks until window closed."""
        self._reactor.start()
        if on_ready:
            self.root.after(200, on_ready)
        self.root.mainloop()
