"""Core geometry types. Everything is in millimetres unless named *_px."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CropMode(StrEnum):
    FIT = "fit"
    FILL = "fill"
    SMART = "smart"
    STRETCH = "stretch"


class Alignment(StrEnum):
    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class PaperSize:
    name: str
    width_mm: float
    height_mm: float

    def rotated(self) -> PaperSize:
        return PaperSize(self.name + " (landscape)", self.height_mm, self.width_mm)


A4 = PaperSize("A4", 210.0, 297.0)
LETTER = PaperSize("Letter", 215.9, 279.4)

PAPER_SIZES: dict[str, PaperSize] = {p.name: p for p in (A4, LETTER)}


@dataclass(frozen=True)
class Margins:
    top: float = 5.0
    bottom: float = 5.0
    left: float = 5.0
    right: float = 5.0


@dataclass(frozen=True)
class Border:
    width_mm: float = 0.0
    color_rgb: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rounded_radius_mm: float = 0.0


@dataclass(frozen=True)
class Slot:
    """A single image placement on a page, in mm, relative to page origin
    (top-left)."""

    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class LayoutPreset:
    id: str
    label: str
    cell_width_mm: float
    cell_height_mm: float
    paper: PaperSize = A4
    margins: Margins = field(default_factory=Margins)
    spacing_mm: float = 4.0
    forced_cols: int | None = None
    forced_rows: int | None = None
    auto_orient: bool = False

    def slots_per_page(self) -> list[Slot]:
        """Compute a centered grid of cells fitting the paper, margins, and
        spacing. Returns slots in reading order (left-to-right, top-to-bottom).
        If forced_cols/forced_rows are set (Custom Layout), use them verbatim
        instead of auto-fitting. Cells that don't fit the page at all yield []."""
        return self._slots_for_paper(self.paper)

    def resolve(self) -> tuple[PaperSize, list[Slot]]:
        """Like slots_per_page(), but if auto_orient is set, also tries the
        page rotated 90° and returns whichever orientation yields more slots
        (portrait wins ties). Returns (paper_actually_used, slots)."""
        slots = self._slots_for_paper(self.paper)
        if not self.auto_orient:
            return self.paper, slots
        rotated_paper = self.paper.rotated()
        rotated_slots = self._slots_for_paper(rotated_paper)
        if len(rotated_slots) > len(slots):
            return rotated_paper, rotated_slots
        return self.paper, slots

    def _slots_for_paper(self, paper: PaperSize) -> list[Slot]:
        usable_w = paper.width_mm - self.margins.left - self.margins.right
        usable_h = paper.height_mm - self.margins.top - self.margins.bottom

        if self.forced_cols is not None and self.forced_rows is not None:
            cols, rows = max(self.forced_cols, 1), max(self.forced_rows, 1)
            grid_w = cols * self.cell_width_mm + (cols - 1) * self.spacing_mm
            grid_h = rows * self.cell_height_mm + (rows - 1) * self.spacing_mm
            if grid_w > usable_w + 1e-6 or grid_h > usable_h + 1e-6:
                return []
        else:
            cols = _max_fit(usable_w, self.cell_width_mm, self.spacing_mm)
            rows = _max_fit(usable_h, self.cell_height_mm, self.spacing_mm)
            if cols == 0 or rows == 0:
                return []
            grid_w = cols * self.cell_width_mm + (cols - 1) * self.spacing_mm
            grid_h = rows * self.cell_height_mm + (rows - 1) * self.spacing_mm

        origin_x = self.margins.left + (usable_w - grid_w) / 2
        origin_y = self.margins.top + (usable_h - grid_h) / 2

        slots: list[Slot] = []
        for row in range(rows):
            for col in range(cols):
                x = origin_x + col * (self.cell_width_mm + self.spacing_mm)
                y = origin_y + row * (self.cell_height_mm + self.spacing_mm)
                slots.append(Slot(x, y, self.cell_width_mm, self.cell_height_mm))
        return slots


def _max_fit(usable: float, cell: float, spacing: float) -> int:
    """How many cells of size `cell` with `spacing` between them fit in `usable`."""
    if cell <= 0 or usable < cell:
        return 0
    n = 1
    while (n + 1) * cell + n * spacing <= usable + 1e-6:
        n += 1
    return n


@dataclass
class Page:
    index: int
    paper: PaperSize
    placements: list[tuple[Slot, PageImage | None]]


@dataclass
class PageImage:
    """Reference to a source image assigned to a slot on a page."""

    source_path: str
    crop_mode: CropMode = CropMode.FIT
    alignment: Alignment = Alignment.CENTER
    rotation_deg: int = 0
