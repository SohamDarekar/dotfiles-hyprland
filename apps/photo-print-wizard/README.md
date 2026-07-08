# Photo Print Wizard

Native GTK4 + Libadwaita photo printing application for Linux, inspired by
(and improving on) the Windows "Print Pictures" wizard. Built for Arch
Linux / Wayland / Hyprland, printing through CUPS.

No Electron, no web tech, no Qt WebEngine.

## Features

- Thumbnail grid with drag & drop, folder import, sort by name/date/size/random
- Physical-unit layout engine (mm → DPI → px), never pixel-first math
- Built-in presets: Full Page, 13×18 cm, 10×15 cm, 9×13 cm, 8×10 in, Wallet (9-up),
  Passport (India/Australia/USA/UK/Canada), Custom Layout
- Automatic pagination — select N photos, get exactly as many pages as needed
- Crop modes: Fit, Fill (center-crop), Smart Crop (face-aware, optional OpenCV), Stretch
- Live WYSIWYG preview (same Cairo renderer used for print/export) with zoom & pan
- CUPS printing via `pycups` — enumerates existing printers only, never touches
  printer configuration
- Export to PDF (vector) or PNG/JPEG/TIFF (raster, chosen DPI)
- Settings persisted per XDG spec

## Architecture

```
src/photo_print_wizard/
  layout/     physical-unit geometry, presets, pagination (no UI, no rendering)
  imaging/    Pillow-based load/orient/crop/thumbnail-cache
  render/     Cairo page renderer — shared by screen preview, PDF export, raster export
  printing/   CUPS backend (pycups) — enumerate + submit jobs only
  settings/   JSON settings store (~/.config/photo-print-wizard/)
  ui/         GTK4/Libadwaita widgets — no business logic
```

Layout math is always done in millimetres; pixels only exist at the render
boundary for a specific DPI target, so preview and print are guaranteed to
match.

## Requirements (Arch Linux)

System packages (already satisfied on most GNOME/Hyprland desktops):

```bash
sudo pacman -S gtk4 libadwaita python-gobject python-pycups python-cairo python-pillow
```

Optional (Smart Crop face detection):

```bash
pip install opencv-python-headless
```

## Running

```bash
cd apps/photo-print-wizard
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e .
.venv/bin/photo-print-wizard
# or
.venv/bin/python -m photo_print_wizard
```

The `--system-site-packages` flag is required so the venv can see the
system-installed PyGObject/GTK4/Adwaita bindings and pycups (these are not
pip-installable in the general case on Arch).

## Desktop integration

A `.desktop` file and SVG icon live under `data/`. Nothing is installed
automatically — run:

```bash
./install.sh
```

to copy them into `~/.local/share/applications/` and `~/.local/share/icons/`.
This only touches your user-local data directories; it does not touch
system paths, CUPS configuration, or Hyprland config.

## Testing

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/ruff check src
```

## Status

Core MVP: layout engine, pagination, imaging, Cairo renderer, CUPS backend,
settings, and full GTK4 UI are implemented and wired together. Contact
Sheet captions, ICC profiles, project save/load, ink/cost estimation and
Flatpak packaging are follow-up phases, not yet implemented.

## License

MIT — see [LICENSE](LICENSE).
