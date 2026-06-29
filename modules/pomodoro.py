import json
import math
import os
import re
import subprocess

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import GLib, Gtk, Pango, PangoCairo
import cairo

from fabric.widgets.box import Box
from fabric.widgets.label import Label

import modules.icons as icons

_COLORS_FILE = os.path.expanduser("~/.config/Ax-Shell/assets/colors.css")
_CONFIG_FILE  = os.path.expanduser("~/.pomodoro.json")

SESSIONS_BEFORE_LONG = 4

_SOUND_WORK_DONE  = "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"
_SOUND_BREAK_DONE = "/usr/share/sounds/freedesktop/stereo/complete.oga"


# ── config ────────────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    try:
        raw = json.loads(open(_CONFIG_FILE).read())
        return {
            "work_mins":  max(1, min(180, int(raw.get("work_mins",  50)))),
            "short_mins": max(1, min(60,  int(raw.get("short_mins", 10)))),
            "long_mins":  max(1, min(180, int(raw.get("long_mins",  30)))),
        }
    except Exception:
        return {"work_mins": 50, "short_mins": 10, "long_mins": 30}


def _save_cfg(cfg: dict):
    try:
        open(_CONFIG_FILE, "w").write(json.dumps(cfg))
    except Exception:
        pass


# ── color helpers ─────────────────────────────────────────────────────────────

def _read_colors() -> dict:
    colors = {}
    try:
        for m in re.finditer(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", open(_COLORS_FILE).read()):
            colors[m.group(1)] = m.group(2)
    except Exception:
        pass
    return colors


def _hex_rgba(h, a=1.0):
    h = h.lstrip("#")
    return int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255, a


# ── ring ──────────────────────────────────────────────────────────────────────

class _Ring(Gtk.DrawingArea):
    SIZE = 230

    def __init__(self):
        super().__init__()
        self._mode      = "work"
        self._progress  = 0.0
        self._time_str  = "50:00"
        self._state_str = "FOCUS"
        self._done      = False
        self.set_size_request(self.SIZE, self.SIZE)
        self.set_hexpand(False)
        self.set_vexpand(False)
        self.connect("draw", self._on_draw)

    def refresh(self, mode, progress, time_str, state_str, done=False):
        self._mode, self._progress = mode, max(0.0, min(1.0, progress))
        self._time_str, self._state_str, self._done = time_str, state_str, done
        self.queue_draw()

    def _arc_color(self, c):
        if self._done:
            return _hex_rgba(c.get("outline", "#948f99"), 0.6)
        return _hex_rgba(c.get(
            {"work": "primary", "short_break": "green"}.get(self._mode, "secondary"),
            "#d0bcfe"))

    def _on_draw(self, widget, cr):
        alloc = widget.get_allocation()
        w, h  = alloc.width, alloc.height
        cx, cy = w / 2.0, h / 2.0
        ring_r = min(w, h) / 2.0 - 18.0
        stroke = 10.0

        c   = _read_colors()
        track = _hex_rgba(c.get("surface-bright", "#3b383e"), 0.5)
        fg    = _hex_rgba(c.get("foreground",     "#e6e0e8"))
        arc   = self._arc_color(c)

        cr.set_line_width(stroke)
        cr.set_source_rgba(*track)
        cr.arc(cx, cy, ring_r, 0, 2 * math.pi)
        cr.stroke()

        sa = -math.pi / 2
        if self._progress > 0.002:
            ea = sa + 2 * math.pi * self._progress
            for extra, alpha in ((12, 0.10), (4, 0.20)):
                cr.set_line_width(stroke + extra)
                cr.set_source_rgba(arc[0], arc[1], arc[2], alpha)
                cr.arc(cx, cy, ring_r, sa, ea); cr.stroke()
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_width(stroke)
            cr.set_source_rgba(*arc)
            cr.arc(cx, cy, ring_r, sa, ea); cr.stroke()

        sl = PangoCairo.create_layout(cr)
        sl.set_text(self._state_str, -1)
        sl.set_font_description(Pango.FontDescription("Sans 12"))
        sl_w, sl_h = sl.get_pixel_size()

        tl = PangoCairo.create_layout(cr)
        tl.set_text(self._time_str, -1)
        tl.set_font_description(Pango.FontDescription("Sans Bold 36"))
        tl_w, tl_h = tl.get_pixel_size()

        top = cy - (sl_h + 4 + tl_h) / 2.0

        cr.move_to(cx - sl_w / 2.0, top)
        cr.set_source_rgba(arc[0], arc[1], arc[2], 0.85)
        PangoCairo.show_layout(cr, sl)

        cr.move_to(cx - tl_w / 2.0, top + sl_h + 4)
        cr.set_source_rgba(*fg)
        PangoCairo.show_layout(cr, tl)

        return False


# ── custom time selector ──────────────────────────────────────────────────────

class _TimeSelector(Gtk.Box):
    """Pill-shaped  [−]  value  [+]  control with a label above."""

    def __init__(self, heading: str, value: int, lo: int, hi: int, on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self._value    = value
        self._lo, self._hi = lo, hi
        self._on_change = on_change
        self._repeat_id = None

        head = Gtk.Label(label=heading)
        head.set_name("pomo-ts-head")

        self._val_lbl = Gtk.Label(label=str(value))
        self._val_lbl.set_name("pomo-ts-value")

        minus = Gtk.Button(label="−")
        minus.set_name("pomo-ts-btn")
        minus.connect("clicked",  self._dec)
        minus.connect("pressed",  self._start_repeat, -1)
        minus.connect("released", self._stop_repeat)

        plus = Gtk.Button(label="+")
        plus.set_name("pomo-ts-btn")
        plus.connect("clicked",  self._inc)
        plus.connect("pressed",  self._start_repeat, +1)
        plus.connect("released", self._stop_repeat)

        pill = Gtk.Box(spacing=0)
        pill.set_name("pomo-ts-pill")
        pill.pack_start(minus,         False, False, 0)
        pill.pack_start(self._val_lbl, True,  True,  0)
        pill.pack_start(plus,          False, False, 0)

        unit = Gtk.Label(label="min")
        unit.set_name("pomo-ts-unit")

        self.pack_start(head, False, False, 0)
        self.pack_start(pill, False, False, 0)
        self.pack_start(unit, False, False, 0)
        self.set_name("pomo-ts-box")
        self.show_all()

    # value helpers
    def get_value(self) -> int: return self._value
    def set_value(self, v: int):
        self._value = max(self._lo, min(self._hi, v))
        self._val_lbl.set_text(str(self._value))

    def _step(self, delta: int):
        nv = max(self._lo, min(self._hi, self._value + delta))
        if nv != self._value:
            self._value = nv
            self._val_lbl.set_text(str(nv))
            self._on_change(nv)

    def _dec(self, *_): self._step(-1)
    def _inc(self, *_): self._step(+1)

    def _start_repeat(self, _, delta: int):
        if self._repeat_id is not None:
            return
        def _tick():
            self._step(delta)
            return GLib.SOURCE_CONTINUE
        self._repeat_id = GLib.timeout_add(120, _tick)

    def _stop_repeat(self, *_):
        if self._repeat_id is not None:
            GLib.source_remove(self._repeat_id)
            self._repeat_id = None


# ── button helpers ────────────────────────────────────────────────────────────

def _icon_btn(css_name, markup, tooltip=None):
    lbl = Gtk.Label()
    lbl.set_markup(markup)
    lbl.set_name("pomo-btn-icon")
    btn = Gtk.Button()
    btn.set_name(css_name)
    btn.add(lbl)
    if tooltip:
        btn.set_tooltip_text(tooltip)
    btn.show_all()
    return btn, lbl


# ── main widget ───────────────────────────────────────────────────────────────

class PomodoroTimer(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="pomodoro",
            orientation="h",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
        )

        cfg = _load_cfg()
        self._work_mins  = cfg["work_mins"]
        self._short_mins = cfg["short_mins"]
        self._long_mins  = cfg["long_mins"]

        self._mode       = "work"
        self._running    = False
        self._done       = False
        self._secs_left  = self._work_mins * 60
        self._total_secs = self._work_mins * 60
        self._completed  = 0
        self._timer_id   = None

        self._build_ui()
        self._refresh()
        self.show_all()

    # ── construction ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # left: ring
        self._ring = _Ring()
        ring_box = Gtk.Box()
        ring_box.set_name("pomo-ring-wrap")
        ring_box.set_halign(Gtk.Align.CENTER)
        ring_box.set_valign(Gtk.Align.CENTER)
        ring_box.set_hexpand(False)
        ring_box.set_vexpand(True)
        ring_box.pack_start(self._ring, False, False, 0)

        # right panel
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right.set_name("pomo-right")
        right.set_halign(Gtk.Align.FILL)
        right.set_valign(Gtk.Align.CENTER)
        right.set_hexpand(True)
        right.set_vexpand(True)

        # session dots
        self._dots: list[Gtk.Label] = []
        dots_box = Gtk.Box(spacing=8)
        dots_box.set_name("pomo-dots")
        dots_box.set_halign(Gtk.Align.CENTER)
        for _ in range(SESSIONS_BEFORE_LONG):
            d = Gtk.Label(label="○")
            d.set_name("pomo-dot")
            d.show()
            dots_box.pack_start(d, False, False, 0)
            self._dots.append(d)

        # mode tabs
        self._mode_btns: dict[str, Gtk.Button] = {}
        mode_box = Gtk.Box(spacing=2)
        mode_box.set_name("pomo-mode-box")
        mode_box.set_halign(Gtk.Align.CENTER)
        for key, text in [("work", "Pomodoro"), ("short_break", "Short Break"), ("long_break", "Long Break")]:
            b = Gtk.Button(label=text)
            b.set_name("pomo-mode-btn")
            b.connect("clicked", self._on_mode_btn, key)
            b.show_all()
            mode_box.pack_start(b, False, False, 0)
            self._mode_btns[key] = b

        # control buttons row
        self._reset_btn, _   = _icon_btn("pomo-btn-sm",   icons.reload, "Reset session")
        self._play_btn,  self._play_icon = _icon_btn("pomo-btn-play", icons.play, "Start / Pause")
        self._stop_btn,  _   = _icon_btn("pomo-btn-stop", icons.stop,  "Stop timer")

        self._reset_btn.connect("clicked", self._on_reset)
        self._play_btn.connect( "clicked", self._on_play_pause)
        self._stop_btn.connect( "clicked", self._on_stop)

        ctrl_box = Gtk.Box(spacing=10)
        ctrl_box.set_name("pomo-controls")
        ctrl_box.set_halign(Gtk.Align.CENTER)
        ctrl_box.pack_start(self._reset_btn, False, False, 0)
        ctrl_box.pack_start(self._play_btn,  False, False, 0)
        ctrl_box.pack_start(self._stop_btn,  False, False, 0)

        # stop-all button (below controls)
        self._stop_all_btn = Gtk.Button(label="Stop All")
        self._stop_all_btn.set_name("pomo-btn-stop-all")
        self._stop_all_btn.set_halign(Gtk.Align.CENTER)
        self._stop_all_btn.connect("clicked", self._on_stop_all)
        self._stop_all_btn.show_all()

        # duration selectors
        self._ts_work  = _TimeSelector("Work",  self._work_mins,  1, 180, self._on_dur("work"))
        self._ts_short = _TimeSelector("Short", self._short_mins, 1,  60, self._on_dur("short"))
        self._ts_long  = _TimeSelector("Long",  self._long_mins,  1, 180, self._on_dur("long"))

        dur_box = Gtk.Box(spacing=10)
        dur_box.set_name("pomo-dur-box")
        dur_box.set_halign(Gtk.Align.CENTER)
        dur_box.pack_start(self._ts_work,  False, False, 0)
        dur_box.pack_start(self._ts_short, False, False, 0)
        dur_box.pack_start(self._ts_long,  False, False, 0)

        right.pack_start(dots_box,           False, False, 0)
        right.pack_start(mode_box,           False, False, 0)
        right.pack_start(ctrl_box,           False, False, 0)
        right.pack_start(self._stop_all_btn, False, False, 0)
        right.pack_start(dur_box,            False, False, 0)
        right.show_all()

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        outer.set_name("pomo-outer")
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_hexpand(True)
        outer.set_vexpand(True)
        outer.pack_start(ring_box, False, False, 0)
        outer.pack_start(right,    False, False, 0)
        outer.show_all()

        self.add(outer)

    # ── display ───────────────────────────────────────────────────────────────

    def _refresh(self):
        mins, secs = self._secs_left // 60, self._secs_left % 60
        progress = 0.0 if self._total_secs == 0 else 1.0 - self._secs_left / self._total_secs
        state = "DONE" if self._done else {"work": "FOCUS", "short_break": "SHORT BREAK", "long_break": "LONG BREAK"}[self._mode]
        self._ring.refresh(self._mode, progress, f"{mins:02d}:{secs:02d}", state, self._done)

        self._play_icon.set_markup(icons.pause if self._running else icons.play)

        filled = self._completed % SESSIONS_BEFORE_LONG
        for i, dot in enumerate(self._dots):
            dot.set_text("●" if i < filled else "○")
            dot.set_name("pomo-dot-filled" if i < filled else "pomo-dot")

        for key, btn in self._mode_btns.items():
            ctx = btn.get_style_context()
            if key == self._mode: ctx.add_class("active")
            else:                 ctx.remove_class("active")

        play_ctx = self._play_btn.get_style_context()
        if self._done: play_ctx.add_class("done")
        else:          play_ctx.remove_class("done")

    # ── timer ─────────────────────────────────────────────────────────────────

    def _start(self):
        if self._timer_id is not None:
            return
        self._done = False
        self._running = True
        self._timer_id = GLib.timeout_add(1000, self._tick)
        self._refresh()

    def _pause(self):
        self._running = False
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        self._refresh()

    def _tick(self):
        if not self._running:
            self._timer_id = None
            return GLib.SOURCE_REMOVE
        self._secs_left -= 1
        self._refresh()
        if self._secs_left <= 0:
            self._secs_left = 0
            self._timer_id  = None
            GLib.idle_add(self._on_complete)
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _on_complete(self):
        self._running = self._done = False
        self._timer_id = None
        self._done = True
        if self._mode == "work":
            self._completed += 1
            _play_sound(_SOUND_WORK_DONE)
        else:
            _play_sound(_SOUND_BREAK_DONE)
        self._refresh()
        return GLib.SOURCE_REMOVE

    def _switch_mode(self, mode):
        self._pause()
        self._mode = mode
        self._done = False
        secs = self._dur_secs(mode)
        self._secs_left = self._total_secs = secs
        self._refresh()

    def _dur_secs(self, mode) -> int:
        return {"work": self._work_mins, "short_break": self._short_mins, "long_break": self._long_mins}[mode] * 60

    # ── handlers ─────────────────────────────────────────────────────────────

    def _on_play_pause(self, *_):
        if self._running:           self._pause()
        elif self._secs_left > 0:   self._start()

    def _on_reset(self, *_):
        self._pause()
        self._done      = False
        self._secs_left = self._total_secs
        self._refresh()

    def _on_stop(self, *_):
        """Stop & reset current session timer (keep session count)."""
        self._pause()
        self._done      = False
        self._secs_left = self._total_secs
        self._refresh()

    def _on_stop_all(self, *_):
        """Reset everything — timer, session count, mode."""
        self._pause()
        self._completed  = 0
        self._mode       = "work"
        self._done       = False
        secs = self._work_mins * 60
        self._secs_left  = secs
        self._total_secs = secs
        self._ts_work.set_value(self._work_mins)
        self._refresh()

    def _on_mode_btn(self, _, mode):
        self._switch_mode(mode)

    def _on_dur(self, which: str):
        def handler(val: int):
            if which == "work":
                self._work_mins = val
                if self._mode == "work" and not self._running:
                    self._secs_left = self._total_secs = val * 60
                    self._refresh()
            elif which == "short":
                self._short_mins = val
                if self._mode == "short_break" and not self._running:
                    self._secs_left = self._total_secs = val * 60
                    self._refresh()
            elif which == "long":
                self._long_mins = val
                if self._mode == "long_break" and not self._running:
                    self._secs_left = self._total_secs = val * 60
                    self._refresh()
            _save_cfg({"work_mins": self._work_mins,
                       "short_mins": self._short_mins,
                       "long_mins": self._long_mins})
        return handler


def _play_sound(path):
    try:
        subprocess.Popen(["paplay", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
