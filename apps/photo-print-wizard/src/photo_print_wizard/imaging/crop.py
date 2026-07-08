"""Crop/fit strategies. All functions take a source PIL image and a target
pixel box, returning a new image exactly `target_size` px."""

from __future__ import annotations

from PIL import Image

from ..layout.geometry import Alignment, CropMode

try:
    import cv2
    import numpy as np

    _HAS_OPENCV = True
except ImportError:  # pragma: no cover - optional dependency
    _HAS_OPENCV = False

_FACE_CASCADE = None


def _face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None and _HAS_OPENCV:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _FACE_CASCADE = cv2.CascadeClassifier(path)
    return _FACE_CASCADE


def apply_crop(
    img: Image.Image,
    target_size: tuple[int, int],
    mode: CropMode = CropMode.FIT,
    alignment: Alignment = Alignment.CENTER,
    background: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    if mode == CropMode.STRETCH:
        return img.resize(target_size, Image.LANCZOS)
    if mode == CropMode.FIT:
        return _fit(img, target_size, background)
    if mode == CropMode.FILL:
        return _fill(img, target_size, alignment, focus=None)
    if mode == CropMode.SMART:
        focus = _detect_face_center(img)
        return _fill(img, target_size, alignment, focus=focus)
    raise ValueError(f"Unknown crop mode: {mode}")


def _fit(
    img: Image.Image, target_size: tuple[int, int], background: tuple[int, int, int]
) -> Image.Image:
    tw, th = target_size
    canvas = Image.new("RGB", (tw, th), background)
    scale = min(tw / img.width, th / img.height)
    new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    resized = img.convert("RGB").resize(new_size, Image.LANCZOS)
    offset = ((tw - new_size[0]) // 2, (th - new_size[1]) // 2)
    canvas.paste(resized, offset)
    return canvas


def _fill(
    img: Image.Image,
    target_size: tuple[int, int],
    alignment: Alignment,
    focus: tuple[float, float] | None,
) -> Image.Image:
    tw, th = target_size
    scale = max(tw / img.width, th / img.height)
    new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    resized = img.convert("RGB").resize(new_size, Image.LANCZOS)

    if focus is not None:
        fx, fy = focus[0] * scale, focus[1] * scale
        left = min(max(fx - tw / 2, 0), new_size[0] - tw)
        top = min(max(fy - th / 2, 0), new_size[1] - th)
    else:
        left, top = _aligned_offset(new_size, target_size, alignment)

    left, top = round(left), round(top)
    return resized.crop((left, top, left + tw, top + th))


def _aligned_offset(
    src_size: tuple[int, int], target_size: tuple[int, int], alignment: Alignment
) -> tuple[float, float]:
    sw, sh = src_size
    tw, th = target_size
    cx, cy = (sw - tw) / 2, (sh - th) / 2
    if alignment == Alignment.TOP:
        cy = 0
    elif alignment == Alignment.BOTTOM:
        cy = sh - th
    elif alignment == Alignment.LEFT:
        cx = 0
    elif alignment == Alignment.RIGHT:
        cx = sw - tw
    return cx, cy


def _detect_face_center(img: Image.Image) -> tuple[float, float] | None:
    """Returns the centroid of detected faces in source-image pixel
    coordinates, or None if OpenCV is unavailable or no face is found
    (caller falls back to center crop)."""
    if not _HAS_OPENCV:
        return None
    cascade = _face_cascade()
    if cascade is None or cascade.empty():
        return None

    gray = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        return None

    xs, ys = [], []
    for x, y, w, h in faces:
        xs.append(x + w / 2)
        ys.append(y + h / 2)
    return sum(xs) / len(xs), sum(ys) / len(ys)
