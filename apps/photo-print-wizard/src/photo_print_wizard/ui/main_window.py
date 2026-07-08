from __future__ import annotations

import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from ..layout import (
    BUILTIN_PRESETS,
    PASSPORT_PRESETS,
    Border,
    Margins,
    custom_layout,
    passport_layout,
)
from ..layout.geometry import Page
from ..printing import CupsError, print_pdf
from ..render import export_pdf
from ..settings import load_settings, save_settings
from .preview_widget import PreviewWidget
from .right_panel import RightPanel
from .state import PAPER_CHOICES, AppState
from .thumbnail_grid import ThumbnailGrid


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="Photo Print Wizard")

        self._settings = load_settings()
        self.state = AppState()
        self.set_default_size(self._settings.window_width, self._settings.window_height)

        toolbar_view = Adw.ToolbarView()
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(toolbar_view)
        self.set_content(self._toast_overlay)

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        export_btn = Gtk.Button(label="Export PDF")
        export_btn.connect("clicked", self._on_export_pdf)
        header.pack_start(export_btn)

        print_btn = Gtk.Button(label="Print", css_classes=["suggested-action"])
        print_btn.connect("clicked", self._on_print)
        header.pack_end(print_btn)

        # Fixed-width side columns (thumbnail grid + right panel) that keep
        # their size on resize; only the center preview stretches. Avoids
        # deriving positions from stale saved window_width, which could
        # push the right panel's divider past the actual (e.g. tiling-WM
        # imposed) window width and leave it invisible until dragged.
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_resize_start_child(False)
        paned.set_shrink_start_child(False)
        toolbar_view.set_content(paned)

        self.thumbnail_grid = ThumbnailGrid(on_changed=self._on_images_changed)
        self.thumbnail_grid.set_size_request(340, -1)
        paned.set_start_child(self.thumbnail_grid)

        right_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        right_paned.set_resize_end_child(False)
        right_paned.set_shrink_end_child(False)
        paned.set_end_child(right_paned)

        self.preview = PreviewWidget(get_page=self._get_current_page)
        self.preview.set_page_change_callback(self._on_page_nav)
        self.preview.set_hexpand(True)
        right_paned.set_start_child(self.preview)

        self.right_panel = RightPanel(on_change=self._on_controls_changed)
        self.right_panel.set_size_request(340, -1)
        right_paned.set_end_child(self.right_panel)

        paned.set_position(340)

        def _place_right_divider(*_args) -> None:
            width = self.get_width() or self._settings.window_width
            right_paned.set_position(max(width - 340 - 340, 200))

        self.connect("map", lambda *_: GLib.idle_add(_place_right_divider))

        self.connect("close-request", self._on_close)

    def add_images(self, paths: list[str]) -> None:
        """Called from 'Open With' / CLI file args."""
        self.thumbnail_grid.add_paths(paths)

    # -- state sync --------------------------------------------------
    def _on_images_changed(self, paths: list[str]) -> None:
        self.state.image_paths = paths
        self.state.rotations = self.thumbnail_grid.get_rotations()
        self._recompute()

    def _on_controls_changed(self) -> None:
        layout = self._resolve_layout()
        if layout.id != self.state.layout.id:
            # Preset just changed: adopt its own tuned margins instead of
            # whatever was left over from the previous preset, so e.g.
            # 8x10in (3mm margins) doesn't inherit 5mm defaults that no
            # longer fit its larger cell.
            self.right_panel.set_margins_mm(layout.margins)
        self.state.layout = layout
        margins = self.right_panel.get_margins_mm()
        self.state.margins = Margins(**margins)
        self.state.paper = list(PAPER_CHOICES.values())[self.right_panel.paper_row.get_selected()]
        self.state.crop_mode = self.right_panel.get_selected_crop_mode()
        self.state.background_rgb = self.right_panel.get_background_rgb()
        self.state.border = Border(
            width_mm=self.right_panel.border_width_row.get_value(),
            rounded_radius_mm=self.right_panel.border_radius_row.get_value(),
        )
        self._recompute()

    def _resolve_layout(self):
        layout_id = self.right_panel.get_selected_layout_id()
        if layout_id in BUILTIN_PRESETS:
            return BUILTIN_PRESETS[layout_id]
        if layout_id.startswith("passport_"):
            key = layout_id.removeprefix("passport_")
            return passport_layout(PASSPORT_PRESETS[key])
        if layout_id == "custom":
            return custom_layout(2, 2, 80.0, 80.0, self.state.margins, 4.0, self.state.paper)
        return BUILTIN_PRESETS["10x15"]

    def _recompute(self) -> None:
        self.state.recompute_pages()
        total = len(self.state.pages)
        self.preview.set_page_info(self.state.current_page_index, total)
        self.preview.queue_redraw()

    def _get_current_page(self) -> Page | None:
        if not self.state.pages:
            return None
        return self.state.pages[self.state.current_page_index]

    def _on_page_nav(self, delta: int) -> None:
        if not self.state.pages:
            return
        n = len(self.state.pages)
        self.state.current_page_index = (self.state.current_page_index + delta) % n
        self.preview.set_page_info(self.state.current_page_index, n)

    # -- actions ---------------------------------------------------------
    def _on_export_pdf(self, _btn) -> None:
        if not self.state.pages:
            self._toast("No images to export.")
            return
        dialog = Gtk.FileDialog(title="Export PDF", initial_name="print-job.pdf")
        dialog.save(self, None, self._on_export_path_chosen)

    def _on_export_path_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        path = gfile.get_path()
        pages, background_rgb, border = (
            self.state.pages,
            self.state.background_rgb,
            self.state.border,
        )

        def worker():
            try:
                export_pdf(pages, path, background_rgb=background_rgb, border=border)
                GLib.idle_add(self._toast, f"Exported to {path}")
            except Exception as exc:
                GLib.idle_add(self._toast, f"Export failed: {exc}")

        GLib.Thread.new(None, worker)

    def _on_print(self, _btn) -> None:
        if not self.state.pages:
            self._toast("No images to print.")
            return

        pages, background_rgb, border = (
            self.state.pages,
            self.state.background_rgb,
            self.state.border,
        )

        # Gtk.PrintUnixDialog talks directly to GTK's own CUPS print
        # backend (enumerate printers + submit job — same "read + submit"
        # contract as pycups, no printer reconfiguration). Deliberately NOT
        # using Gtk.PrintOperation's PRINT_DIALOG action: on this system it
        # routes through xdg-desktop-portal-gtk, whose print dialog renders
        # as a blank window under Hyprland (reproduced: dialog surface maps
        # but never paints). PrintUnixDialog bypasses the portal entirely.
        dialog = Gtk.PrintUnixDialog(title="Print", transient_for=self, modal=True)
        first = pages[0]
        paper = Gtk.PaperSize.new_custom(
            "photo-print-wizard",
            first.paper.name,
            first.paper.width_mm,
            first.paper.height_mm,
            Gtk.Unit.MM,
        )
        page_setup = Gtk.PageSetup()
        page_setup.set_paper_size(paper)
        page_setup.set_top_margin(0, Gtk.Unit.MM)
        page_setup.set_bottom_margin(0, Gtk.Unit.MM)
        page_setup.set_left_margin(0, Gtk.Unit.MM)
        page_setup.set_right_margin(0, Gtk.Unit.MM)
        dialog.set_page_setup(page_setup)
        dialog.props.print_settings = Gtk.PrintSettings()
        dialog.set_manual_capabilities(
            Gtk.PrintCapabilities.COPIES
            | Gtk.PrintCapabilities.COLLATE
            | Gtk.PrintCapabilities.REVERSE
            | Gtk.PrintCapabilities.NUMBER_UP
        )

        def on_response(dlg: Gtk.PrintUnixDialog, response_id: int) -> None:
            if response_id != Gtk.ResponseType.OK:
                dlg.destroy()
                return
            printer = dlg.get_selected_printer()
            settings = dlg.props.print_settings
            dlg.destroy()
            if printer is None:
                self._toast("No printer selected.")
                return
            printer_name = printer.get_name()
            copies = settings.get_n_copies() if settings else 1
            tmp_pdf = Path(tempfile.gettempdir()) / "photo-print-wizard-job.pdf"

            def worker():
                try:
                    export_pdf(pages, str(tmp_pdf), background_rgb=background_rgb, border=border)
                    job_id = print_pdf(
                        printer_name,
                        str(tmp_pdf),
                        job_title="Photo Print Wizard",
                        options={"copies": str(copies)},
                    )
                    GLib.idle_add(self._toast, f"Sent to {printer_name} (job #{job_id})")
                except CupsError as exc:
                    GLib.idle_add(self._toast, f"Print failed: {exc}")
                except Exception as exc:
                    GLib.idle_add(self._toast, f"Print failed: {exc}")

            GLib.Thread.new(None, worker)

        dialog.connect("response", on_response)
        dialog.present()

    def _toast(self, message: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def _on_close(self, _window) -> bool:
        self._settings.window_width = self.get_width()
        self._settings.window_height = self.get_height()
        printer = self.right_panel.get_selected_printer()
        if printer:
            self._settings.last_printer = printer
        save_settings(self._settings)
        return False
