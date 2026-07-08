"""Physical-unit conversions. All layout math happens in millimetres;
pixels only exist at the render boundary for a specific target DPI."""

from __future__ import annotations

MM_PER_INCH = 25.4


def mm_to_inch(mm: float) -> float:
    return mm / MM_PER_INCH


def inch_to_mm(inch: float) -> float:
    return inch * MM_PER_INCH


def mm_to_px(mm: float, dpi: float) -> float:
    return mm_to_inch(mm) * dpi


def px_to_mm(px: float, dpi: float) -> float:
    return (px / dpi) * MM_PER_INCH


def mm_to_pt(mm: float) -> float:
    """PDF/Cairo points: 1 pt = 1/72 inch."""
    return mm_to_inch(mm) * 72.0


def pt_to_mm(pt: float) -> float:
    return (pt / 72.0) * MM_PER_INCH
