from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from .ui.main_window import MainWindow

APP_ID = "dev.sohamdarekar.PhotoPrintWizard"


class PhotoPrintWizardApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self) -> None:
        win = self.props.active_window
        if not win:
            win = MainWindow(self)
        win.present()

    def do_open(self, files: list, _n_files: int, _hint: str) -> None:
        """Invoked when launched via 'Open With' or `photo-print-wizard file.jpg ...`."""
        win = self.props.active_window
        if not win:
            win = MainWindow(self)
        paths = [f.get_path() for f in files if f.get_path()]
        win.add_images(paths)
        win.present()
