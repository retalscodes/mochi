# 🍡 mochi

A soft, tiny focus timer widget for your desktop — built for ADHD brains.

![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-pink?style=flat-square)

## features

- 🍅 **Pomodoro presets** — 20/10, 25/5, 40/20, 50/10, or fully custom
- 🔁 **Configurable rounds** — set how many cycles before you're done
- 📌 **Task intent prompt** — name what you're working on before each session
- 💤 **Enforced breaks** — no skipping, rest is part of the work
- 🔥 **Session streak** — counts your completed sessions today
- 🔔 **Gentle audio cues** — soft ascending/descending chords, no jarring alarms
- 📋 **Built-in checklist** — add, check off, and clear tasks without leaving the widget
- 🌌 **Aurora animated background** — slowly shifting blobs of color, calming to look at
- 🖱️ **Draggable + always on top** — sits wherever you want on screen

## requirements

- Python 3.10+
- No external libraries — pure stdlib + tkinter

## usage

```bash
python mochi.py
```

To run without a terminal window opening:

```bash
pythonw mochi.py
```

To pin it to startup, create a shortcut pointing to `pythonw mochi.py`.
