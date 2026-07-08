"""Disk-backed thumbnail cache so a 1000-image selection stays responsive.

Thumbnails are stored as JPEG in ~/.cache/photo-print-wizard/thumbnails/,
keyed by source path + mtime + size, so stale entries are never served.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from PIL import Image

from .loader import load_image

THUMB_SIZE = (200, 200)

_CACHE_DIR = (
    Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    / "photo-print-wizard"
    / "thumbnails"
)


def _cache_key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_thumbnail_path(source_path: str | Path) -> Path:
    """Return a path to a cached thumbnail JPEG for `source_path`, generating
    it on first request."""
    source_path = Path(source_path)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(source_path)
    thumb_path = _CACHE_DIR / f"{key}.jpg"

    if not thumb_path.exists():
        img = load_image(source_path).convert("RGB")
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        img.save(thumb_path, "JPEG", quality=85)

    return thumb_path


def clear_cache() -> None:
    if not _CACHE_DIR.exists():
        return
    for f in _CACHE_DIR.glob("*.jpg"):
        f.unlink(missing_ok=True)
