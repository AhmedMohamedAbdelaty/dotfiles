local var_mainMod = "Super"
local var_term = "kitty"
local var_file = "dolphin"
local var_editor = "code"
local var_browser = "brave"
local var_moveactivewindow = "grep -q \"true\" <<< $(hyprctl activewindow -j | jq -r .floating) && hyprctl dispatch moveactive"

-- █▄▀ █▀▀ █▄█ █▄▄ █ █▄░█ █▀▄ █ █▄░█ █▀▀ █▀

-- █░█ ██▄ ░█░ █▄█ █ █░▀█ █▄▀ █ █░▀█ █▄█ ▄█

-- See https://wiki.hyprland.org/Configuring/Keywords/

-- &  https://wiki.hyprland.org/Configuring/Binds/

-- Main modifier

-- Assign apps

-- █░█ ██▄ ░█░ █▄█ █ █░▀█ █▄▀ █ █░▀█ █▄█ ▄█

-- See https://wiki.hyprland.org/Configuring/Keywords/

-- &  https://wiki.hyprland.org/Configuri# notification center keybinds (dunst)
hl.bind(var_mainMod .. " + N", hl.dsp.exec_cmd("dunstctl history-pop"))
hl.bind(var_mainMod .. " + SHIFT + N", hl.dsp.exec_cmd("dunstctl close-all"))
hl.bind(var_mainMod .. " + CTRL + N", hl.dsp.exec_cmd("dunstctl set-paused toggle"))
hl.bind(var_mainMod .. " + ALT + N", hl.dsp.exec_cmd("dunstctl context"))

-- Quick notification actions
hl.bind(var_mainMod .. " + comma", hl.dsp.exec_cmd("swaync-client -cp"))
hl.bind(var_mainMod .. " + SHIFT + comma", hl.dsp.exec_cmd("swaync-client -C"))

-- Main modifier

-- Assign apps

-- Window/Session actions
hl.bind(var_mainMod .. "+Shift + P", hl.dsp.exec_cmd("hyprpicker -a"), {
    description = "Color Picker",
})
hl.bind(var_mainMod .. " + Q", hl.dsp.exec_cmd(var_scrPath .. "/dontkillsteam.sh"))
hl.bind("ALT + F4", hl.dsp.exec_cmd(var_scrPath .. "/dontkillsteam.sh"))
hl.bind(var_mainMod .. " + Delete", hl.dsp.exit())
hl.bind(var_mainMod .. " + W", hl.dsp.window.float({ action = "toggle" }))
hl.bind(var_mainMod .. " + G", hl.dsp.group.toggle())
hl.bind("ALT + Return", hl.dsp.window.fullscreen())
hl.bind(var_mainMod .. " + L", hl.dsp.exec_cmd("swaylock"))
hl.bind(var_mainMod .. "+Shift + F", hl.dsp.exec_cmd(var_scrPath .. "/windowpin.sh"))
hl.bind(var_mainMod .. " + Backspace", hl.dsp.exec_cmd(var_scrPath .. "/logoutlaunch.sh"))
hl.bind("CTRL + ALT + W", hl.dsp.exec_cmd("killall waybar || waybar"))
hl.bind(var_mainMod .. "+Ctrl + T", hl.dsp.exec_cmd("~/.config/waybar/restart-tray.sh"))

-- Application shortcuts
hl.bind(var_mainMod .. " + T", hl.dsp.exec_cmd(var_term))
hl.bind(var_mainMod .. " + E", hl.dsp.exec_cmd(var_file))
hl.bind(var_mainMod .. " + C", hl.dsp.exec_cmd(var_editor))
hl.bind(var_mainMod .. " + F", hl.dsp.exec_cmd(var_browser))
hl.bind("CTRL + SHIFT + Escape", hl.dsp.exec_cmd(var_scrPath .. "/sysmonlaunch.sh"))

-- Open obsidian
hl.bind(var_mainMod .. " + O", hl.dsp.exec_cmd("obsidian"))

-- Rofi menus
hl.bind(var_mainMod .. " + A", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/rofilaunch.sh d"))
hl.bind(var_mainMod .. " + Tab", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/rofilaunch.sh w"))
hl.bind(var_mainMod .. "+Shift + E", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/rofilaunch.sh f"))

-- Audio control
hl.bind("F10", hl.dsp.exec_cmd(var_scrPath .. "/volumecontrol.sh -o m"), {
    locked = true,
})
hl.bind("F11", hl.dsp.exec_cmd(var_scrPath .. "/volumecontrol.sh -o d"), {
    repeating = true,
    locked = true,
})
hl.bind("F12", hl.dsp.exec_cmd(var_scrPath .. "/volumecontrol.sh -o i"), {
    repeating = true,
    locked = true,
})
hl.bind("XF86AudioMute", hl.dsp.exec_cmd(var_scrPath .. "/volumecontrol.sh -o m"), {
    locked = true,
})
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd(var_scrPath .. "/volumecontrol.sh -i m"), {
    locked = true,
})
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd(var_scrPath .. "/volumecontrol.sh -o d"), {
    repeating = true,
    locked = true,
})
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd(var_scrPath .. "/volumecontrol.sh -o i"), {
    repeating = true,
    locked = true,
})

-- Media control
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), {
    locked = true,
})
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), {
    locked = true,
})
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), {
    locked = true,
})
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), {
    locked = true,
})

-- Brightness control
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd(var_scrPath .. "/brightnesscontrol.sh i"), {
    repeating = true,
    locked = true,
})
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(var_scrPath .. "/brightnesscontrol.sh d"), {
    repeating = true,
    locked = true,
})

-- Move between grouped windows
hl.bind(var_mainMod .. " + CTRL + H", hl.dsp.group.prev())
hl.bind(var_mainMod .. " + CTRL + L", hl.dsp.group.next())

-- Screenshot/Screencapture
hl.bind(var_mainMod .. " + P", hl.dsp.exec_cmd(var_scrPath .. "/screenshot.sh s"))
hl.bind(var_mainMod .. "+Ctrl + P", hl.dsp.exec_cmd(var_scrPath .. "/screenshot.sh sf"))
hl.bind(var_mainMod .. "+Alt + P", hl.dsp.exec_cmd(var_scrPath .. "/screenshot.sh m"))
hl.bind("Print", hl.dsp.exec_cmd(var_scrPath .. "/screenshot.sh p"))

-- Custom scripts
hl.bind(var_mainMod .. "+Alt + G", hl.dsp.exec_cmd(var_scrPath .. "/gamemode.sh"))

-- bind = $mainMod+Alt, Right, exec, $scrPath/swwwallpaper.sh -n # next wallpaper

-- bind = $mainMod+Alt, Left, exec, $scrPath/swwwallpaper.sh -p # previous wallpaper

-- bind = $mainMod+Alt, Up, exec, $scrPath/wbarconfgen.sh n # next waybar mode

-- bind = $mainMod+Alt, Down, exec, $scrPath/wbarconfgen.sh p # previous waybar mode
hl.bind(var_mainMod .. "+Shift + R", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/wallbashtoggle.sh -m"))
hl.bind(var_mainMod .. "+Shift + T", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/themeselect.sh"))
hl.bind(var_mainMod .. "+Shift + A", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/rofiselect.sh"))
hl.bind(var_mainMod .. "+Shift + W", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/swwwallselect.sh"))

-- bind = $mainMod, V, exec, pkill -x rofi || $scrPath/cliphist.sh c # launch clipboard

-- bind = $mainMod+Shift, V, exec, pkill -x rofi || $scrPath/cliphist.sh # launch clipboard Manager
hl.bind(var_mainMod .. " + V", hl.dsp.exec_cmd("copyq show"))
hl.bind(var_mainMod .. "+Shift + V", hl.dsp.exec_cmd("copyq menu"))
hl.bind(var_mainMod .. " + K", hl.dsp.exec_cmd(var_scrPath .. "/keyboardswitch.sh"))
hl.bind(var_mainMod .. " + slash", hl.dsp.exec_cmd("pkill -x rofi || " .. var_scrPath .. "/keybinds_hint.sh c"))

-- Move/Change window focus
hl.bind(var_mainMod .. " + Left", hl.dsp.focus({ direction = "left" }))
hl.bind(var_mainMod .. " + Right", hl.dsp.focus({ direction = "right" }))
hl.bind(var_mainMod .. " + Up", hl.dsp.focus({ direction = "up" }))
hl.bind(var_mainMod .. " + Down", hl.dsp.focus({ direction = "down" }))
hl.bind("ALT + Tab", hl.dsp.focus({ direction = "down" }))

-- Switch workspaces
hl.bind(var_mainMod .. " + 1", hl.dsp.focus({ workspace = 1 }))
hl.bind(var_mainMod .. " + 2", hl.dsp.focus({ workspace = 2 }))
hl.bind(var_mainMod .. " + 3", hl.dsp.focus({ workspace = 3 }))
hl.bind(var_mainMod .. " + 4", hl.dsp.focus({ workspace = 4 }))
hl.bind(var_mainMod .. " + 5", hl.dsp.focus({ workspace = 5 }))
hl.bind(var_mainMod .. " + 6", hl.dsp.focus({ workspace = 6 }))
hl.bind(var_mainMod .. " + 7", hl.dsp.focus({ workspace = 7 }))
hl.bind(var_mainMod .. " + 8", hl.dsp.focus({ workspace = 8 }))
hl.bind(var_mainMod .. " + 9", hl.dsp.focus({ workspace = 9 }))
hl.bind(var_mainMod .. " + 0", hl.dsp.focus({ workspace = 10 }))

-- Switch workspaces to a relative workspace
hl.bind(var_mainMod .. "+Ctrl + Right", hl.dsp.focus({ workspace = "r+1" }))
hl.bind(var_mainMod .. "+Ctrl + Left", hl.dsp.focus({ workspace = "r-1" }))

-- Move to the first empty workspace
hl.bind(var_mainMod .. "+Ctrl + Down", hl.dsp.focus({ workspace = "empty" }))

-- Resize windows
hl.bind(var_mainMod .. "+Shift + Right", hl.dsp.window.resize({ x = 30, y = 0, relative = true }), {
    repeating = true,
})
hl.bind(var_mainMod .. "+Shift + Left", hl.dsp.window.resize({ x = -30, y = 0, relative = true }), {
    repeating = true,
})
hl.bind(var_mainMod .. "+Shift + Up", hl.dsp.window.resize({ x = 0, y = -30, relative = true }), {
    repeating = true,
})
hl.bind(var_mainMod .. "+Shift + Down", hl.dsp.window.resize({ x = 0, y = 30, relative = true }), {
    repeating = true,
})

-- Move focused window to a workspace
hl.bind(var_mainMod .. "+Shift + 1", hl.dsp.window.move({ workspace = 1 }))
hl.bind(var_mainMod .. "+Shift + 2", hl.dsp.window.move({ workspace = 2 }))
hl.bind(var_mainMod .. "+Shift + 3", hl.dsp.window.move({ workspace = 3 }))
hl.bind(var_mainMod .. "+Shift + 4", hl.dsp.window.move({ workspace = 4 }))
hl.bind(var_mainMod .. "+Shift + 5", hl.dsp.window.move({ workspace = 5 }))
hl.bind(var_mainMod .. "+Shift + 6", hl.dsp.window.move({ workspace = 6 }))
hl.bind(var_mainMod .. "+Shift + 7", hl.dsp.window.move({ workspace = 7 }))
hl.bind(var_mainMod .. "+Shift + 8", hl.dsp.window.move({ workspace = 8 }))
hl.bind(var_mainMod .. "+Shift + 9", hl.dsp.window.move({ workspace = 9 }))
hl.bind(var_mainMod .. "+Shift + 0", hl.dsp.window.move({ workspace = 10 }))

-- Move focused window to a relative workspace
hl.bind(var_mainMod .. "+Ctrl+Alt + Right", hl.dsp.window.move({ workspace = "r+1" }))
hl.bind(var_mainMod .. "+Ctrl+Alt + Left", hl.dsp.window.move({ workspace = "r-1" }))

-- Move active window around current workspace with mainMod + SHIFT + CTRL [←→↑↓]
hl.bind(var_mainMod .. " + SHIFT + $CONTROL + left", hl.dsp.exec_cmd(var_moveactivewindow .. " -30 0 || hyprctl dispatch movewindow l"), {
    repeating = true,
    description = "Move activewindow to the right",
})
hl.bind(var_mainMod .. " + SHIFT + $CONTROL + right", hl.dsp.exec_cmd(var_moveactivewindow .. " 30 0 || hyprctl dispatch movewindow r"), {
    repeating = true,
    description = "Move activewindow to the right",
})
hl.bind(var_mainMod .. " + SHIFT + $CONTROL + up", hl.dsp.exec_cmd(var_moveactivewindow .. "  0 -30 || hyprctl dispatch movewindow u"), {
    repeating = true,
    description = "Move activewindow to the right",
})
hl.bind(var_mainMod .. " + SHIFT + $CONTROL + down", hl.dsp.exec_cmd(var_moveactivewindow .. " 0 30 || hyprctl dispatch movewindow d"), {
    repeating = true,
    description = "Move activewindow to the right",
})

-- Enable moving windows between monitors with directional keys (Hyprland 0.54+)
hl.config({
    binds = {
        window_direction_monitor_fallback = true,
    },
})

-- Scroll through existing workspaces
hl.bind(var_mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(var_mainMod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }))

-- Move/Resize focused window
hl.bind(var_mainMod .. " + mouse:272", hl.dsp.window.drag(), {
    mouse = true,
})
hl.bind(var_mainMod .. " + mouse:273", hl.dsp.window.resize(), {
    mouse = true,
})
hl.bind(var_mainMod .. " + Z", hl.dsp.window.drag(), {
    mouse = true,
})
hl.bind(var_mainMod .. " + X", hl.dsp.window.resize(), {
    mouse = true,
})

-- Move/Switch to special workspace (scratchpad)
hl.bind(var_mainMod .. "+Alt + S", hl.dsp.window.move({ workspace = "special", silent = true }))
hl.bind(var_mainMod .. " + S", hl.dsp.workspace.toggle_special(""))

-- Toggle focused window split

-- bind = $mainMod, J, togglesplit

-- Move focused window to a workspace silently
hl.bind(var_mainMod .. "+Alt + 1", hl.dsp.window.move({ workspace = 1, silent = true }))
hl.bind(var_mainMod .. "+Alt + 2", hl.dsp.window.move({ workspace = 2, silent = true }))
hl.bind(var_mainMod .. "+Alt + 3", hl.dsp.window.move({ workspace = 3, silent = true }))
hl.bind(var_mainMod .. "+Alt + 4", hl.dsp.window.move({ workspace = 4, silent = true }))
hl.bind(var_mainMod .. "+Alt + 5", hl.dsp.window.move({ workspace = 5, silent = true }))
hl.bind(var_mainMod .. "+Alt + 6", hl.dsp.window.move({ workspace = 6, silent = true }))
hl.bind(var_mainMod .. "+Alt + 7", hl.dsp.window.move({ workspace = 7, silent = true }))
hl.bind(var_mainMod .. "+Alt + 8", hl.dsp.window.move({ workspace = 8, silent = true }))
hl.bind(var_mainMod .. "+Alt + 9", hl.dsp.window.move({ workspace = 9, silent = true }))
hl.bind(var_mainMod .. "+Alt + 0", hl.dsp.window.move({ workspace = 10, silent = true }))

-- Hyprspace Overview Controls

-- bind = $mainMod, Y, overview:toggle         # Toggle on current monitor

-- bind = $mainMod SHIFT, Y, overview:toggle,all  # Toggle on all monitors

-- bind = $mainMod ALT, Y, overview:close      # Force close

-- bind = SUPER, escape, overview:close        # Additional escape option

-- s# # # # # # #

-- notification center keybinds (swaync)
hl.bind(var_mainMod .. " + N", hl.dsp.exec_cmd("swaync-client -t -sw"))
hl.bind(var_mainMod .. " + SHIFT + N", hl.dsp.exec_cmd("swaync-client -C"))
hl.bind(var_mainMod .. " + CTRL + N", hl.dsp.exec_cmd("swaync-client -d -sw"))
hl.bind(var_mainMod .. " + ALT + N", hl.dsp.exec_cmd("swaync-client --reload-config"))

-- Quick notification actions
hl.bind(var_mainMod .. " + comma", hl.dsp.exec_cmd("swaync-client -cp"))
hl.bind(var_mainMod .. " + SHIFT + comma", hl.dsp.exec_cmd("swaync-client -C"))
