# Return to the desktop from before Dux

Run from a terminal **inside the graphical session**:

```sh
~/.local/share/bin/restore-pre-dux --apply
```

The command checks the SHA-256 of the original pre-trial archive at `~/.local/state/hyprland-recovery/pre-dux-20261105-121547/desktop-config.tar`. It also verifies the pre-migration `themes-before.tar` checksum and restores these pre-existing theme files: GTK3 `settings.ini`; Qt5 and Qt6 `qt5ct.conf`/`qt6ct.conf` and `colors.conf`; and Kitty `kitty.conf`, `theme.conf`, and `userprefs.conf`. It saves current versions and user-service states in a new `~/.local/state/hyprland-recovery/before-restore-pre-dux-.../` directory before changing anything. It stops and disables only the Dux units, in this order: `dux-custom-poll.service`, `dms.service`, then `dux-trial.service`; restores the listed Hyprland sources, generated Lua, bindings and affected scripts from the original archive; and enables Waybar. It saves the DMS service override directory and relevant enablement links in the before-image. In an active graphical session it starts the existing polkit agent launcher only when no known agent is running, starts the original wallpaper launcher if neither supported wallpaper daemon is running, starts missing text and image clipboard watchers, restarts Waybar, and restarts, reloads, or starts swaync where appropriate. Wallpaper launch failures are reported. Without an active session, the authentication agent starts at the next login. Hyprland is reloaded when accessible; otherwise log out and back in. Existing changes to restored files are retained in the new backup, not merged.

The rollback leaves Dux packages, settings, state, newly generated theme assets, GTK4 symlinks, other services and unrelated files in place. It does not restore external theme directories or runtime application theme state; a new login or application restart may be needed. It does not run automatically. The Lua restored is the exact pre-Dux generated file; later changes to source files require regeneration using `python ~/.config/hypr/recovery/rebuild.py`.

## Recover the state immediately before rollback

The command prints the new backup directory. If it stops partway, the same backup is still available. To inspect it, replace `BACKUP` below with that printed directory:

```sh
cd BACKUP
sha256sum -c before.sha256
tar -tvf before.tar
cat before.json
```

The archive contains only paths present before rollback. `before.json` also lists paths that were absent and records each relevant unit's previous active/enabled state. To restore selected files, inspect the archive first, then use `tar -xvf before.tar -C "$HOME" -- path/from/list`. Restore the previous unit enablement and running state manually with `systemctl --user` if desired. Do not extract the whole archive without inspecting it: it may overwrite subsequent changes or recreate links.
