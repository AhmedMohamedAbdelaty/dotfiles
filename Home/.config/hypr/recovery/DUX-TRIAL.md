# Dux Shell trial

- Super+Alt+F12 starts the trial; Super+Shift+Alt+F12 stops it and restores Waybar if it was running before the trial.
- The trial is not enabled at login. A reboot returns to the existing desktop.
- The original shortcuts, HyMission and swaync remain active. Swaync keeps the notification service, so the Dux notification panel is not the active notification center during this trial.
- Dux and Quickshell are extracted from signed Arch packages into `~/.local/opt/dux-trial`, not installed by pacman, and will not update automatically. Dynamic application-theme changes and Dux's polkit agent are disabled for the trial.
- The existing screen locker remains available with Super+L; Dux's loginctl lock integration is disabled while evaluating the shell.
- The existing configuration snapshot is at `~/.local/state/hyprland-recovery/pre-dux-20261105-121547/desktop-config.tar`. Review its contents before restoring it, since extracting it over your home directory can overwrite changes made since the snapshot.
- Dux may create `~/.config/dms`, `~/.local/state/dms`, and generated fragments in `~/.config/hypr/dms`. The restored Hyprland configuration does not source these fragments.
