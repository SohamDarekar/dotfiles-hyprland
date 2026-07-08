"""Image loading with EXIF auto-orientation and broad format support."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ExifTags, Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:  # pragma: no cover - optional dependency
    HEIF_SUPPORTED = False

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
}
if HEIF_SUPPORTED:
    SUPPORTED_EXTENSIONS |= {".heif", ".heic"}


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def load_image(path: str | Path) -> Image.Image:
    """Open an image, apply EXIF orientation, return RGB (or RGBA if the
    source has alpha). GIFs are reduced to their first frame."""
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        img.seek(0)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    return img


def read_exif_orientation(path: str | Path) -> int:
    """Returns the raw EXIF orientation tag (1-8), or 1 if absent."""
    try:
        img = Image.open(path)
        exif = img.getexif()
        orientation_tag = next((k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None)
        if orientation_tag is not None:
            return int(exif.get(orientation_tag, 1))
    except Exception:
        pass
    return 1


@lru_cache(maxsize=512)
def get_image_size(path: str) -> tuple[int, int]:
    """Cheap, cached (width, height) lookup that respects EXIF orientation
    without decoding full pixel data."""
    with Image.open(path) as img:
        orientation = read_exif_orientation(path)
        w, h = img.size
        if orientation in (5, 6, 7, 8):
            w, h = h, w
        return w, h
