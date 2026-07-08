"""Turns a flat list of source images + a LayoutPreset into a list of Pages.

No manual arrangement required: images fill slots in order, left-to-right,
top-to-bottom, overflowing onto new pages as needed. The last page may be
partially filled (remaining slots are left empty).
"""

from __future__ import annotations

from .geometry import CropMode, LayoutPreset, Page, PageImage


def paginate(
    image_paths: list[str],
    layout: LayoutPreset,
    crop_mode: CropMode = CropMode.FIT,
    copies_per_image: int = 1,
    rotations: dict[str, int] | None = None,
) -> list[Page]:
    """Build pages for `image_paths` under `layout`.

    copies_per_image > 1 repeats each image that many times consecutively
    before moving to the next (used by passport-photo "4/6/8 copies" mode).
    `rotations` maps source path -> extra rotation in degrees (0/90/180/270)
    applied on top of EXIF auto-orientation, e.g. from user rotate buttons.
    """
    if not image_paths:
        return []

    paper, slots = layout.resolve()
    if not slots:
        raise ValueError(
            f"Layout '{layout.label}' cell size does not fit on "
            f"{layout.paper.name} with current margins."
        )

    rotations = rotations or {}
    expanded: list[str] = []
    for p in image_paths:
        expanded.extend([p] * copies_per_image)

    pages: list[Page] = []
    for page_start in range(0, len(expanded), len(slots)):
        chunk = expanded[page_start : page_start + len(slots)]
        placements = []
        for slot, path in zip(slots, chunk, strict=False):
            placements.append(
                (
                    slot,
                    PageImage(
                        source_path=path,
                        crop_mode=crop_mode,
                        rotation_deg=rotations.get(path, 0),
                    ),
                )
            )
        for slot in slots[len(chunk) :]:
            placements.append((slot, None))
        pages.append(Page(index=len(pages), paper=paper, placements=placements))

    return pages
