# Ax-Shell

Personal Hyprland shell setup based on [Axenide/Ax-Shell](https://github.com/Axenide/Ax-Shell).

This repo is my recovery guide as much as my desktop setup. If I break something, this is the file I come back to first.

## Purpose

- Keep one known-good Ax-Shell setup.
- Make it easy to restore config, fonts, and keybinds after I break them.
- Document where the important pieces live so I do not have to rediscover them later.

## What This Repo Runs

- Main Ax-Shell app entrypoint: `main.py`
- Hyprland bootstrap config: `hyprland.conf`
- Ax-Shell source file: `config/hypr/ax-shell.conf`
- Config GUI entrypoint: `config/config.py`
- Config data and defaults: `config/config.json` and `config/settings_constants.py`
- Theme output: `styles/colors.css` and `config/hypr/colors.conf`
- Wallpaper defaults: `assets/wallpapers_example/`

## Features In This Fork

- Top, bottom, left, or right bar placement.
- Centered bar support.
- Dock with size and visibility controls.
- Notch-style launcher panel with dashboard, launcher, overview, tools, power, wallpapers, emoji, clipboard history, Bluetooth, Kanban, Tmux, and player widgets.
- Dynamic Hyprland workspaces, including add and remove support.
- System tray.
- Notifications.
- Weather.
- CPU, RAM, disk, GPU, and battery metrics.
- Clock format toggle for 12-hour or 24-hour time.
- Wallpaper switching and random wallpaper action.
- Caffeine toggle.
- CSS reload without restarting the whole shell.
- Power mode scripts.
- Battery monitor and battery status script.
- Shader and visual widgets.
- Settings GUI for keybinds, appearance, terminal, Hyprland options, and reset.
- Matugen integration for wallpaper-driven color generation.

## Install Or Repair

If this repo is cloned on a new machine, start here:

```bash
bash install.sh
```

That script should:

- clone or update Ax-Shell into `~/.config/Ax-Shell`
- install required Arch/AUR packages
- install Python/runtime dependencies used by the code
- install fonts into `~/.fonts/zed-sans` and `~/.fonts/tabler-icons`
- generate config files if they do not exist
- start Ax-Shell through `uwsm`

If install fails, check these first:

- `yay` or `paru` exists and works.
- Network access is available.
- You are not running as root.
- Hyprland, `uwsm`, and the required Python/GTK packages are installed.

## Important Files When Fixing Things

- Hyprland entry file: `hyprland.conf`
- Ax-Shell source include: `config/hypr/ax-shell.conf`
- Main config values: `config/config.json`
- Default config values: `config/settings_constants.py`
- Settings GUI behavior: `config/settings_gui.py`
- Runtime startup: `main.py`
- Package installer: `install.sh`

## How I Reload Things

- Reload Ax-Shell: `SUPER + ALT + B`
- Reload CSS: `SUPER + SHIFT + B`
- Restart with inspector: `SUPER + CTRL + ALT + B`
- Open settings from launcher: use the config button in the launcher panel

## Keybinds I Care About

- `SUPER + D`: dashboard
- `SUPER + R`: launcher
- `SUPER + TAB`: overview
- `SUPER + S`: toolbox
- `SUPER + V`: clipboard history
- `SUPER + Y`: Bluetooth
- `SUPER + K`: Kanban
- `SUPER + COMMA`: wallpapers
- `SUPER + PERIOD`: emoji picker
- `SUPER + ESCAPE`: power menu
- `SUPER + SHIFT + C`: caffeine toggle
- `SUPER + SHIFT + B`: reload CSS
- `SUPER + ALT + B`: reload Ax-Shell

## Recovery Checklist

- If Ax-Shell does not start, verify Hyprland is launching `uwsm` and that `main.py` runs cleanly.
- If the bar or notch is missing, check `config/hypr/ax-shell.conf` and `config/config.json`.
- If colors or CSS look wrong, rerun matugen or use the reload CSS bind.
- If wallpapers fail, confirm `~/.current.wall` points to a valid file and `assets/wallpapers_example/` still exists.
- If fonts look wrong, rerun `install.sh` and confirm both font directories exist.
- If keybinds feel wrong, edit `config/config.json` and then reload Ax-Shell.
- If config is corrupted, restore `config/config.json.bak`.

## Uninstall

- Use `uninstall.sh` to remove configs and the Hyprland entry.

## Credits

- Base project: [Axenide/Ax-Shell](https://github.com/Axenide/Ax-Shell)
- Some changes in this fork are mine.
