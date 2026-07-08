"""Built-in layout presets with exact physical dimensions (mm)."""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import A4, LayoutPreset, Margins, PaperSize

FULL_PAGE = LayoutPreset(
    id="full_page",
    label="Full Page",
    cell_width_mm=A4.width_mm - 10.0,
    cell_height_mm=A4.height_mm - 10.0,
    spacing_mm=0.0,
)

# NOTE on achievable counts: these presets use *exact* physical print sizes
# (spec requirement). A4 is 210x297mm. Some marketing copy for consumer photo
# apps claims counts (e.g. "4x6 (4 per page)", "9x13 (6 per page)") that are
# geometrically impossible on A4 at true size — e.g. two 152mm-tall 4x6 cells
# need 304mm of page height, but A4 is only 297mm tall in any orientation.
# Rather than shrink the "exact" print size to fake the marketed count, each
# preset here auto-orients (portrait/landscape, whichever yields more slots)
# and reports the true maximum: 13x18 -> 2, 10x15 -> 2, 9x13 -> 4, wallet -> 9.
SIZE_13X18 = LayoutPreset(
    id="13x18",
    label="13 × 18 cm (5×7 in)",
    cell_width_mm=127.0,
    cell_height_mm=178.0,
    margins=Margins(3.0, 3.0, 3.0, 3.0),
    spacing_mm=2.0,
    auto_orient=True,
)

SIZE_10X15 = LayoutPreset(
    id="10x15",
    label="10 × 15 cm (4×6 in)",
    cell_width_mm=102.0,
    cell_height_mm=152.0,
    margins=Margins(2.0, 2.0, 2.0, 2.0),
    spacing_mm=2.0,
    auto_orient=True,
)

SIZE_9X13 = LayoutPreset(
    id="9x13",
    label="9 × 13 cm (3.5×5 in)",
    cell_width_mm=89.0,
    cell_height_mm=127.0,
    margins=Margins(3.0, 3.0, 3.0, 3.0),
    spacing_mm=2.0,
    auto_orient=True,
)

SIZE_8X10IN = LayoutPreset(
    id="8x10in",
    label="8 × 10 in",
    cell_width_mm=203.0,
    cell_height_mm=254.0,
    margins=Margins(3.0, 3.0, 3.0, 3.0),
    spacing_mm=0.0,
)

WALLET = LayoutPreset(
    id="wallet",
    label="Wallet (2.5×3.5 in)",
    cell_width_mm=63.5,
    cell_height_mm=88.9,
    margins=Margins(3.0, 3.0, 3.0, 3.0),
    spacing_mm=2.0,
)

BUILTIN_PRESETS: dict[str, LayoutPreset] = {
    p.id: p for p in (FULL_PAGE, SIZE_13X18, SIZE_10X15, SIZE_9X13, SIZE_8X10IN, WALLET)
}


@dataclass(frozen=True)
class PassportPreset:
    id: str
    country: str
    width_mm: float
    height_mm: float


PASSPORT_PRESETS: dict[str, PassportPreset] = {
    p.id: p
    for p in (
        PassportPreset("in", "India", 35.0, 45.0),
        PassportPreset("au", "Australia", 35.0, 45.0),
        PassportPreset("us", "USA", 50.8, 50.8),
        PassportPreset("uk", "UK", 35.0, 45.0),
        PassportPreset("ca", "Canada", 50.0, 70.0),
    )
}


def passport_layout(preset: PassportPreset, copies: int | None = None) -> LayoutPreset:
    """Build a LayoutPreset for a passport photo size. If `copies` is None,
    auto-fills the page with as many copies as fit."""
    layout = LayoutPreset(
        id=f"passport_{preset.id}",
        label=f"Passport – {preset.country} ({preset.width_mm:g}×{preset.height_mm:g} mm)",
        cell_width_mm=preset.width_mm,
        cell_height_mm=preset.height_mm,
        spacing_mm=2.0,
    )
    if copies is None:
        return layout
    max_slots = len(layout.slots_per_page())
    n = min(copies, max_slots)
    # Cap the grid to exactly `n` slots by forcing a 1-row grid of `n`
    # columns; pagination() will still only place images into as many
    # slots as fit, so this simply bounds the auto-fill count.
    return LayoutPreset(
        id=layout.id,
        label=layout.label,
        cell_width_mm=layout.cell_width_mm,
        cell_height_mm=layout.cell_height_mm,
        paper=layout.paper,
        margins=layout.margins,
        spacing_mm=layout.spacing_mm,
        forced_cols=n,
        forced_rows=1,
    )


def custom_layout(
    rows: int,
    cols: int,
    cell_width_mm: float,
    cell_height_mm: float,
    margins: Margins,
    spacing_mm: float,
    paper: PaperSize = A4,
) -> LayoutPreset:
    return LayoutPreset(
        id="custom",
        label=f"Custom {rows}×{cols}",
        cell_width_mm=cell_width_mm,
        cell_height_mm=cell_height_mm,
        paper=paper,
        margins=margins,
        spacing_mm=spacing_mm,
        forced_cols=cols,
        forced_rows=rows,
    )
