-- Ax-Shell keybinds & overrides (migrated from ax-shell.conf)

local function loadColors(path)
    local colors = {}
    local f = io.open(path, "r")
    if f then
        for line in f:lines() do
            local name, value = line:match("^%$(%a[%w_]*)%s*=%s*(.-)%s*$")
            if name then colors[name] = value end
        end
        f:close()
    end
    return colors
end

-- colors.conf stays hyprlang-style on purpose: matugen (Ax-Shell's theme
-- engine) regenerates it on every wallpaper/theme change, and hyprlock.conf
-- also sources it directly (hyprlock's parser is unaffected by the .conf
-- deprecation). We just read the plain "$name = value" lines here instead
-- of re-plumbing the whole theme pipeline into Lua.
local colors = loadColors("/home/soh4m/.config/Ax-Shell/config/hypr/colors.conf")

local fabricSend = "fabric-cli exec ax-shell"
local axMessage = [[notify-send "Axenide" "FIRE IN THE HOLE‼️🗣️🔥🕳️" -i "/home/soh4m/.config/Ax-Shell/assets/ax.png" -A "🗣️" -A "🔥" -A "🕳️" -a "Source Code"]]

-- exec-once equivalent: plain top-level calls run once as this script loads.
-- (hl.on("hyprland.start", ...) is NOT reliable for this -- that event fires
-- inconsistently relative to when this file's require() runs, so autostart
-- here silently no-op'd on some boots. The official example config never
-- uses hyprland.start for autostart either, only plain top-level exec_cmd.)
hl.exec_cmd("uwsm app -- python /home/soh4m/.config/Ax-Shell/main.py")
hl.exec_cmd("~/.config/Ax-Shell/scripts/monitor-watcher.sh")
hl.exec_cmd([[wl-paste --type text --watch cliphist store]])
hl.exec_cmd([[wl-paste --type image --watch cliphist store]])
hl.exec_cmd("~/.local/bin/mount-homelab")
hl.exec_cmd("/usr/lib/hyprpolkitagent")
hl.exec_cmd("gnome-keyring-daemon --start --components=secrets,pkcs11,ssh")
hl.exec_cmd("chmod +x ~/.config/Ax-Shell/scripts/battery-monitor.sh && ~/.config/Ax-Shell/scripts/battery-monitor.sh")
hl.exec_cmd("swww img ~/.current.wall")

-- hypridle/swww-daemon launch only lives here (fires on cold boot too, not
-- just manual reloads) -- do NOT also start them in the block above, that
-- caused a duplicate swww-daemon launch racing for the same IPC socket and
-- aborting (systemd-coredump showed two swww-daemon crashes every boot).
hl.on("config.reloaded", function()
    hl.exec_cmd([[pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle]])
    hl.exec_cmd("uwsm app -- swww-daemon")
end)

-- lazy/detach unmount so a dead/slow homelab SSH connection can never block
-- reboot/shutdown in an uninterruptible FUSE wait (observed: kernel hung-task
-- warning on fuse_do_getattr, needed a hard power cycle to recover). Lazy
-- unmount alone only detaches the mountpoint -- the sshfs process's
-- underlying ssh child keeps running and is what systemd-shutdown then
-- waits on, so kill that process too instead of just detaching.
hl.on("hyprland.shutdown", function()
    hl.exec_cmd([[fusermount3 -uz "$HOME/Homelab" 2>/dev/null; pkill -9 -f "sshfs nexus-vps-local" 2>/dev/null; pkill -9 -f "ssh:.*nexus-vps-local" 2>/dev/null || true]])
end)

----------------------------
-- Custom user keybinds --
----------------------------

hl.bind("SUPER + B", hl.dsp.exec_cmd("firefox"))

for i = 1, 10 do
    local key = i % 10 -- 10 maps to key 0
    hl.bind("SUPER + " .. key,         hl.dsp.focus({ workspace = i }))
    hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

hl.bind("CTRL + SHIFT + S", hl.dsp.exec_cmd("grimblast copy area"))
hl.bind("SUPER + W",        hl.dsp.window.close())
hl.bind("SUPER + F",        hl.dsp.exec_cmd("hyprctl dispatch fullscreen 1"))
hl.bind("SUPER + E",        hl.dsp.exec_cmd("nautilus"))
hl.bind("SUPER + SHIFT + F", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + CTRL + F",  hl.dsp.exec_cmd("hyprctl dispatch pin"))

hl.bind("SUPER + G",      hl.dsp.exec_cmd("nm-connection-editor"))
hl.bind("SUPER + Return", hl.dsp.exec_cmd("kitty"))

hl.bind("SUPER + left",  hl.dsp.focus({ direction = "left" }))
hl.bind("SUPER + right", hl.dsp.focus({ direction = "right" }))
hl.bind("SUPER + up",    hl.dsp.focus({ direction = "up" }))
hl.bind("SUPER + down",  hl.dsp.focus({ direction = "down" }))

hl.bind("SUPER + M",         hl.dsp.exec_cmd("hyprctl dispatch movetoworkspacesilent special:minimized"))
hl.bind("SUPER + SHIFT + M", hl.dsp.workspace.toggle_special("minimized"))

hl.bind("SUPER + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })

hl.bind("SUPER + SHIFT + R", hl.dsp.exec_cmd("code"))

hl.bind("SUPER + CTRL + left",  hl.dsp.exec_cmd("hyprctl dispatch resizeactive -50 0"))
hl.bind("SUPER + CTRL + right", hl.dsp.exec_cmd("hyprctl dispatch resizeactive 50 0"))
hl.bind("SUPER + CTRL + up",    hl.dsp.exec_cmd("hyprctl dispatch resizeactive 0 -50"))
hl.bind("SUPER + CTRL + down",  hl.dsp.exec_cmd("hyprctl dispatch resizeactive 0 50"))

hl.bind("SUPER + ALT + left",  hl.dsp.exec_cmd("hyprctl dispatch moveactive -50 0"))
hl.bind("SUPER + ALT + right", hl.dsp.exec_cmd("hyprctl dispatch moveactive 50 0"))
hl.bind("SUPER + ALT + up",    hl.dsp.exec_cmd("hyprctl dispatch moveactive 0 -50"))
hl.bind("SUPER + ALT + down",  hl.dsp.exec_cmd("hyprctl dispatch moveactive 0 50"))

hl.bind("SUPER + EQUAL", hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("calculator")']]))

hl.bind("SUPER + SHIFT + I", hl.dsp.exec_cmd("hyprpicker -a"))
hl.bind("SUPER + L",         hl.dsp.exec_cmd("hyprlock"))
hl.bind("SUPER + U",         hl.dsp.exec_cmd("/home/soh4m/.local/bin/monitor-menu"))
hl.bind("SUPER + CTRL + S",  hl.dsp.exec_cmd("systemctl suspend"))

hl.bind("SUPER + ALT + B", hl.dsp.exec_cmd([[systemctl --user stop 'app-Hyprland-python-*.scope' 2>/dev/null; sleep 0.3; uwsm app -- python /home/soh4m/.config/Ax-Shell/main.py]]))

hl.bind("SUPER + A", hl.dsp.exec_cmd("/home/soh4m/.config/Ax-Shell/scripts/show_battery_status.sh"))

hl.bind("SUPER + D",   hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("dashboard")']]))
hl.bind("SUPER + Y",   hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("bluetooth")']]))
hl.bind("SUPER + N",   hl.dsp.exec_cmd(fabricSend .. [[ 'notch.dashboard.widgets.buttons.night_mode_button.toggle_hyprsunset()']]))
hl.bind("SUPER + K",   hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("kanban")']]))
hl.bind("SUPER + R",   hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("launcher")']]))
hl.bind("SUPER + T",   hl.dsp.exec_cmd("alacritty"))
hl.bind("SUPER + V",   hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("cliphist")']]))
hl.bind("SUPER + S",   hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("tools")']]))
hl.bind("SUPER + TAB", hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("overview")']]))
hl.bind("SUPER + COMMA", hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("wallpapers")']]))
hl.bind("SUPER + SHIFT + COMMA", hl.dsp.exec_cmd(fabricSend .. [[ 'notch.dashboard.wallpapers.set_random_wallpaper(None, external=True)']]))
hl.bind("SUPER + PERIOD", hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("emoji")']]))
hl.bind("SUPER + ESCAPE", hl.dsp.exec_cmd(fabricSend .. [[ 'notch.open_notch("power")']]))
hl.bind("SUPER + SHIFT + C", hl.dsp.exec_cmd(fabricSend .. [[ 'notch.dashboard.widgets.buttons.caffeine_button.toggle_inhibit(external=True)']]))
hl.bind("SUPER + SHIFT + B", hl.dsp.exec_cmd(fabricSend .. [[ 'app.set_css()']]))
hl.bind("SUPER + CTRL + ALT + B", hl.dsp.exec_cmd([[systemctl --user stop 'app-Hyprland-python-*.scope' 2>/dev/null; sleep 0.3; GTK_DEBUG=interactive uwsm app -- python /home/soh4m/.config/Ax-Shell/main.py]]))

hl.bind("SUPER + P",                 hl.dsp.exec_cmd("~/.config/Ax-Shell/scripts/set_power_mode.sh powersave"))
hl.bind("SUPER + ALT + P",           hl.dsp.exec_cmd("~/.config/Ax-Shell/scripts/set_power_mode.sh ultra-powersave"))
hl.bind("SUPER + SHIFT + P",         hl.dsp.exec_cmd("~/.config/Ax-Shell/scripts/set_power_mode.sh performance"))
hl.bind("SUPER + CTRL + ALT + P",    hl.dsp.exec_cmd("~/.config/Ax-Shell/scripts/set_power_mode.sh disabled"))
hl.bind("SUPER + CTRL + SHIFT + P",  hl.dsp.exec_cmd("~/.config/Ax-Shell/scripts/set_power_mode.sh auto"))

hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),        { locked = true, repeating = true })
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),       { locked = true })

--------------------------
-- Windows / Workspaces --
--------------------------

hl.window_rule({
    name  = "firefox-pip",
    match = { title = "^(Picture-in-Picture)$" },
    float = true,
    pin   = true,
})

hl.window_rule({
    name  = "monitor-menu",
    match = { title = "^(monitor-menu)$" },
    float  = true,
    center = true,
    size   = "660 220",
})

------------------------------------
-- Ax-Shell look & feel overrides --
------------------------------------

hl.config({
    general = {
        col = {
            active_border   = "rgb(" .. (colors.primary or "99ccf9") .. ")",
            inactive_border = "rgb(" .. (colors.surface or "101418") .. ")",
        },
        gaps_in = 2,
        gaps_out = 4,
        border_size = 2,
        layout = "dwindle",
    },

    cursor = {
        no_warps = true,
    },

    decoration = {
        blur = {
            enabled = true,
            size = 5,
            passes = 3,
            new_optimizations = true,
            contrast = 1,
            brightness = 1,
        },
        rounding = 14,
        shadow = {
            enabled = true,
            range = 10,
            render_power = 2,
            color = "rgba(00000040)",
        },
    },
})

hl.curve("axShellBezier", { type = "bezier", points = { {0.4, 0.0}, {0.2, 1.0} } })
hl.animation({ leaf = "windows",    enabled = true, speed = 2.5, bezier = "axShellBezier", style = "popin 80%" })
hl.animation({ leaf = "border",     enabled = true, speed = 2.5, bezier = "axShellBezier" })
hl.animation({ leaf = "fade",       enabled = true, speed = 2.5, bezier = "axShellBezier" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 2.5, bezier = "axShellBezier", style = "slidefade 20%" })
