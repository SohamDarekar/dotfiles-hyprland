# Ax-Shell

This is my personal Hyprland shell setup. Most of this repo was built by [Axenide](https://github.com/axenide).

**Purpose:** Just a backup in case I break something.  

## Important Info

- Main config: `~/.config/Ax-Shell/hypr/ax-shell.conf`
- Hyprland config: `~/.config/Ax-Shell/hyprland.conf`
- Add this line only once in the **hyprland.conf** file: `source = ~/.config/Ax-Shell/config/hypr/ax-shell.conf`
- Most keybinds are available in: `~/.config/Ax-Shell/hypr/ax-shell.conf`
- Reload Ax-Shell using: ***SUPER + ALT + B***
- To add new wallpapers, add new images in this folder: `.config/Ax-Shell/assets/wallpapers_example`
- Custom styles: `~/.config/Ax-Shell/styles/`
- If you break the config, restore from `config.json.bak` or reset with the setup script.
- Update logic is in `modules/updater.py` and version info in `version.json`.
- Fonts are auto-installed to `~/.fonts/zed-sans` and `~/.fonts/tabler-icons`.
- Uninstall script: `uninstall.sh` (removes configs and Hyprland entry).

## Restore Tips

- If Ax-Shell doesn't start, check Python dependencies and Hyprland.
- If config is corrupted, copy `config/config.json.bak` to `config/config.json`.
- If fonts look weird, rerun the install script or copy fonts manually.
- For custom keybinds, edit `config/config.json` and reload.

## Credits

Most code by [Axenide](https://github.com/axenide).  
Official repo: [https://github.com/Axenide/Ax-Shell](https://github.com/Axenide/Ax-Shell)  
Some modules use my code.

---
