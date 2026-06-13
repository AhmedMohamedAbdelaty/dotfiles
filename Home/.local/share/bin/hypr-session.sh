#!/usr/bin/env bash

set -u

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/hyde"
CONFIG_FILE="${CONFIG_DIR}/session-restore.json"
STATE_FILE="${CACHE_DIR}/session-restore.json"
LOCK_FILE="/tmp/hyde-session-restore-$(id -u).lock"

mkdir -p "${CONFIG_DIR}" "${CACHE_DIR}"

notify_user() {
    local title="${1}"
    local message="${2:-}"
    command -v notify-send >/dev/null 2>&1 && notify-send -a "Session Restore" "${title}" "${message}" >/dev/null 2>&1
}

write_default_config() {
    cat > "${CONFIG_FILE}" <<'JSON'
{
  "version": 1,
  "restore_on_startup": true,
  "startup_delay": 3,
  "notify": true,
  "apps": [
    { "name": "Brave", "class": "brave-browser", "command": "brave", "enabled": true },
    { "name": "VS Code", "class": "code", "command": "code", "enabled": true },
    { "name": "Telegram", "class": "org.telegram.desktop", "command": "Telegram -autostart", "enabled": true },
    { "name": "Legcord", "class": "legcord", "command": "legcord", "enabled": true },
    { "name": "Vesktop", "class": "dev.vencord.Vesktop", "command": "flatpak run dev.vencord.Vesktop", "enabled": true },
    { "name": "Kitty", "class": "kitty", "command": "kitty", "enabled": true },
    { "name": "Dolphin", "class": "org.kde.dolphin", "command": "dolphin", "enabled": true },
    { "name": "Obsidian", "class": "obsidian", "command": "obsidian", "enabled": true },
    { "name": "Spotify", "class": "spotify", "command": "spotify", "enabled": false },
    { "name": "Steam", "class": "Steam", "command": "steam", "enabled": false },
    { "name": "CopyQ", "class": "com.github.hluk.copyq", "command": "copyq", "enabled": false }
  ]
}
JSON
}

ensure_config() {
    if [ ! -f "${CONFIG_FILE}" ]; then
        write_default_config
        return
    fi

    if ! jq empty "${CONFIG_FILE}" >/dev/null 2>&1; then
        mv "${CONFIG_FILE}" "${CONFIG_FILE}.broken.$(date +%Y%m%d-%H%M%S)"
        write_default_config
        notify_user "Session settings were reset" "The previous config was invalid JSON."
    fi
}

notifications_enabled() {
    ensure_config
    jq -e '.notify != false' "${CONFIG_FILE}" >/dev/null 2>&1
}

save_session() {
    ensure_config
    local clients_file tmp_file
    clients_file="$(mktemp)"
    tmp_file="$(mktemp)"

    if ! hyprctl clients -j > "${clients_file}" 2>/dev/null; then
        rm -f "${clients_file}" "${tmp_file}"
        echo "Hyprland is not available."
        notify_user "Session save failed" "Hyprland is not available."
        return 1
    fi

    jq -n \
        --slurpfile clients "${clients_file}" \
        --slurpfile cfg "${CONFIG_FILE}" '
        {
          version: 1,
          saved_at: (now | todateiso8601),
          apps: [
            $cfg[0].apps[]
            | select(.enabled != false) as $app
            | ($clients[0]
              | map(select((.class == $app.class) or (.initialClass == $app.class)))
              | sort_by(.focusHistoryID)
              | .[0]) as $client
            | select($client != null)
            | {
                name: $app.name,
                class: $app.class,
                command: $app.command,
                workspace: ($client.workspace.id // 1),
                workspace_name: ($client.workspace.name // ""),
                monitor: ($client.monitor // null),
                floating: ($client.floating // false),
                fullscreen: ($client.fullscreen // 0),
                size: ($client.size // []),
                at: ($client.at // [])
              }
          ]
        }' > "${tmp_file}"

    mv "${tmp_file}" "${STATE_FILE}"
    rm -f "${clients_file}"

    local count
    count="$(jq '.apps | length' "${STATE_FILE}")"
    echo "Saved ${count} app(s) to ${STATE_FILE}"
    notifications_enabled && notify_user "Session saved" "${count} app(s) saved."
}

class_running() {
    local class="${1}"
    hyprctl clients -j 2>/dev/null | jq -e --arg class "${class}" 'any(.[]; (.class == $class) or (.initialClass == $class))' >/dev/null 2>&1
}

command_available() {
    local command_line="${1}"
    local first_word
    first_word="$(awk '{print $1}' <<< "${command_line}")"
    if [ "${first_word}" = "flatpak" ]; then
        command -v flatpak >/dev/null 2>&1
    else
        command -v "${first_word}" >/dev/null 2>&1
    fi
}

restore_session() {
    ensure_config
    local dry_run=false startup=false startup_delay=""

    while [ $# -gt 0 ]; do
        case "${1}" in
            --dry-run|dry-run) dry_run=true ;;
            --startup) startup=true ;;
            --startup-delay)
                shift
                startup_delay="${1:-}"
                ;;
        esac
        shift || true
    done

    if [ "${startup}" = true ]; then
        jq -e '.restore_on_startup != false' "${CONFIG_FILE}" >/dev/null 2>&1 || exit 0
        if [ -z "${startup_delay}" ]; then
            startup_delay="$(jq -r '.startup_delay // 3' "${CONFIG_FILE}")"
        fi
        sleep "${startup_delay}"
    fi

    if [ ! -f "${STATE_FILE}" ]; then
        echo "No saved session found. Run: hypr-session.sh save"
        [ "${startup}" = false ] && notify_user "No saved session" "Save a session first."
        return 1
    fi

    if ! jq empty "${STATE_FILE}" >/dev/null 2>&1; then
        echo "Saved session is invalid JSON: ${STATE_FILE}"
        notify_user "Session restore failed" "Saved session is invalid JSON."
        return 1
    fi

    local launched=0 skipped=0 missing=0
    while IFS=$'\t' read -r name class command workspace floating width height x y; do
        [ -z "${class}" ] && continue

        if class_running "${class}"; then
            echo "Skip ${name}: already running"
            skipped=$((skipped + 1))
            continue
        fi

        if ! command_available "${command}"; then
            echo "Skip ${name}: command not found (${command})"
            missing=$((missing + 1))
            continue
        fi

        if [ "${dry_run}" = true ]; then
            echo "Would launch ${name} on workspace ${workspace}: ${command}"
            continue
        fi

        hyprctl dispatch exec "[workspace ${workspace} silent] ${command}" >/dev/null 2>&1 || true
        launched=$((launched + 1))

        if [ "${floating}" = "true" ] && [ -n "${width}" ] && [ -n "${height}" ] && [ -n "${x}" ] && [ -n "${y}" ]; then
            (
                sleep 2
                hyprctl dispatch focuswindow "class:${class}" >/dev/null 2>&1 || exit 0
                hyprctl dispatch togglefloating active >/dev/null 2>&1 || true
                hyprctl dispatch resizeactive "exact ${width} ${height}" >/dev/null 2>&1 || true
                hyprctl dispatch moveactive "exact ${x} ${y}" >/dev/null 2>&1 || true
            ) &
        fi
    done < <(jq -r '.apps[] | [.name, .class, .command, (.workspace|tostring), (.floating|tostring), (.size[0] // ""), (.size[1] // ""), (.at[0] // ""), (.at[1] // "")] | @tsv' "${STATE_FILE}")

    if [ "${dry_run}" = true ]; then
        return 0
    fi

    echo "Launched ${launched}, skipped ${skipped}, missing ${missing}"
    notifications_enabled && notify_user "Session restored" "Launched ${launched}, skipped ${skipped}, missing ${missing}."
}

status_text() {
    ensure_config
    if [ ! -f "${STATE_FILE}" ] || ! jq empty "${STATE_FILE}" >/dev/null 2>&1; then
        echo "No saved session."
        return
    fi

    jq -r '"Saved: \(.saved_at // "unknown")\nApps: \(.apps | length)\n\n" + (.apps | map("- \(.name) -> workspace \(.workspace)") | join("\n"))' "${STATE_FILE}"
}

waybar_status() {
    ensure_config
    if [ ! -f "${STATE_FILE}" ] || ! jq empty "${STATE_FILE}" >/dev/null 2>&1; then
        jq -n '{text:"󰒲 Session", tooltip:"No saved session. Left click to open session restore.", class:"session-empty"}'
        return
    fi

    jq -n --slurpfile state "${STATE_FILE}" '{
      text: ("󰒲 " + (($state[0].apps | length) | tostring)),
      tooltip: ("Saved: " + ($state[0].saved_at // "unknown") + "\n" + ($state[0].apps | map(.name + " -> workspace " + (.workspace|tostring)) | join("\n"))),
      class: "session-saved"
    }'
}

show_status_gui() {
    status_text | yad --text-info --title="Session Restore Status" --width=640 --height=420 --button="Close:0" >/dev/null 2>&1 || true
}

settings_gui() {
    ensure_config
    while true; do
        local startup delay notify result code
        startup="$(jq -r '.restore_on_startup != false' "${CONFIG_FILE}")"
        delay="$(jq -r '.startup_delay // 3' "${CONFIG_FILE}")"
        notify="$(jq -r '.notify != false' "${CONFIG_FILE}")"

        result="$(yad --form --title="Session Restore Settings" --width=520 \
            --field="Restore saved session at login:CHK" "${startup}" \
            --field="Startup delay seconds:NUM" "${delay}!0..30!1" \
            --field="Show notifications:CHK" "${notify}" \
            --button="Open App List:20" --button="Cancel:1" --button="Save:0")"
        code=$?

        case "${code}" in
            0)
                local restore_value delay_value notify_value tmp_file
                IFS='|' read -r restore_value delay_value notify_value _ <<< "${result}"
                tmp_file="$(mktemp)"
                jq \
                    --argjson restore "$(printf '%s' "${restore_value}" | tr '[:upper:]' '[:lower:]')" \
                    --argjson notify "$(printf '%s' "${notify_value}" | tr '[:upper:]' '[:lower:]')" \
                    --arg delay "${delay_value%%.*}" \
                    '.restore_on_startup = $restore | .notify = $notify | .startup_delay = ($delay | tonumber)' \
                    "${CONFIG_FILE}" > "${tmp_file}" && mv "${tmp_file}" "${CONFIG_FILE}"
                notify_user "Session settings saved" "Restore settings updated."
                return
                ;;
            20)
                xdg-open "${CONFIG_FILE}" >/dev/null 2>&1 || notify_user "Open config failed" "${CONFIG_FILE}"
                ;;
            *)
                return
                ;;
        esac
    done
}

clear_session() {
    rm -f "${STATE_FILE}"
    echo "Saved session cleared."
    notifications_enabled && notify_user "Session cleared" "Saved session removed."
}

clear_session_gui() {
    yad --question --title="Clear Saved Session" --text="Remove the saved session restore state?" --button="Cancel:1" --button="Clear:0" >/dev/null 2>&1
    [ $? -eq 0 ] && clear_session >/dev/null
}

session_gui() {
    ensure_config
    while true; do
        yad --list --title="Session Restore" --width=720 --height=440 \
            --column="Action" --column="What it does" \
            "Save current session" "Remember curated running apps and workspaces" \
            "Restore saved session" "Open missing apps from the saved session" \
            "Preview restore" "Show what would launch without opening apps" \
            "Status" "Show saved apps and target workspaces" \
            "Settings" "Startup restore, delay, notifications, app list" \
            "Clear saved session" "Remove saved session state" \
            --button="Save:10" --button="Restore:20" --button="Preview:30" --button="Status:40" --button="Settings:50" --button="Clear:60" --button="Close:0" >/dev/null 2>&1
        case $? in
            10) save_session | yad --text-info --title="Session Saved" --width=520 --height=220 --button="Close:0" >/dev/null 2>&1 || true ;;
            20) restore_session | yad --text-info --title="Session Restore" --width=640 --height=300 --button="Close:0" >/dev/null 2>&1 || true ;;
            30) restore_session --dry-run | yad --text-info --title="Session Restore Preview" --width=720 --height=360 --button="Close:0" >/dev/null 2>&1 || true ;;
            40) show_status_gui ;;
            50) settings_gui ;;
            60) clear_session_gui ;;
            *) break ;;
        esac
    done
}

usage() {
    cat <<EOF
Usage: hypr-session.sh <command>

Commands:
  save              Save curated running apps and workspaces
  restore           Restore missing apps from the saved session
  restore --dry-run Preview restore actions without launching apps
  restore --startup Restore at login when enabled in settings
  status            Print saved session summary
  waybar            Print Waybar JSON status
  gui|menu          Open beginner-friendly GUI
  settings          Open settings GUI
  clear             Remove saved session state
EOF
}

main() {
    local command="${1:-gui}"
    shift || true

    exec 9>"${LOCK_FILE}"
    flock -n 9 || {
        echo "Another session restore action is already running."
        exit 1
    }

    case "${command}" in
        save) save_session "$@" ;;
        restore) restore_session "$@" ;;
        dry-run) restore_session --dry-run "$@" ;;
        status) status_text ;;
        waybar) waybar_status ;;
        gui|menu) session_gui ;;
        settings) settings_gui ;;
        clear) clear_session ;;
        help|-h|--help) usage ;;
        *) usage; exit 1 ;;
    esac
}

main "$@"
