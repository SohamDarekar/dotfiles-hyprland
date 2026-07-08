"""Central mutable state for the main window. UI widgets read/write this
and call `recompute_pages()`; no business logic lives in the widgets."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..layout import (
    A4,
    BUILTIN_PRESETS,
    LETTER,
    Border,
    CropMode,
    LayoutPreset,
    Margins,
    Page,
    PaperSize,
    paginate,
)


@dataclass
class AppState:
    image_paths: list[str] = field(default_factory=list)
    rotations: dict[str, int] = field(default_factory=dict)
    sort_mode: str = "name"  # name | date | size | random

    layout: LayoutPreset = field(default_factory=lambda: BUILTIN_PRESETS["10x15"])
    paper: PaperSize = A4
    margins: Margins = field(default_factory=Margins)
    crop_mode: CropMode = CropMode.FIT
    border: Border = field(default_factory=Border)
    background_rgb: tuple[float, float, float] = (1.0, 1.0, 1.0)

    printer_name: str | None = None

    pages: list[Page] = field(default_factory=list)
    current_page_index: int = 0

    def recompute_pages(self) -> None:
        layout = self.layout
        if layout.paper != self.paper or layout.margins != self.margins:
            layout = LayoutPreset(
                id=layout.id,
                label=layout.label,
                cell_width_mm=layout.cell_width_mm,
                cell_height_mm=layout.cell_height_mm,
                paper=self.paper,
                margins=self.margins,
                spacing_mm=layout.spacing_mm,
                forced_cols=layout.forced_cols,
                forced_rows=layout.forced_rows,
                auto_orient=layout.auto_orient,
            )
        if not self.image_paths:
            self.pages = []
            self.current_page_index = 0
            return
        try:
            self.pages = paginate(
                self.image_paths, layout, crop_mode=self.crop_mode, rotations=self.rotations
            )
        except ValueError:
            self.pages = []
        self.current_page_index = min(self.current_page_index, max(len(self.pages) - 1, 0))


PAPER_CHOICES: dict[str, PaperSize] = {"A4": A4, "Letter": LETTER}
