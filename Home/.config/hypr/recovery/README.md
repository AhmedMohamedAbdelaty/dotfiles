# Restored Hyprland setup

The active configuration is `~/.config/hypr/hyprland.lua`, generated from the 11 files sourced by the original `hyprland.conf`. Older incomplete Lua modules are retained but not loaded.

Keep editing your original `.conf` files for personal settings. Apply changes with:

```sh
python ~/.config/hypr/recovery/rebuild.py && hyprctl reload
```

The generator validates the native Lua before replacing the active file. Direct edits to generated `hyprland.lua` will be replaced by regeneration. Wallpaper/theme and animation controls regenerate automatically. The shortcut menu reads `recovery/binds.json`.

Pre-recovery config, helper scripts and Waybar config are saved at:

`/home/ahmed/.local/state/hyprland-recovery/20261102-115932`

The original `.conf` files remain the editable sources, with compatibility fixes applied where needed. Session startup is configured, but no saved app-session state existed at recovery time. No packages were changed.

## Compatibility fixes

Kitty no longer restores a maximized OS window (`remember_window_size no` in `~/.config/kitty/userprefs.conf`). Deliberate fullscreen shortcuts remain available.

Theme rebuilding supports all 12 installed HyDE templates, including old layer-blur syntax and removed shadow defaults. All 18 animation presets validate, including disabled animation leaves. Theme/cursor commands run through compositor lifecycle hooks, so validation does not execute them. Rebuild validation uses an isolated runtime and preserves the previous Lua on failure.

Logout, idle DPMS, Waybar actions, window pinning, session restore, screenshots and theme refresh use Lua-compatible compositor calls. Game mode reads the new boolean option representation. Session save/restore succeeds when notifications are disabled.

The active startup chain remains the original `hyprland.conf` and its includes. Unsourced historical files under `conf/` are retained as history.

## Original desktop UI

Super+/ uses the original HyDE shortcut renderer, grouped sections, Rofi theme, font, icons and geometry overrides. `keybind-menu.py` adapts its metadata and selections to Lua actions.

Waybar runs through the packaged `waybar.service` user unit, enabled for `graphical-session.target` so it starts after the graphical session is ready. Startup imports the compositor's environment; Ctrl+Alt+W toggles the service, and game mode and layout generation restart it. Restore the autostart link with `systemctl --user enable waybar.service` if needed.

The theme, wallpaper, style, animation and clipboard menus convert display scale numerically, including integer and fractional values. Theme and wallpaper menus fall back to the source image when a cached preview is missing. Rebuild previews with `swwwallcache.sh -t "Catppuccin Mocha"` or `swwwallcache.sh -w /path/to/image`.
