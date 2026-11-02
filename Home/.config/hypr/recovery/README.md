# Restored Hyprland setup

The active configuration is `~/.config/hypr/hyprland.lua`, generated from the 11 files sourced by the original `hyprland.conf`. Older incomplete Lua modules are retained but not loaded.

Keep editing your original `.conf` files for personal settings. Apply changes with:

```sh
python ~/.config/hypr/recovery/rebuild.py && hyprctl reload
```

The generator validates the native Lua before replacing the active file. Direct edits to generated `hyprland.lua` will be replaced by regeneration. Wallpaper/theme and animation controls regenerate automatically. The shortcut menu reads `recovery/binds.json`.

Pre-recovery config, helper scripts and Waybar config are saved at:

`/home/ahmed/.local/state/hyprland-recovery/20261102-115932`

All original `.conf` files were retained unchanged. Session startup is configured, but no saved app-session state existed at recovery time. No packages were changed.

## Compatibility fixes

Kitty no longer restores a maximized OS window (`remember_window_size no` in `~/.config/kitty/userprefs.conf`). Deliberate fullscreen shortcuts remain available.

Theme rebuilding supports all 12 installed HyDE templates, including old layer-blur syntax and removed shadow defaults. All 18 animation presets validate, including disabled animation leaves. Theme/cursor commands run through compositor lifecycle hooks, so validation does not execute them. Rebuild validation uses an isolated runtime and preserves the previous Lua on failure.

Logout, idle DPMS, Waybar actions, window pinning, session restore, screenshots and theme refresh use Lua-compatible compositor calls. Game mode reads the new boolean option representation. Session save/restore succeeds when notifications are disabled.

The active startup chain remains the original `hyprland.conf` and its includes. Unsourced historical files under `conf/` are retained as history.
