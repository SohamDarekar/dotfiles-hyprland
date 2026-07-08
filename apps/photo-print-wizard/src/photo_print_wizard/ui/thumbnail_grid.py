"""Left panel: thumbnail grid with drag & drop, add/remove/sort controls."""

from __future__ import annotations

import os
import random
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk
from PIL import Image

from ..imaging import SUPPORTED_EXTENSIONS, get_thumbnail_path, is_supported


class ThumbnailItem(GObject.Object):
    path = GObject.Property(type=str)
    rotation = GObject.Property(type=int, default=0)

    def __init__(self, path: str):
        super().__init__()
        self.path = path


class ThumbnailGrid(Gtk.Box):
    """Emits `changed` (via callback) whenever the image list mutates."""

    def __init__(self, on_changed: Callable[[list[str]], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._on_changed = on_changed
        self._store = Gio.ListStore(item_type=ThumbnailItem)

        self._build_toolbar()
        self._build_grid()
        self._setup_dnd()

    # -- toolbar -----------------------------------------------------
    def _build_toolbar(self) -> None:
        bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            margin_top=6,
            margin_start=6,
            margin_end=6,
        )

        add_images_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Images")
        add_images_btn.connect("clicked", self._on_add_images)
        bar.append(add_images_btn)

        add_folder_btn = Gtk.Button(icon_name="folder-new-symbolic", tooltip_text="Add Folder")
        add_folder_btn.connect("clicked", self._on_add_folder)
        bar.append(add_folder_btn)

        remove_btn = Gtk.Button(icon_name="list-remove-symbolic", tooltip_text="Remove Selected")
        remove_btn.connect("clicked", self._on_remove_selected)
        bar.append(remove_btn)

        rotate_left_btn = Gtk.Button(
            icon_name="object-rotate-left-symbolic", tooltip_text="Rotate Selected Left"
        )
        rotate_left_btn.connect("clicked", lambda _b: self._on_rotate_selected(-90))
        bar.append(rotate_left_btn)

        rotate_right_btn = Gtk.Button(
            icon_name="object-rotate-right-symbolic", tooltip_text="Rotate Selected Right"
        )
        rotate_right_btn.connect("clicked", lambda _b: self._on_rotate_selected(90))
        bar.append(rotate_right_btn)

        clear_btn = Gtk.Button(icon_name="edit-clear-all-symbolic", tooltip_text="Clear All")
        clear_btn.connect("clicked", self._on_clear_all)
        bar.append(clear_btn)

        sort_model = Gtk.StringList.new(["Name", "Date", "Size", "Random"])
        self._sort_dropdown = Gtk.DropDown(model=sort_model)
        self._sort_dropdown.set_tooltip_text("Sort by")
        self._sort_dropdown.connect("notify::selected", self._on_sort_changed)
        bar.append(self._sort_dropdown)

        self.append(bar)

    def _build_grid(self) -> None:
        self._flowbox = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.MULTIPLE,
            homogeneous=True,
            row_spacing=8,
            column_spacing=8,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )
        self._flowbox.bind_model(self._store, self._create_thumb_widget)

        scroller = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scroller.set_child(self._flowbox)
        self.append(scroller)

    def _create_thumb_widget(self, item: ThumbnailItem) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, width_request=110)
        picture = Gtk.Picture(
            content_fit=Gtk.ContentFit.COVER, width_request=100, height_request=100
        )
        box.append(picture)
        label = Gtk.Label(label=Path(item.path).name, ellipsize=3, max_width_chars=14)
        box.append(label)

        def _load_thumb():
            try:
                thumb = get_thumbnail_path(item.path)
                GLib.idle_add(self._set_picture_rotated, picture, str(thumb), item.rotation)
            except Exception:
                pass

        GLib.Thread.new(None, _load_thumb)
        item.connect(
            "notify::rotation",
            lambda it, _pspec: self._set_picture_rotated(
                picture, str(get_thumbnail_path(item.path)), it.rotation
            ),
        )

        # FlowBox's default click behavior only ever selects (never
        # deselects) on a plain click; toggling requires Ctrl/Shift.
        # Intercept in the capture phase so a plain click toggles instead.
        click = Gtk.GestureClick(button=1)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def _on_click(gesture, _n_press, _x, _y) -> None:
            child = box.get_parent()
            if child is None:
                return
            if child.is_selected():
                self._flowbox.unselect_child(child)
            else:
                self._flowbox.select_child(child)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        click.connect("pressed", _on_click)
        box.add_controller(click)
        return box

    def _set_picture_rotated(self, picture: Gtk.Picture, thumb_path: str, rotation: int) -> None:
        try:
            img = Image.open(thumb_path).convert("RGB")
            if rotation:
                img = img.rotate(-rotation, expand=True)
            data = img.tobytes()
            w, h = img.size
            pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(data), GdkPixbuf.Colorspace.RGB, False, 8, w, h, w * 3
            )
            picture.set_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
        except Exception:
            picture.set_filename(thumb_path)

    # -- drag & drop ---------------------------------------------------
    def _setup_dnd(self) -> None:
        target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        target.connect("drop", self._on_drop)
        self._flowbox.add_controller(target)

    def _on_drop(self, _target, value: Gdk.FileList, _x, _y) -> bool:
        paths = []
        for gfile in value.get_files():
            p = gfile.get_path()
            if p:
                if os.path.isdir(p):
                    paths.extend(self._scan_folder(p))
                elif is_supported(p):
                    paths.append(p)
        self._add_paths(paths)
        return True

    # -- toolbar handlers ------------------------------------------------
    def _on_add_images(self, _btn) -> None:
        dialog = Gtk.FileDialog(title="Add Images")
        filt = Gtk.FileFilter(name="Images")
        for ext in SUPPORTED_EXTENSIONS:
            filt.add_suffix(ext.lstrip("."))
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filt)
        dialog.set_filters(filters)
        dialog.open_multiple(None, None, self._on_files_chosen)

    def _on_files_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            files = dialog.open_multiple_finish(result)
        except GLib.Error:
            return
        paths = [f.get_path() for f in files if f.get_path()]
        self._add_paths([p for p in paths if is_supported(p)])

    def _on_add_folder(self, _btn) -> None:
        dialog = Gtk.FileDialog(title="Add Folder")
        dialog.select_folder(None, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        path = folder.get_path()
        if path:
            self._add_paths(self._scan_folder(path))

    def _scan_folder(self, folder: str) -> list[str]:
        found = []
        for root, _dirs, files in os.walk(folder):
            for name in files:
                p = os.path.join(root, name)
                if is_supported(p):
                    found.append(p)
        return found

    def _on_rotate_selected(self, delta: int) -> None:
        selected = self._flowbox.get_selected_children()
        if not selected:
            return
        for child in selected:
            item = self._store.get_item(child.get_index())
            item.rotation = (item.rotation + delta) % 360
        self._emit_changed()

    def get_rotations(self) -> dict[str, int]:
        return {
            self._store.get_item(i).path: self._store.get_item(i).rotation
            for i in range(self._store.get_n_items())
            if self._store.get_item(i).rotation
        }

    def _on_remove_selected(self, _btn) -> None:
        selected = self._flowbox.get_selected_children()
        indices = sorted((c.get_index() for c in selected), reverse=True)
        for i in indices:
            self._store.remove(i)
        self._emit_changed()

    def _on_clear_all(self, _btn) -> None:
        self._store.remove_all()
        self._emit_changed()

    def _on_sort_changed(self, dropdown: Gtk.DropDown, _pspec) -> None:
        mode = ["name", "date", "size", "random"][dropdown.get_selected()]
        self._sort(mode)

    def _sort(self, mode: str) -> None:
        rotations = self.get_rotations()
        paths = [self._store.get_item(i).path for i in range(self._store.get_n_items())]
        if mode == "name":
            paths.sort(key=lambda p: Path(p).name.lower())
        elif mode == "date":
            paths.sort(key=lambda p: os.path.getmtime(p))
        elif mode == "size":
            paths.sort(key=lambda p: os.path.getsize(p))
        elif mode == "random":
            random.shuffle(paths)
        self._store.remove_all()
        for p in paths:
            item = ThumbnailItem(p)
            item.rotation = rotations.get(p, 0)
            self._store.append(item)
        self._emit_changed()

    # -- public API --------------------------------------------------
    def add_paths(self, paths: list[str]) -> None:
        self._add_paths([p for p in paths if is_supported(p)])

    def _add_paths(self, paths: list[str]) -> None:
        existing = {self._store.get_item(i).path for i in range(self._store.get_n_items())}
        for p in paths:
            if p not in existing:
                self._store.append(ThumbnailItem(p))
                existing.add(p)
        self._emit_changed()

    def _emit_changed(self) -> None:
        paths = [self._store.get_item(i).path for i in range(self._store.get_n_items())]
        self._on_changed(paths)

    def get_paths(self) -> list[str]:
        return [self._store.get_item(i).path for i in range(self._store.get_n_items())]
