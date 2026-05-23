import tkinter as tk
import math, random, colorsys, threading, winsound

class Pomodoro:
    PRESETS = [("20 / 10", 20, 10), ("25 / 5", 25, 5), ("40 / 20", 40, 20), ("50 / 10", 50, 10)]

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        self.W, self.H = 320, 410
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{sw - self.W - 24}+{sh - self.H - 64}")

        self.state   = "idle"
        self.focus_m = tk.IntVar(value=25)
        self.break_m = tk.IntVar(value=5)
        self.rounds  = tk.IntVar(value=4)
        self.task    = tk.StringVar()
        self.round_n  = 0
        self.streak   = 0
        self.checklist = []  # list of {"text": str, "done": bool}
        self.tl = 0
        self.tt = 1
        self.paused  = False
        self._job    = None
        self.time_id = None
        self.streak_id = None
        self.pause_btn = None

        # aurora blobs
        random.seed()
        self.t = 0.0
        self.blobs = [{
            "x": random.random(), "y": random.random(),
            "vx": (random.random() - .5) * .0025,
            "vy": (random.random() - .5) * .0025,
            "r":  .22 + random.random() * .22,
            "ph": random.random() * 6.28,
        } for _ in range(6)]

        self.cv = tk.Canvas(self.root, bg="#0a0a1c", highlightthickness=0,
                            width=self.W, height=self.H)
        self.cv.pack(fill="both", expand=True)

        self._ox = self._oy = 0
        self.cv.bind("<ButtonPress-1>", self._drag_start)
        self.cv.bind("<B1-Motion>",     self._drag_move)

        self._tick_anim()
        self._show_idle()
        self.root.mainloop()

    # ── ANIMATION ────────────────────────────────────────────────────────────────

    def _hue(self):
        return {"focus": .63, "break": .40, "done": .55, "checklist": .50}.get(self.state, .72)

    def _tick_anim(self):
        self.t += .018
        h0 = self._hue()
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

        # dark vignette overlay
        self.cv.create_rectangle(0, 0, self.W, self.H,
                                 fill="#000000", outline="", stipple="gray50", tags="bg")

        if self.state in ("focus", "break") and self.tt > 0:
            self._draw_ring()

        self.cv.tag_raise("ui")
        self.cv.after(18, self._tick_anim)

    def _draw_ring(self):
        cx, cy, r = self.W // 2, 185, 85
        self.cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                           start=90, extent=359.9,
                           outline="#333355", width=10, style="arc", tags="bg")
        col = "#64b5f6" if self.state == "focus" else "#81c784"
        ext = max(1.0, 360 * (self.tl / self.tt))
        self.cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                           start=90, extent=ext,
                           outline=col, width=10, style="arc", tags="bg")

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
        self._btn("✕", self.root.destroy, self.W - 22, 14, w=24, h=20,
                  bg="#222233", fg="#888899", size=8)

    # ── SCREENS ──────────────────────────────────────────────────────────────────

    def _show_idle(self):
        self._cancel_timer()
        self.state = "idle"
        self._clear()

        self._txt(self.W//2, 28,  "🍅  Focus Timer", 15, bold=True)
        self._txt(self.W//2, 52,  f"🔥  {self.streak} sessions today", 9, color="#aaaadd")
        self._txt(self.W//2, 82,  "Quick start", 9, color="#8888bb")

        for i, (lbl, fm, bm) in enumerate(self.PRESETS):
            bx = 88 + (i % 2) * 144
            by = 108 + (i // 2) * 46
            self._btn(lbl, lambda f=fm, b=bm: self._pick_preset(f, b),
                      bx, by, w=124, h=34, bg="#2e2e5e")

        self._txt(self.W//2, 205, "or set custom", 9, color="#8888bb")

        row = tk.Frame(self.root, bg="#14142e")
        for var, label in [(self.focus_m, "Focus"), (self.break_m, "Break"), (self.rounds, "×")]:
            tk.Label(row, text=label, bg="#14142e", fg="#9999cc",
                     font=("Segoe UI", 8)).pack(side="left", padx=(6, 2))
            tk.Spinbox(row, textvariable=var, from_=1, to=99, width=3,
                       bg="#1e1e40", fg="white", buttonbackground="#2e2e5e",
                       font=("Segoe UI", 10), relief="flat").pack(side="left")
        self.cv.create_window(self.W//2, 232, window=row, tags="ui", height=28, width=252)

        self._btn("▶  Start", self._show_setup, self.W//2, 268, w=144, h=40,
                  bg="#4040a0", size=11)
        done_count = sum(1 for x in self.checklist if x["done"])
        total      = len(self.checklist)
        badge      = f"  ({done_count}/{total})" if total else ""
        self._btn(f"📋  My List{badge}", self._show_checklist,
                  self.W//2, 322, w=144, h=32, bg="#2a2a50", size=9)
        self._close_btn()

    def _pick_preset(self, fm, bm):
        self.focus_m.set(fm)
        self.break_m.set(bm)
        self._show_setup()

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
        self._close_btn()

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
        col = "#64b5f6" if is_focus else "#81c784"

        self._txt(self.W//2, 26,  "FOCUS" if is_focus else "💤  BREAK", 11, bold=True, color=col)
        self._txt(self.W//2, 46,
                  f"Round {self.round_n + 1} of {self.rounds.get()}", 9, color="#9999cc")
        task = self.task.get().strip()
        if task:
            # truncate long task names
            display = task if len(task) <= 30 else task[:28] + "…"
            self._txt(self.W//2, 64, f"📌 {display}", 9, color="#ccccff")

        self.time_id = self.cv.create_text(
            self.W//2, 185,
            text=self._fmt(self.tl),
            font=("Segoe UI", 40, "bold"), fill="white", tags="ui"
        )
        self.streak_id = self.cv.create_text(
            self.W//2, 232,
            text=f"🔥 {self.streak}",
            font=("Segoe UI", 10), fill="#8888bb", tags="ui"
        )

        self.pause_btn = self._btn(
            "⏸  Pause", self._toggle_pause,
            self.W//2 - 64, 298, w=110, h=34, bg="#2e2e5e"
        )
        self._btn("↺  Reset", self._show_idle,
                  self.W//2 + 64, 298, w=110, h=34, bg="#2e2e40")

        hint = "focus — no skipping ahead" if is_focus else "💤 enforced rest — breathe"
        self._txt(self.W//2, 348, hint, 8, color="#555577")
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

    def _show_done(self):
        self.state = "done"
        self._cancel_timer()
        self._clear()
        self._play_done()

        self._txt(self.W//2,  70, "🎉", 36)
        self._txt(self.W//2, 120, "All done!", 20, bold=True)
        self._txt(self.W//2, 152,
                  f"Completed {self.rounds.get()} rounds", 11, color="#9999cc")
        task = self.task.get().strip()
        if task:
            self._txt(self.W//2, 176, f'“{task}”', 9, color="#ccccff")
        self._txt(self.W//2, 215,
                  f"🔥 {self.streak} sessions today", 13, bold=True, color="#ffcc44")

        self._btn("▶  New session", self._show_idle,
                  self.W//2, 272, w=154, h=40, bg="#4040a0", size=11)
        self._close_btn()

    # ── CHECKLIST ────────────────────────────────────────────────────────────────

    def _show_checklist(self):
        self.state = "checklist"
        self._clear()

        self._txt(self.W//2, 26, "📋  My List", 14, bold=True)

        done_count = sum(1 for x in self.checklist if x["done"])
        total      = len(self.checklist)
        self._txt(self.W//2, 48,
                  f"{done_count} of {total} done" if total else "nothing here yet — add something!",
                  9, color="#8888bb")

        # ── scrollable list ──────────────────────────────────────────────────────
        outer = tk.Frame(self.root, bg="#0e0e26", bd=0)
        list_cv = tk.Canvas(outer, bg="#0e0e26", highlightthickness=0, width=270, height=218)
        sb = tk.Scrollbar(outer, orient="vertical", command=list_cv.yview,
                          bg="#1a1a3a", troughcolor="#0e0e26")
        list_cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        list_cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(list_cv, bg="#0e0e26")
        inner_id = list_cv.create_window(0, 0, window=inner, anchor="nw", width=270)
        self.cv.create_window(self.W//2, 170, window=outer, width=286, height=218, tags="ui")

        new_text = tk.StringVar()

        def refresh():
            for w in inner.winfo_children():
                w.destroy()
            for i, item in enumerate(self.checklist):
                done  = item["done"]
                color = "#555577" if done else "#ddddff"
                sym   = "✓" if done else "○"
                label = item["text"]
                if len(label) > 26:
                    label = label[:24] + "…"

                row = tk.Frame(inner, bg="#0e0e26")
                row.pack(fill="x", padx=4, pady=2)

                tk.Button(row, text=sym, command=lambda i=i: toggle(i),
                          bg="#0e0e26", fg="#64b5f6" if done else "#6666aa",
                          font=("Segoe UI", 10), relief="flat", bd=0,
                          cursor="hand2", width=2).pack(side="left")
                tk.Label(row, text=label, bg="#0e0e26", fg=color, anchor="w",
                         font=("Segoe UI", 9, "overstrike" if done else "normal")
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

        # bind mousewheel scrolling
        def _on_wheel(e):
            list_cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
        list_cv.bind("<MouseWheel>", _on_wheel)
        inner.bind("<MouseWheel>", _on_wheel)

        refresh()

        # ── add item row ─────────────────────────────────────────────────────────
        e = tk.Entry(self.root, textvariable=new_text,
                     font=("Segoe UI", 10), bg="#1a1a3a", fg="white",
                     insertbackground="white", relief="flat", justify="left")
        self.cv.create_window(self.W//2 - 22, 300, window=e, width=224, height=30, tags="ui")
        e.focus_set()
        e.bind("<Return>", lambda _: add_item())
        self._btn("+", add_item, self.W//2 + 118, 300, w=30, h=30, bg="#4040a0", size=12)

        # ── bottom row ───────────────────────────────────────────────────────────
        self._btn("← Back", self._show_idle,  self.W//2 - 58, 348, w=100, h=28, bg="#252540", size=9)
        self._btn("clear done", clear_done,   self.W//2 + 60, 348, w=96,  h=28, bg="#2a2020", fg="#aa7777", size=8)
        self._close_btn()

    # ── SOUND ────────────────────────────────────────────────────────────────────

    def _beep(self, seq):
        def _play():
            for freq, dur in seq:
                try: winsound.Beep(freq, dur)
                except Exception: pass
        threading.Thread(target=_play, daemon=True).start()

    def _play_start(self):
        self._beep([(523, 80), (659, 80), (784, 120)])      # C E G — focus chord

    def _play_break(self):
        self._beep([(784, 80), (659, 80), (523, 120)])      # G E C — descend, relax

    def _play_done(self):
        self._beep([(523,80),(659,80),(784,80),(1047,200)])  # celebration arpeggio

    # ── DRAG ─────────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._ox, self._oy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._ox
        y = self.root.winfo_y() + e.y - self._oy
        self.root.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    Pomodoro()
