"""Application settings persisted as JSON under
~/.config/photo-print-wizard/settings.json (XDG_CONFIG_HOME respected).
Never touches any other config path.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

_CONFIG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "photo-print-wizard"
)
_SETTINGS_PATH = _CONFIG_DIR / "settings.json"

_MAX_RECENT_FOLDERS = 10


@dataclass
class Settings:
    last_printer: str | None = None
    last_paper_size: str = "A4"
    last_margins_mm: dict[str, float] = field(
        default_factory=lambda: {"top": 5.0, "bottom": 5.0, "left": 5.0, "right": 5.0}
    )
    last_layout_id: str = "10x15"
    last_crop_mode: str = "fit"
    theme: str = "system"  # system | light | dark
    window_width: int = 1280
    window_height: int = 800
    recent_folders: list[str] = field(default_factory=list)

    def add_recent_folder(self, folder: str) -> None:
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        del self.recent_folders[_MAX_RECENT_FOLDERS:]


def load_settings() -> Settings:
    if not _SETTINGS_PATH.exists():
        return Settings()
    try:
        data = json.loads(_SETTINGS_PATH.read_text())
        return Settings(**{k: v for k, v in data.items() if k in Settings.__dataclass_fields__})
    except (json.JSONDecodeError, TypeError):
        return Settings()


def save_settings(settings: Settings) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(asdict(settings), indent=2))
