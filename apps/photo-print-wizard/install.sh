#!/usr/bin/env bash
# Installs the .desktop entry and icon into your user-local data
# directories (~/.local/share/applications, ~/.local/share/icons).
#
# Does NOT touch anything outside $HOME/.local/share, does not use sudo,
# does not modify system paths, CUPS, or Hyprland config. Run manually:
#   ./install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="$SCRIPT_DIR/.venv/bin/photo-print-wizard"

if [[ ! -x "$VENV_BIN" ]]; then
    echo "error: $VENV_BIN not found." >&2
    echo "Run this first:" >&2
    echo "  python3 -m venv --system-site-packages .venv && .venv/bin/pip install -e ." >&2
    exit 1
fi

APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$APPS_DIR" "$ICON_DIR"

sed "s|__EXEC__|$VENV_BIN|" "$SCRIPT_DIR/data/photo-print-wizard.desktop.in" \
    > "$APPS_DIR/photo-print-wizard.desktop"

cp "$SCRIPT_DIR/data/icons/photo-print-wizard.svg" "$ICON_DIR/photo-print-wizard.svg"

command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$APPS_DIR" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Installed:"
echo "  $APPS_DIR/photo-print-wizard.desktop"
echo "  $ICON_DIR/photo-print-wizard.svg"
echo "Photo Print Wizard should now appear in your app launcher."
