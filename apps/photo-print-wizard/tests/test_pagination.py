import pytest

from photo_print_wizard.layout.geometry import CropMode, Margins
from photo_print_wizard.layout.pagination import paginate
from photo_print_wizard.layout.presets import SIZE_10X15, custom_layout


def test_seventeen_images_paginate_with_no_manual_work():
    # SIZE_10X15 achieves 2 slots/page (see test_presets for why "4 per
    # page" is physically impossible on A4 at true 10x15cm size).
    paths = [f"img{i}.jpg" for i in range(1, 18)]
    pages = paginate(paths, SIZE_10X15)
    assert len(pages) == 9  # ceil(17 / 2 per page)
    flat = [img.source_path for page in pages for _slot, img in page.placements if img]
    assert flat == paths
    last_filled = [img for _slot, img in pages[-1].placements if img]
    assert len(last_filled) == 1
    assert last_filled[0].source_path == "img17.jpg"


def test_pagination_preserves_order():
    paths = [f"img{i}.jpg" for i in range(8)]
    pages = paginate(paths, SIZE_10X15)
    flat = [img.source_path for page in pages for _slot, img in page.placements if img]
    assert flat == paths


def test_empty_list_yields_no_pages():
    assert paginate([], SIZE_10X15) == []


def test_crop_mode_propagated():
    pages = paginate(["a.jpg"], SIZE_10X15, crop_mode=CropMode.FILL)
    _slot, img = pages[0].placements[0]
    assert img.crop_mode == CropMode.FILL


def test_copies_per_image_repeats():
    pages = paginate(["a.jpg", "b.jpg"], SIZE_10X15, copies_per_image=4)
    flat = [img.source_path for page in pages for _slot, img in page.placements if img]
    assert flat == ["a.jpg"] * 4 + ["b.jpg"] * 4


def test_layout_that_does_not_fit_raises():
    oversized = custom_layout(1, 1, 500.0, 500.0, Margins(), 0.0)
    with pytest.raises(ValueError):
        paginate(["a.jpg"], oversized)


def test_custom_layout_forced_grid():
    layout = custom_layout(2, 3, 50.0, 50.0, Margins(top=5, bottom=5, left=5, right=5), 2.0)
    slots = layout.slots_per_page()
    assert len(slots) == 6
