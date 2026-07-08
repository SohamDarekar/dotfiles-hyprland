"""Center preview: renders the current Page exactly as it will print, with
zoom/pan and page navigation."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..layout.geometry import Page
from ..render.page_renderer import render_page


class PreviewWidget(Gtk.Box):
    def __init__(self, get_page: Callable[[], Page | None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._get_page = get_page
        self._zoom = 1.0
        self._pan = (0.0, 0.0)
        self._drag_start = None

        self._area = Gtk.DrawingArea(vexpand=True, hexpand=True)
        self._area.set_draw_func(self._on_draw)
        self._setup_gestures()

        scroller = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scroller.set_child(self._area)
        self.append(scroller)

        self.append(self._build_toolbar())

    def _build_toolbar(self) -> Gtk.Box:
        bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            halign=Gtk.Align.CENTER,
            margin_bottom=6,
        )

        prev_btn = Gtk.Button(icon_name="go-previous-symbolic")
        prev_btn.connect("clicked", lambda _b: self._change_page(-1))
        bar.append(prev_btn)

        self._page_label = Gtk.Label(label="Page 0 / 0")
        bar.append(self._page_label)

        next_btn = Gtk.Button(icon_name="go-next-symbolic")
        next_btn.connect("clicked", lambda _b: self._change_page(1))
        bar.append(next_btn)

        zoom_out = Gtk.Button(icon_name="zoom-out-symbolic")
        zoom_out.connect("clicked", lambda _b: self._zoom_by(0.8))
        bar.append(zoom_out)

        zoom_reset = Gtk.Button(icon_name="zoom-fit-best-symbolic")
        zoom_reset.connect("clicked", lambda _b: self._zoom_reset())
        bar.append(zoom_reset)

        zoom_in = Gtk.Button(icon_name="zoom-in-symbolic")
        zoom_in.connect("clicked", lambda _b: self._zoom_by(1.25))
        bar.append(zoom_in)

        self._on_page_change: Callable[[int], None] | None = None
        return bar

    def set_page_change_callback(self, cb: Callable[[int], None]) -> None:
        self._on_page_change = cb

    def _change_page(self, delta: int) -> None:
        if self._on_page_change:
            self._on_page_change(delta)
        self.queue_redraw()

    def set_page_info(self, current: int, total: int) -> None:
        self._page_label.set_label(f"Page {current + 1} / {total}" if total else "No pages")

    def _zoom_by(self, factor: float) -> None:
        self._zoom = max(0.1, min(self._zoom * factor, 8.0))
        self._area.queue_draw()

    def _zoom_reset(self) -> None:
        self._zoom = 1.0
        self._pan = (0.0, 0.0)
        self._area.queue_draw()

    def _setup_gestures(self) -> None:
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", lambda g, x, y: setattr(self, "_drag_start", self._pan))
        drag.connect("drag-update", self._on_drag_update)
        self._area.add_controller(drag)

        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self._on_scroll)
        self._area.add_controller(scroll)

    def _on_drag_update(self, _gesture, dx: float, dy: float) -> None:
        if self._drag_start is not None:
            self._pan = (self._drag_start[0] + dx, self._drag_start[1] + dy)
            self._area.queue_draw()

    def _on_scroll(self, _controller, _dx, dy) -> bool:
        self._zoom_by(0.9 if dy > 0 else 1.1)
        return True

    def queue_redraw(self) -> None:
        self._area.queue_draw()

    def _on_draw(self, _area, cr, width, height) -> None:
        page = self._get_page()
        if page is None:
            return

        base_px_per_mm = min(width / page.paper.width_mm, height / page.paper.height_mm) * 0.95
        px_per_mm = base_px_per_mm * self._zoom

        page_w = page.paper.width_mm * px_per_mm
        page_h = page.paper.height_mm * px_per_mm
        origin_x = (width - page_w) / 2 + self._pan[0]
        origin_y = (height - page_h) / 2 + self._pan[1]

        cr.save()
        cr.set_source_rgb(0.85, 0.85, 0.85)
        cr.paint()
        cr.restore()

        cr.save()
        cr.translate(origin_x, origin_y)
        cr.rectangle(-2, -2, page_w + 4, page_h + 4)
        cr.set_source_rgba(0, 0, 0, 0.3)
        cr.fill()
        try:
            render_page(cr, page, px_per_mm, show_guides=True)
        except Exception:
            pass
        cr.restore()
