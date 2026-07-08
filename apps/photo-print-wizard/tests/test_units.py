from photo_print_wizard.layout.units import inch_to_mm, mm_to_inch, mm_to_pt, mm_to_px, pt_to_mm


def test_mm_inch_roundtrip():
    assert abs(inch_to_mm(mm_to_inch(100.0)) - 100.0) < 1e-9


def test_mm_to_px_at_300dpi():
    assert abs(mm_to_px(25.4, 300) - 300.0) < 1e-6


def test_mm_pt_roundtrip():
    assert abs(pt_to_mm(mm_to_pt(50.0)) - 50.0) < 1e-9


def test_5x7_inch_matches_127x178mm():
    assert abs(inch_to_mm(5.0) - 127.0) < 0.1
    assert abs(inch_to_mm(7.0) - 178.0) < 0.3
