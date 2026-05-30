import tkinter as tk
import math, random, colorsys, threading, winsound
import urllib.request, json, subprocess, sys

# ── PYGAME AUTO-INSTALL ──────────────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()
    HAS_MUSIC = True
except ImportError:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pygame", "-q"],
                       capture_output=True, check=True)
        import pygame
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.mixer.init()
        HAS_MUSIC = True
    except Exception:
        HAS_MUSIC = False
except Exception:
    HAS_MUSIC = False

BREAK_PROMPTS = [
    "💧  drink some water",
    "🧘  take 3 deep breaths",
    "👀  look 20 ft away for 20 sec",
    "🤸  stretch your neck & shoulders",
    "🚶  stand up and walk around",
    "😌  close your eyes a moment",
    "🙌  shake out your hands & wrists",
    "🍎  have a small snack",
    "📵  step away from the screen",
    "☀️  step outside if you can",
]

RADIO_TAGS = {
    "🎵 Lofi":      "lofi",
    "🎷 Jazz":      "jazz",
    "🎻 Classical": "classical",
    "🌿 Ambient":   "ambient",
}


class Pomodoro:
    PRESETS = [("20 / 10", 20, 10), ("25 / 5", 25, 5),
               ("40 / 20", 40, 20), ("50 / 10", 50, 10)]

    THEMES = {
        "purple": {"hue": 0.72, "acc": "#9d8fff", "bg": "#0a0a1c", "label": "✨ Purple"},
        "ocean":  {"hue": 0.59, "acc": "#5eb8ff", "bg": "#040e1a", "label": "🌊 Ocean"},
        "forest": {"hue": 0.37, "acc": "#6fcf7e", "bg": "#04140a", "label": "🌿 Forest"},
        "sakura": {"hue": 0.93, "acc": "#ff8fbc", "bg": "#180810", "label": "🌸 Sakura"},
        "sunset": {"hue": 0.07, "acc": "#ffaa55", "bg": "#180c04", "label": "🌅 Sunset"},
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        self.W, self.H = 320, 410
        self._nW, self._nH = self.W, self.H          # saved normal size
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{sw-self.W-24}+{sh-self.H-64}")

        # state
        self.state      = "idle"
        self.mini       = False
        self.theme_key  = "purple"
        self.focus_m    = tk.IntVar(value=25)
        self.break_m    = tk.IntVar(value=5)
        self.rounds     = tk.IntVar(value=4)
        self.task       = tk.StringVar()
        self.round_n    = 0
        self.streak     = 0
        self.checklist  = []
        self.tl = 0
        self.tt = 1
        self.paused     = False
        self._job       = None
        self.time_id    = None
        self.streak_id  = None
        self.pause_btn  = None

        # music
        self.stations      = {}
        self.station_idx   = {}
        self.current_tag   = None
        self.music_playing = False
        self.music_loading = False
        self.music_volume  = 0.7

        # aurora
        random.seed()
        self.t = 0.0
        self.blobs = [{
            "x":  random.random(), "y":  random.random(),
            "vx": (random.random() - .5) * .0025,
            "vy": (random.random() - .5) * .0025,
            "r":  .22 + random.random() * .22,
            "ph": random.random() * 6.28,
        } for _ in range(6)]

        self.cv = tk.Canvas(self.root, bg="#0a0a1c", highlightthickness=0,
                            width=self.W, height=self.H)
        self.cv.pack(fill="both", expand=True)

        self._ox = self._oy = 0
        self.cv.bind("<ButtonPress-1>",   self._drag_start)
        self.cv.bind("<B1-Motion>",       self._drag_move)
        self.cv.bind("<Double-Button-1>", self._on_dbl)

        self._tick_anim()
        self._show_idle()
        self.root.mainloop()

    # ── THEME ────────────────────────────────────────────────────────────────────

    @property
    def theme(self):
        return self.THEMES[self.theme_key]

    def _hue(self):
        base = self.theme["hue"]
        off  = {"focus": -.09, "break": -.30, "done": -.17, "music": -.05}
        return (base + off.get(self.state, 0)) % 1.0

    # ── ANIMATION ────────────────────────────────────────────────────────────────

    def _tick_anim(self):
        self.t += .018
        h0 = self._hue()
        self.cv.config(bg=self.theme["bg"])
        self.cv.delete("bg")

        for bl in self.blobs:
            bl["x"] += bl["vx"] + .0008 * math.sin(self.t * .5 + bl["ph"])
            bl["y"] += bl["vy"] + .0006 * math.cos(self.t * .4 + bl["ph"])
            if not (-.25 < bl["x"] < 1.25): bl["vx"] *= -1
            if not (-.25 < bl["y"] < 1.25): bl["vy"] *= -1
            hue = (h0 + .18 * math.sin(self.t * .2 + bl["ph"])) % 1.0
            val = .38 + .10 * math.sin(self.t * .3 + bl["ph"])
            r, g, b = colorsys.hsv_to_rgb(hue, .65, val)
            c   = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            cx  = int(bl["x"] * self.W)
            cy  = int(bl["y"] * self.H)
            rad = int(bl["r"] * self.W)
            self.cv.create_oval(cx-rad, cy-rad, cx+rad, cy+rad,
                                fill=c, outline="", tags="bg")

        self.cv.create_rectangle(0, 0, self.W, self.H,
                                 fill="#000000", outline="", stipple="gray50", tags="bg")

        if self.mini:
            self._draw_mini()
        else:
            if self.state in ("focus", "break") and self.tt > 0:
                self._draw_ring()
            self.cv.tag_raise("ui")

        self.cv.after(18, self._tick_anim)

    def _draw_ring(self):
        cx, cy, r = self.W // 2, 185, 85
        self.cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                           start=90, extent=359.9,
                           outline="#333355", width=10, style="arc", tags="bg")
        col = self.theme["acc"] if self.state == "focus" else "#81c784"
        ext = max(1.0, 360 * (self.tl / self.tt))
        self.cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                           start=90, extent=ext,
                           outline=col, width=10, style="arc", tags="bg")

    # ── MINI MODE ────────────────────────────────────────────────────────────────

    def _draw_mini(self):
        self.cv.delete("ui")
        acc  = self.theme["acc"]
        cats = ["(=^ω^=)", "(=^-^=)", "( =ω= )", "(=^•^=)"]
        cat  = cats[int(self.t * 0.8) % len(cats)]
        self.cv.create_text(32, self.H // 2, text=cat,
                            font=("Segoe UI", 10), fill=acc, anchor="center", tags="ui")
        if self.state in ("focus", "break"):
            label = "FOCUS" if self.state == "focus" else "BREAK"
            self.cv.create_text(self.W // 2, 13,
                                text=label, font=("Segoe UI", 7, "bold"),
                                fill=acc, anchor="center", tags="ui")
            self.cv.create_text(self.W // 2, self.H // 2,
                                text=self._fmt(self.tl),
                                font=("Segoe UI", 15, "bold"),
                                fill="white", anchor="center", tags="ui")
            frac = self.tl / self.tt if self.tt else 0
            for i in range(10):
                x = self.W // 2 - 44 + i * 10
                filled = i < int(frac * 10)
                self.cv.create_oval(x-3, self.H-14, x+3, self.H-8,
                                    fill=acc if filled else "#333355",
                                    outline="", tags="ui")
        else:
            self.cv.create_text(self.W // 2, self.H // 2, text="mochi 🍡",
                                font=("Segoe UI", 11, "bold"),
                                fill="white", anchor="center", tags="ui")
        self.cv.create_text(self.W - 10, 10, text="⛶",
                            font=("Segoe UI", 9), fill="#555577",
                            anchor="ne", tags="ui")

    def _go_mini(self):
        self._nW, self._nH = self.W, self.H
        self.mini = True
        self.W, self.H = 230, 68
        self._clear()
        self.root.geometry(f"{self.W}x{self.H}")
        self.cv.config(width=self.W, height=self.H)

    def _go_normal(self):
        self.mini = False
        self.W, self.H = self._nW, self._nH
        self.root.geometry(f"{self.W}x{self.H}")
        self.cv.config(width=self.W, height=self.H)
        redraw = {
            "idle": self._show_idle, "setup": self._show_setup,
            "focus": self._render_timer, "break": self._render_timer,
            "done": self._show_done, "checklist": self._show_checklist,
            "music": self._show_music, "settings": self._show_settings,
        }
        redraw.get(self.state, self._show_idle)()

    def _on_dbl(self, _):
        if self.mini:
            self._go_normal()

    # ── HELPERS ──────────────────────────────────────────────────────────────────

    def _clear(self):
        self.cv.delete("ui")
        for w in self.cv.winfo_children():
            w.destroy()

    def _txt(self, x, y, text, size=12, bold=False, color="white", anchor="center"):
        self.cv.create_text(x, y, text=text,
                            font=("Segoe UI", size, "bold" if bold else "normal"),
                            fill=color, anchor=anchor, tags="ui")

    def _btn(self, text, cmd, x, y, w=120, h=34, bg="#2a2a4a", fg="white", size=10):
        b = tk.Button(self.root, text=text, command=cmd,
                      font=("Segoe UI", size), bg=bg, fg=fg, relief="flat",
                      activebackground="#555588", activeforeground="white",
                      bd=0, cursor="hand2")
        self.cv.create_window(x, y, window=b, width=w, height=h, tags="ui")
        return b

    def _close_btn(self):
        self._btn("✕", self.root.destroy, self.W-22, 14, w=24, h=20,
                  bg="#222233", fg="#888899", size=8)

    def _mini_btn(self):
        self._btn("▂", self._go_mini, self.W-46, 14, w=24, h=20,
                  bg="#222233", fg="#888899", size=8)

    # ── IDLE ─────────────────────────────────────────────────────────────────────

    def _show_idle(self):
        self._cancel_timer()
        self.state = "idle"
        self._clear()
        acc = self.theme["acc"]

        self._txt(self.W//2, 26, "🍡  mochi", 16, bold=True, color=acc)
        self._txt(self.W//2, 50, f"🔥  {self.streak} sessions today", 9, color="#aaaadd")
        self._txt(self.W//2, 76, "Quick start", 9, color="#8888bb")

        for i, (lbl, fm, bm) in enumerate(self.PRESETS):
            bx = 88 + (i % 2) * 144
            by = 102 + (i // 2) * 44
            self._btn(lbl, lambda f=fm, b=bm: self._pick_preset(f, b),
                      bx, by, w=124, h=32, bg="#2e2e5e")

        self._txt(self.W//2, 192, "or custom", 9, color="#8888bb")

        row = tk.Frame(self.root, bg="#14142e")
        for var, label in [(self.focus_m, "Focus"), (self.break_m, "Break"), (self.rounds, "×")]:
            tk.Label(row, text=label, bg="#14142e", fg="#9999cc",
                     font=("Segoe UI", 8)).pack(side="left", padx=(6, 2))
            tk.Spinbox(row, textvariable=var, from_=1, to=99, width=3,
                       bg="#1e1e40", fg="white", buttonbackground="#2e2e5e",
                       font=("Segoe UI", 10), relief="flat").pack(side="left")
        self.cv.create_window(self.W//2, 218, window=row, tags="ui", height=28, width=252)

        self._btn("▶  Start", self._show_setup, self.W//2, 262, w=144, h=38,
                  bg="#4040a0", size=11)

        done_count = sum(1 for x in self.checklist if x["done"])
        total      = len(self.checklist)
        badge      = f" ({done_count}/{total})" if total else ""
        self._btn(f"📋{badge}", self._show_checklist, self.W//2-90, 314, w=54, h=30, bg="#2a2a50", size=10)
        self._btn("🎵",         self._show_music,     self.W//2,    314, w=54, h=30, bg="#2a2a50", size=10)
        self._btn("⚙",          self._show_settings,  self.W//2+90, 314, w=54, h=30, bg="#2a2a50", size=10)

        self._mini_btn()
        self._close_btn()

    def _pick_preset(self, fm, bm):
        self.focus_m.set(fm)
        self.break_m.set(bm)
        self._show_setup()

    # ── SETUP ────────────────────────────────────────────────────────────────────

    def _show_setup(self):
        self.state = "setup"
        self._clear()

        self._txt(self.W//2, 38,  "What are you working on?", 12, bold=True)
        self._txt(self.W//2, 60,
                  f"{self.focus_m.get()} min focus  ·  {self.break_m.get()} min break  ·  {self.rounds.get()}×",
                  9, color="#9999cc")

        e = tk.Entry(self.root, textvariable=self.task,
                     font=("Segoe UI", 11), bg="#1a1a3a", fg="white",
                     insertbackground="white", relief="flat", justify="center")
        self.cv.create_window(self.W//2, 105, window=e, width=260, height=36, tags="ui")
        e.focus_set()
        e.bind("<Return>", lambda _: self._start_session())

        self._txt(self.W//2, 138, "press Enter or click below", 8, color="#666699")
        self._btn("▶  Let's go", self._start_session, self.W//2, 178, w=150, h=38,
                  bg="#4040a0", size=11)
        self._btn("← Back", self._show_idle, self.W//2, 226, w=90, h=28,
                  bg="#252540", size=9)
        self._mini_btn()
        self._close_btn()

    # ── TIMER ────────────────────────────────────────────────────────────────────

    def _start_session(self):
        self.round_n = 0
        self._begin_focus()

    def _begin_focus(self):
        self.state = "focus"
        self.tl = self.focus_m.get() * 60
        self.tt = self.tl
        self._render_timer()
        self._tick_timer()
        self._play_start()

    def _begin_break(self):
        self.state = "break"
        self.tl = self.break_m.get() * 60
        self.tt = self.tl
        self._render_timer()
        self._tick_timer()
        self._play_break()

    def _render_timer(self):
        self._clear()
        is_focus = self.state == "focus"
        acc = self.theme["acc"]
        col = acc if is_focus else "#81c784"

        self._txt(self.W//2, 26, "FOCUS" if is_focus else "💤  BREAK", 11, bold=True, color=col)
        self._txt(self.W//2, 46, f"Round {self.round_n+1} of {self.rounds.get()}", 9, color="#9999cc")
        task = self.task.get().strip()
        if task:
            display = task if len(task) <= 30 else task[:28] + "…"
            self._txt(self.W//2, 64, f"📌 {display}", 9, color="#ccccff")

        self.time_id = self.cv.create_text(
            self.W//2, 185, text=self._fmt(self.tl),
            font=("Segoe UI", 40, "bold"), fill="white", tags="ui")
        self.streak_id = self.cv.create_text(
            self.W//2, 232, text=f"🔥 {self.streak}",
            font=("Segoe UI", 10), fill="#8888bb", tags="ui")

        if not is_focus:
            prompt = random.choice(BREAK_PROMPTS)
            self._txt(self.W//2, 262, prompt, 9, color="#99bb99")

        btn_y  = 300 if is_focus else 318
        hint_y = 360 if is_focus else 374

        self.pause_btn = self._btn("⏸  Pause", self._toggle_pause,
                                   self.W//2-64, btn_y, w=110, h=34, bg="#2e2e5e")
        self._btn("↺  Reset", self._show_idle,
                  self.W//2+64, btn_y, w=110, h=34, bg="#2e2e40")

        hint = "focus — no skipping" if is_focus else "💤 rest is enforced"
        self._txt(self.W//2, hint_y, hint, 8, color="#555577")

        self._mini_btn()
        self._close_btn()

    def _fmt(self, secs):
        return f"{secs // 60:02d}:{secs % 60:02d}"

    def _update_display(self):
        try:
            self.cv.itemconfig(self.time_id,   text=self._fmt(self.tl))
            self.cv.itemconfig(self.streak_id, text=f"🔥 {self.streak}")
        except Exception:
            pass

    def _tick_timer(self):
        if self.paused:
            self._job = self.cv.after(200, self._tick_timer)
            return
        if self.tl > 0:
            self.tl -= 1
            self._update_display()
            self._job = self.cv.after(1000, self._tick_timer)
        else:
            self._on_done()

    def _on_done(self):
        if self.state == "focus":
            self.streak  += 1
            self.round_n += 1
            if self.round_n >= self.rounds.get():
                self._show_done()
            else:
                self._begin_break()
        else:
            self._begin_focus()

    def _toggle_pause(self):
        self.paused = not self.paused
        try:
            self.pause_btn.config(text="▶  Resume" if self.paused else "⏸  Pause")
        except Exception:
            pass

    def _cancel_timer(self):
        if self._job:
            self.cv.after_cancel(self._job)
            self._job = None
        self.paused = False

    # ── DONE ─────────────────────────────────────────────────────────────────────

    def _show_done(self):
        self.state = "done"
        self._cancel_timer()
        self._clear()
        self._play_done()

        self._txt(self.W//2,  70, "🎉", 36)
        self._txt(self.W//2, 120, "All done!", 20, bold=True)
        self._txt(self.W//2, 152, f"Completed {self.rounds.get()} rounds", 11, color="#9999cc")
        task = self.task.get().strip()
        if task:
            self._txt(self.W//2, 176, f'"{task}"', 9, color="#ccccff")
        self._txt(self.W//2, 215, f"🔥 {self.streak} sessions today",
                  13, bold=True, color="#ffcc44")
        self._btn("▶  New session", self._show_idle,
                  self.W//2, 272, w=154, h=40, bg="#4040a0", size=11)
        self._mini_btn()
        self._close_btn()

    # ── CHECKLIST ────────────────────────────────────────────────────────────────

    def _show_checklist(self):
        self.state = "checklist"
        self._clear()
        acc = self.theme["acc"]

        self._txt(self.W//2, 26, "📋  My List", 14, bold=True)
        done_count = sum(1 for x in self.checklist if x["done"])
        total = len(self.checklist)
        self._txt(self.W//2, 48,
                  f"{done_count} of {total} done" if total else "nothing here yet!",
                  9, color="#8888bb")

        outer   = tk.Frame(self.root, bg="#0e0e26", bd=0)
        list_cv = tk.Canvas(outer, bg="#0e0e26", highlightthickness=0, width=270, height=210)
        sb = tk.Scrollbar(outer, orient="vertical", command=list_cv.yview,
                          bg="#1a1a3a", troughcolor="#0e0e26")
        list_cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        list_cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(list_cv, bg="#0e0e26")
        list_cv.create_window(0, 0, window=inner, anchor="nw", width=270)
        self.cv.create_window(self.W//2, 165, window=outer, width=286, height=210, tags="ui")

        new_text = tk.StringVar()

        def refresh():
            for w in inner.winfo_children():
                w.destroy()
            for i, item in enumerate(self.checklist):
                done  = item["done"]
                color = "#555577" if done else "#ddddff"
                sym   = "✓" if done else "○"
                label = item["text"][:26] + ("…" if len(item["text"]) > 26 else "")
                row = tk.Frame(inner, bg="#0e0e26")
                row.pack(fill="x", padx=4, pady=2)
                tk.Button(row, text=sym, command=lambda i=i: toggle(i),
                          bg="#0e0e26", fg=acc if done else "#6666aa",
                          font=("Segoe UI", 10), relief="flat", bd=0,
                          cursor="hand2", width=2).pack(side="left")
                tk.Label(row, text=label, bg="#0e0e26", fg=color, anchor="w",
                         font=("Segoe UI", 9,
                               "overstrike" if done else "normal")
                         ).pack(side="left", fill="x", expand=True)
                tk.Button(row, text="×", command=lambda i=i: delete(i),
                          bg="#0e0e26", fg="#554455", activeforeground="#ff6666",
                          font=("Segoe UI", 8), relief="flat", bd=0,
                          cursor="hand2").pack(side="right", padx=2)
            inner.update_idletasks()
            list_cv.configure(scrollregion=list_cv.bbox("all"))

        def toggle(i):
            self.checklist[i]["done"] = not self.checklist[i]["done"]
            refresh()

        def delete(i):
            self.checklist.pop(i)
            refresh()

        def add_item():
            text = new_text.get().strip()
            if text:
                self.checklist.append({"text": text, "done": False})
                new_text.set("")
                refresh()

        def clear_done():
            self.checklist = [x for x in self.checklist if not x["done"]]
            refresh()

        list_cv.bind("<MouseWheel>",
                     lambda e: list_cv.yview_scroll(int(-1*(e.delta/120)), "units"))
        inner.bind("<MouseWheel>",
                   lambda e: list_cv.yview_scroll(int(-1*(e.delta/120)), "units"))
        refresh()

        e = tk.Entry(self.root, textvariable=new_text,
                     font=("Segoe UI", 10), bg="#1a1a3a", fg="white",
                     insertbackground="white", relief="flat", justify="left")
        self.cv.create_window(self.W//2-22, 290, window=e, width=224, height=30, tags="ui")
        e.focus_set()
        e.bind("<Return>", lambda _: add_item())
        self._btn("+", add_item, self.W//2+118, 290, w=30, h=30, bg="#4040a0", size=12)

        self._btn("← Back",  self._show_idle, self.W//2-58, 338, w=100, h=28, bg="#252540", size=9)
        self._btn("clear ✓", clear_done,      self.W//2+60, 338, w=96,  h=28,
                  bg="#2a2020", fg="#aa7777", size=8)
        self._mini_btn()
        self._close_btn()

    # ── MUSIC ────────────────────────────────────────────────────────────────────

    def _show_music(self):
        self.state = "music"
        self._clear()
        acc = self.theme["acc"]

        self._txt(self.W//2, 26, "🎵  Radio", 14, bold=True)

        if not HAS_MUSIC:
            self._txt(self.W//2, 130, "pygame not available", 10, color="#aa7777")
            self._txt(self.W//2, 155, "pip install pygame", 9, color="#666688")
            self._btn("← Back", self._show_idle, self.W//2, 210, w=90, h=28,
                      bg="#252540", size=9)
            self._close_btn()
            return

        self._txt(self.W//2, 52, "choose a genre", 9, color="#8888bb")

        tags = list(RADIO_TAGS.items())
        for i, (label, tag) in enumerate(tags):
            bx     = 84 + (i % 2) * 152
            by     = 82 + (i // 2) * 44
            active = (self.current_tag == tag and self.music_playing)
            self._btn(label, lambda t=tag: self._toggle_station(t),
                      bx, by, w=132, h=32,
                      bg="#4040a0" if active else "#2e2e5e")

        self._txt(self.W//2, 184, "now playing", 8, color="#666688")
        name   = ""
        if self.current_tag and self.stations.get(self.current_tag):
            idx  = self.station_idx.get(self.current_tag, 0)
            st   = self.stations[self.current_tag][idx]
            name = st.get("name", "")[:34]
        status = "⏳ loading…" if self.music_loading else (name or "—")
        self._txt(self.W//2, 202, status, 9, color=acc)

        if self.music_playing:
            self._btn("⏹  Stop", self._stop_music,   self.W//2-62, 236, w=110, h=32, bg="#2e2e40")
            self._btn("⏭  Next", self._next_station, self.W//2+62, 236, w=110, h=32, bg="#2e2e5e")

        self._txt(self.W//2, 278, "volume", 8, color="#666688")
        vf = tk.Frame(self.root, bg="#14142e")
        vs = tk.Scale(vf, from_=0, to=100, orient="horizontal",
                      length=210, bg="#14142e", fg=acc,
                      troughcolor="#2a2a4a", highlightthickness=0,
                      showvalue=False, sliderlength=14,
                      command=self._set_volume)
        vs.set(int(self.music_volume * 100))
        vs.pack()
        self.cv.create_window(self.W//2, 298, window=vf, tags="ui", width=230, height=30)

        self._btn("← Back", self._show_idle, self.W//2, 352, w=90, h=28,
                  bg="#252540", size=9)
        self._mini_btn()
        self._close_btn()

    def _toggle_station(self, tag):
        if self.current_tag == tag and self.music_playing:
            self._stop_music()
            return
        self.current_tag = tag
        if self.stations.get(tag):
            self._play_current()
        else:
            self._fetch_and_play(tag)

    def _fetch_and_play(self, tag):
        self.music_loading = True
        self._show_music()

        def fetch():
            try:
                api_tag = RADIO_TAGS[tag]
                url = (f"https://de1.api.radio-browser.info/json/stations/search"
                       f"?tag={api_tag}&limit=12&order=votes&hidebroken=true&codec=MP3")
                with urllib.request.urlopen(url, timeout=7) as r:
                    data = json.loads(r.read())
                self.stations[tag] = [s for s in data if s.get("url_resolved")]
                self.station_idx[tag] = 0
            except Exception:
                self.stations[tag] = []
            self.music_loading = False
            if self.stations.get(tag):
                self.root.after(0, self._play_current)
            else:
                self.root.after(0, self._show_music)

        threading.Thread(target=fetch, daemon=True).start()

    def _play_current(self):
        tag = self.current_tag
        if not tag or not self.stations.get(tag):
            return
        url = self.stations[tag][self.station_idx.get(tag, 0)].get("url_resolved", "")
        if not url:
            return
        self.music_loading = True
        self._show_music()

        def load():
            try:
                pygame.mixer.music.load(url)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(self.music_volume)
                self.music_playing = True
            except Exception:
                self.music_playing = False
            self.music_loading = False
            self.root.after(0, self._show_music)

        threading.Thread(target=load, daemon=True).start()

    def _stop_music(self):
        try: pygame.mixer.music.stop()
        except Exception: pass
        self.music_playing = False
        self._show_music()

    def _next_station(self):
        tag = self.current_tag
        if not tag or not self.stations.get(tag):
            return
        n = len(self.stations[tag])
        self.station_idx[tag] = (self.station_idx.get(tag, 0) + 1) % n
        self._play_current()

    def _set_volume(self, val):
        self.music_volume = int(val) / 100
        try: pygame.mixer.music.set_volume(self.music_volume)
        except Exception: pass

    # ── SETTINGS ─────────────────────────────────────────────────────────────────

    def _show_settings(self):
        self.state = "settings"
        self._clear()
        acc = self.theme["acc"]

        self._txt(self.W//2, 26, "⚙  Settings", 14, bold=True)

        # ── color theme ──────────────────────────────────────────────────────
        self._txt(self.W//2, 54, "color theme", 9, color="#8888bb")
        keys = list(self.THEMES.keys())
        for i, key in enumerate(keys):
            th = self.THEMES[key]
            bx = 64 + (i % 3) * 98
            by = 80 + (i // 3) * 44
            active = self.theme_key == key
            self._btn(th["label"], lambda k=key: self._set_theme(k),
                      bx, by, w=86, h=32,
                      bg="#4040a0" if active else "#2e2e5e",
                      fg=th["acc"] if not active else "white", size=8)

        # ── opacity ──────────────────────────────────────────────────────────
        self._txt(self.W//2, 174, "── window opacity ──", 8, color="#555577")
        # show current % value dynamically
        cur_pct = int(self.root.attributes("-alpha") * 100)
        self.opacity_lbl = self.cv.create_text(
            self.W//2, 196, text=f"{cur_pct}%",
            font=("Segoe UI", 9), fill=acc, tags="ui")

        of = tk.Frame(self.root, bg="#14142e")
        def _on_opacity(v):
            self.root.attributes("-alpha", int(v) / 100)
            try: self.cv.itemconfig(self.opacity_lbl, text=f"{int(v)}%")
            except Exception: pass
        os_ = tk.Scale(of, from_=40, to=100, orient="horizontal",
                       length=230, bg="#14142e", fg=acc,
                       troughcolor="#2a2a4a", highlightthickness=0,
                       showvalue=False, sliderlength=18,
                       command=_on_opacity)
        os_.set(cur_pct)
        os_.pack()
        self.cv.create_window(self.W//2, 220, window=of, tags="ui", width=250, height=34)

        self._btn("← Back", self._show_idle, self.W//2, 282, w=90, h=28,
                  bg="#252540", size=9)
        self._mini_btn()
        self._close_btn()

    def _set_theme(self, key):
        self.theme_key = key
        self.cv.config(bg=self.THEMES[key]["bg"])
        self._show_settings()

    # ── SOUND ────────────────────────────────────────────────────────────────────

    def _beep(self, seq):
        def _play():
            for freq, dur in seq:
                try: winsound.Beep(freq, dur)
                except Exception: pass
        threading.Thread(target=_play, daemon=True).start()

    def _play_start(self): self._beep([(523,80),(659,80),(784,120)])
    def _play_break(self): self._beep([(784,80),(659,80),(523,120)])
    def _play_done(self):  self._beep([(523,80),(659,80),(784,80),(1047,200)])

    # ── DRAG ─────────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._ox, self._oy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._ox
        y = self.root.winfo_y() + e.y - self._oy
        self.root.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    Pomodoro()
