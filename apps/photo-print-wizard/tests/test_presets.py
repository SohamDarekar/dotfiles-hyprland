from photo_print_wizard.layout.presets import (
    BUILTIN_PRESETS,
    SIZE_9X13,
    SIZE_10X15,
    SIZE_13X18,
    WALLET,
)


def test_13x18_achieves_two_per_page():
    _paper, slots = SIZE_13X18.resolve()
    assert len(slots) == 2


def test_10x15_achieves_two_per_page():
    # NOTE: two 152mm-tall 4x6 cells need 304mm of page height, but A4 is
    # only 297mm in its longest dimension, so "4 per page" is physically
    # impossible at true size on A4. 2-up (achievable) is the true max.
    _paper, slots = SIZE_10X15.resolve()
    assert len(slots) == 2


def test_9x13_achieves_four_per_page():
    _paper, slots = SIZE_9X13.resolve()
    assert len(slots) == 4


def test_wallet_is_nine_per_page_3x3():
    slots = WALLET.slots_per_page()
    assert len(slots) == 9
    xs = sorted({round(s.x_mm, 3) for s in slots})
    ys = sorted({round(s.y_mm, 3) for s in slots})
    assert len(xs) == 3
    assert len(ys) == 3


def test_exact_physical_dimensions_mm():
    assert SIZE_13X18.cell_width_mm == 127.0
    assert SIZE_13X18.cell_height_mm == 178.0
    assert SIZE_10X15.cell_width_mm == 102.0
    assert SIZE_10X15.cell_height_mm == 152.0
    assert SIZE_9X13.cell_width_mm == 89.0
    assert SIZE_9X13.cell_height_mm == 127.0
    assert WALLET.cell_width_mm == 63.5
    assert WALLET.cell_height_mm == 88.9


def test_slots_fit_within_paper_bounds():
    for preset in BUILTIN_PRESETS.values():
        for slot in preset.slots_per_page():
            assert slot.x_mm >= 0
            assert slot.y_mm >= 0
            assert slot.x_mm + slot.width_mm <= preset.paper.width_mm + 1e-6
            assert slot.y_mm + slot.height_mm <= preset.paper.height_mm + 1e-6
