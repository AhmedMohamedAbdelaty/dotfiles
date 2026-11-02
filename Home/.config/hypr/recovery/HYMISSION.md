# HyMission

- Super+Y toggles the window overview; Super+Shift+Y shows all workspaces.
- Search starts on demand with `/`, keeping the overview responsive. The h/j/k/l keys also navigate previews.
- The restored Hyprland Lua generator loads `~/.local/lib/hymission.so` and preserves the shortcuts in the Super+/ menu.
- The build is pinned to HyMission `a022307005087f3f5ab2efd1ffba558304c08273` and official Hyprland `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426` (0.57.0).
- To reconstruct the local plugin and its search helper on a matching installation, run `~/.local/share/bin/hymission-rebuild.sh`. It needs Git, CMake, Ninja, a C++ compiler, pkg-config, and the Hyprland, Lua, GLib, GTK4, gtk4-layer-shell, and libadwaita development files.
- Plugins depend on Hyprland's exact ABI. After a Hyprland update, verify upstream compatibility and rebuild for the new version; this pinned recipe deliberately refuses a different version. The plugin also checks compatibility when it loads.
- The rebuild script does not reload an active plugin. A new session uses the newly built file.
