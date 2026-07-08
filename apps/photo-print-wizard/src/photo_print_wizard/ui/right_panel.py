"""Right panel: printer, layout preset, crop mode, margins, border,
background — all Adwaita PreferencesGroup rows."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from ..layout import BUILTIN_PRESETS, PASSPORT_PRESETS, CropMode
from ..printing import CupsError, list_printers


class RightPanel(Gtk.Box):
    def __init__(self, on_change: Callable[[], None]):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        self._on_change = on_change

        scroller = Gtk.ScrolledWindow(vexpand=True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        scroller.set_child(content)
        self.append(scroller)

        content.append(self._build_printer_group())
        content.append(self._build_layout_group())
        content.append(self._build_crop_group())
        content.append(self._build_margins_group())
        content.append(self._build_border_group())
        content.append(self._build_background_group())

        self._load_printers_async()

    # -- printer -------------------------------------------------------
    def _build_printer_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Printer")
        self._printer_model = Gtk.StringList()
        self._printer_row = Adw.ComboRow(title="Printer", model=self._printer_model)
        self._printer_row.connect("notify::selected", lambda *_: self._on_change())
        group.add(self._printer_row)

        self._paper_model = Gtk.StringList.new(["A4", "Letter"])
        self.paper_row = Adw.ComboRow(title="Paper Size", model=self._paper_model)
        self.paper_row.connect("notify::selected", lambda *_: self._on_change())
        group.add(self.paper_row)

        self.color_row = Adw.SwitchRow(title="Color", active=True)
        self.color_row.connect("notify::active", lambda *_: self._on_change())
        group.add(self.color_row)

        return group

    def _load_printers_async(self) -> None:
        def worker():
            try:
                printers = list_printers()
                names = [p.name for p in printers]
            except CupsError:
                names = []
            GLib.idle_add(self._populate_printers, names)

        GLib.Thread.new(None, worker)

    def _populate_printers(self, names: list[str]) -> None:
        fallback = names or ["No printers found"]
        self._printer_model.splice(0, self._printer_model.get_n_items(), fallback)

    def get_selected_printer(self) -> str | None:
        idx = self._printer_row.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or self._printer_model.get_n_items() == 0:
            return None
        return self._printer_model.get_string(idx)

    # -- layout ----------------------------------------------------------
    def _build_layout_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Layout Preset")
        labels = [p.label for p in BUILTIN_PRESETS.values()]
        labels += [f"Passport – {p.country}" for p in PASSPORT_PRESETS.values()]
        labels += ["Contact Sheet", "Custom Layout"]
        self._layout_ids = (
            list(BUILTIN_PRESETS.keys())
            + [f"passport_{p.id}" for p in PASSPORT_PRESETS.values()]
            + ["contact_sheet", "custom"]
        )

        self._layout_model = Gtk.StringList.new(labels)
        self.layout_row = Adw.ComboRow(title="Preset", model=self._layout_model, selected=2)
        self.layout_row.connect("notify::selected", lambda *_: self._on_change())
        group.add(self.layout_row)
        return group

    def get_selected_layout_id(self) -> str:
        return self._layout_ids[self.layout_row.get_selected()]

    # -- crop --------------------------------------------------------
    def _build_crop_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Cropping")
        self._crop_model = Gtk.StringList.new(["Fit", "Fill", "Smart Crop", "Stretch"])
        self.crop_row = Adw.ComboRow(title="Mode", model=self._crop_model, selected=0)
        self.crop_row.connect("notify::selected", lambda *_: self._on_change())
        group.add(self.crop_row)
        return group

    def get_selected_crop_mode(self) -> CropMode:
        return [CropMode.FIT, CropMode.FILL, CropMode.SMART, CropMode.STRETCH][
            self.crop_row.get_selected()
        ]

    # -- margins -------------------------------------------------------
    def _build_margins_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Margins (mm)")
        self.margin_rows: dict[str, Adw.SpinRow] = {}
        for label, key, default in (
            ("Top", "top", 5.0),
            ("Bottom", "bottom", 5.0),
            ("Left", "left", 5.0),
            ("Right", "right", 5.0),
        ):
            adj = Gtk.Adjustment(lower=0, upper=50, step_increment=1, value=default)
            row = Adw.SpinRow(title=label, adjustment=adj, digits=1)
            row.connect("notify::value", lambda *_: self._on_change())
            self.margin_rows[key] = row
            group.add(row)
        return group

    def get_margins_mm(self) -> dict[str, float]:
        return {k: r.get_value() for k, r in self.margin_rows.items()}

    def set_margins_mm(self, margins) -> None:
        """Sync the spin rows to `margins` (a Margins instance) without
        firing `on_change` recursively."""
        for key, row in self.margin_rows.items():
            row.set_value(getattr(margins, key))

    # -- border --------------------------------------------------------
    def _build_border_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Border")
        adj = Gtk.Adjustment(lower=0, upper=10, step_increment=0.5, value=0)
        self.border_width_row = Adw.SpinRow(title="Width (mm)", adjustment=adj, digits=1)
        self.border_width_row.connect("notify::value", lambda *_: self._on_change())
        group.add(self.border_width_row)

        radius_adj = Gtk.Adjustment(lower=0, upper=20, step_increment=0.5, value=0)
        self.border_radius_row = Adw.SpinRow(
            title="Rounded Corners (mm)", adjustment=radius_adj, digits=1
        )
        self.border_radius_row.connect("notify::value", lambda *_: self._on_change())
        group.add(self.border_radius_row)
        return group

    # -- background ------------------------------------------------------
    def _build_background_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Background")
        self._bg_model = Gtk.StringList.new(["White", "Black", "Custom"])
        self.background_row = Adw.ComboRow(title="Color", model=self._bg_model, selected=0)
        self.background_row.connect("notify::selected", lambda *_: self._on_change())
        group.add(self.background_row)
        return group

    def get_background_rgb(self) -> tuple[float, float, float]:
        idx = self.background_row.get_selected()
        return [(1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)][idx]
