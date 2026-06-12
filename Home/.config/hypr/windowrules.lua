-- █░█░█ █ █▄░█ █▀▄ █▀█ █░█░█   █▀█ █░█ █░░ █▀▀ █▀

-- ▀▄▀▄▀ █ █░▀█ █▄▀ █▄█ ▀▄▀▄▀   █▀▄ █▄█ █▄▄ ██▄ ▄█

-- See https://wiki.hyprland.org/Configuring/Window-Rules/

-- Updated for Hyprland 0.53+ syntax

-- Opacity rules for browsers
hl.window_rule({
    match = {
        class = "^(firefox)$",
    },
    opacity = "0.90 0.90",
})
hl.window_rule({
    match = {
        class = "^(Google-chrome)$",
    },
    opacity = "0.90 0.90",
})
hl.window_rule({
    match = {
        class = "^(Brave-browser)$",
    },
    opacity = "0.90 0.90",
})

-- Opacity rules for code editors
hl.window_rule({
    match = {
        class = "^(code-oss)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^([Cc]ode)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(code-url-handler)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(code-insiders-url-handler)$",
    },
    opacity = "0.80 0.80",
})

-- Opacity rules for terminals and file managers
hl.window_rule({
    match = {
        class = "^(kitty)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(org.kde.dolphin)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(org.kde.ark)$",
    },
    opacity = "0.80 0.80",
})

-- Opacity rules for settings apps
hl.window_rule({
    match = {
        class = "^(nwg-look)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(qt5ct)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(qt6ct)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(kvantummanager)$",
    },
    opacity = "0.80 0.80",
})

-- Opacity rules for system utilities
hl.window_rule({
    match = {
        class = "^(org.pulseaudio.pavucontrol)$",
    },
    opacity = "0.80 0.70",
})
hl.window_rule({
    match = {
        class = "^(blueman-manager)$",
    },
    opacity = "0.80 0.70",
})
hl.window_rule({
    match = {
        class = "^(nm-applet)$",
    },
    opacity = "0.80 0.70",
})
hl.window_rule({
    match = {
        class = "^(nm-connection-editor)$",
    },
    opacity = "0.80 0.70",
})
hl.window_rule({
    match = {
        class = "^(org.kde.polkit-kde-authentication-agent-1)$",
    },
    opacity = "0.80 0.70",
})
hl.window_rule({
    match = {
        class = "^(polkit-gnome-authentication-agent-1)$",
    },
    opacity = "0.80 0.70",
})
hl.window_rule({
    match = {
        class = "^(org.freedesktop.impl.portal.desktop.gtk)$",
    },
    opacity = "0.80 0.70",
})
hl.window_rule({
    match = {
        class = "^(org.freedesktop.impl.portal.desktop.hyprland)$",
    },
    opacity = "0.80 0.70",
})

-- Opacity rules for Steam and Spotify
hl.window_rule({
    match = {
        class = "^([Ss]team)$",
    },
    opacity = "0.70 0.70",
})
hl.window_rule({
    match = {
        class = "^(steamwebhelper)$",
    },
    opacity = "0.70 0.70",
})
hl.window_rule({
    match = {
        class = "^([Ss]potify)$",
    },
    opacity = "0.70 0.70",
})
hl.window_rule({
    match = {
        title = "^(Spotify Free)$",
    },
    opacity = "0.70 0.70",
})
hl.window_rule({
    match = {
        title = "^(Spotify Premium)$",
    },
    opacity = "0.70 0.70",
})

-- Opacity rules for various apps
hl.window_rule({
    match = {
        class = "^(com.github.rafostar.Clapper)$",
    },
    opacity = "0.90 0.90",
})
hl.window_rule({
    match = {
        class = "^(com.github.tchx84.Flatseal)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(hu.kramo.Cartridges)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(com.obsproject.Studio)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(gnome-boxes)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(vesktop)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(discord)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(WebCord)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(ArmCord)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(app.drey.Warp)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(net.davidotek.pupgui2)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(yad)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(Signal)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(io.github.alainm23.planify)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(io.gitlab.theevilskeleton.Upscaler)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(com.github.unrud.VideoDownloader)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(io.gitlab.adhami3310.Impression)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(io.missioncenter.MissionCenter)$",
    },
    opacity = "0.80 0.80",
})
hl.window_rule({
    match = {
        class = "^(io.github.flattool.Warehouse)$",
    },
    opacity = "0.80 0.80",
})

-- Float rules for dolphin dialogs
hl.window_rule({
    match = {
        class = "^(org.kde.dolphin)$ match:title ^(Progress Dialog — Dolphin)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(org.kde.dolphin)$ match:title ^(Copying — Dolphin)$",
    },
    float = true,
})

-- Float rules for firefox
hl.window_rule({
    match = {
        title = "^(About Mozilla Firefox)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(firefox)$ match:title ^(Picture-in-Picture)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(firefox)$ match:title ^(Library)$",
    },
    float = true,
})

-- Float rules for terminal apps
hl.window_rule({
    match = {
        class = "^(kitty)$ match:title ^(top)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(kitty)$ match:title ^(btop)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(kitty)$ match:title ^(htop)$",
    },
    float = true,
})

-- Float rules for various applications
hl.window_rule({
    match = {
        class = "^(vlc)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(kvantummanager)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(qt5ct)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(qt6ct)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(nwg-look)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(org.kde.ark)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(org.pulseaudio.pavucontrol)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(blueman-manager)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(nm-applet)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(nm-connection-editor)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(org.kde.polkit-kde-authentication-agent-1)$",
    },
    float = true,
})

-- Float rules for GTK apps
hl.window_rule({
    match = {
        class = "^(Signal)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(com.github.rafostar.Clapper)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(app.drey.Warp)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(net.davidotek.pupgui2)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(yad)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(eog)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(io.github.alainm23.planify)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(io.gitlab.theevilskeleton.Upscaler)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(com.github.unrud.VideoDownloader)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(io.gitlab.adhami3310.Impression)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(io.missioncenter.MissionCenter)$",
    },
    float = true,
})

-- Common modals
hl.window_rule({
    match = {
        title = "^(Open)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        title = "^(Choose Files)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        title = "^(Save As)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        title = "^(Confirm to replace files)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        title = "^(File Operation Progress)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(xdg-desktop-portal-gtk)$",
    },
    float = true,
})

-- Screenshot tools rules
hl.window_rule({
    match = {
        class = "^(grimblast)$",
    },
    no_focus = true,
})
hl.window_rule({
    match = {
        class = "^(grim)$",
    },
    no_focus = true,
})
hl.window_rule({
    match = {
        class = "^(slurp)$",
    },
    no_focus = true,
})
hl.window_rule({
    match = {
        class = "^(grimblast)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(grim)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(slurp)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(slurp)$",
    },
    stay_focused = true,
})

-- Notification rules for dunst
hl.window_rule({
    match = {
        class = "^(dunst)$",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "^(dunst)$",
    },
    border_size = 0,
})
hl.window_rule({
    match = {
        class = "^(dunst)$",
    },
    no_focus = true,
})

-- █░░ ▄▀█ █▄█ █▀▀ █▀█   █▀█ █░█ █░░ █▀▀ █▀

-- █▄▄ █▀█ ░█░ ██▄ █▀▄   █▀▄ █▄█ █▄▄ ██▄ ▄█

-- vscode blur and opacity
hl.window_rule({
    match = {
        class = "^(code)$",
    },
    opacity = "0.95 override",
})
hl.window_rule({
    match = {
        class = "^(code)$",
    },
    no_blur = true,
})

-- swaync notification center
hl.window_rule({
    match = {
        class = "(swaync-notification-window)",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "(swaync-control-center)",
    },
    float = true,
})
hl.window_rule({
    match = {
        class = "(swaync-notification-window)",
    },
    border_size = 0,
})
hl.window_rule({
    match = {
        class = "(swaync-control-center)",
    },
    border_size = 0,
})
hl.window_rule({
    match = {
        class = "(swaync-notification-window)",
    },
    no_focus = true,
})
hl.window_rule({
    match = {
        class = "(swaync-control-center)",
    },
    opacity = 0.95,
})
