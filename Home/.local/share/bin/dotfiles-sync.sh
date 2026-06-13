#!/usr/bin/env bash

set -u
set -o pipefail

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/hyde"
CONFIG_FILE="${CONFIG_DIR}/dotfiles-sync.json"
LOG_DIR="${CACHE_DIR}/dotfiles-sync"
LOCK_FILE="/tmp/hyde-dotfiles-sync-$(id -u).lock"

mkdir -p "${CONFIG_DIR}" "${LOG_DIR}"

CONFIG_SCOPES=(
    hypr waybar rofi swaync wlogout swaylock
    kitty ghostty fastfetch btop fontconfig
    environment.d autostart zsh
)

HOME_FILES=(.zshrc .zprofile .zshenv .p10k.zsh .profile .bashrc .gitconfig)
HOME_DIRS=(.zsh .oh-my-zsh .fonts)
ASSET_DIRS=(.themes .icons)
GIT_PATH_EXCLUDES=(
    ':(exclude)Home/.config/waybar/debug_*.py'
    ':(exclude)Home/.config/waybar/*_test.py'
    ':(exclude)Home/.config/waybar/test_*.py'
    ':(exclude)Home/.config/waybar/.pytest_cache'
)

EXCLUDES=(
    --exclude .git
    --exclude node_modules
    --exclude __pycache__
    --exclude .cache
    --exclude dist
    --exclude '*.log'
    --exclude '*.tmp'
    --exclude '*.bak'
    --exclude '*.pyc'
    --exclude 'debug_*.py'
    --exclude '*_test.py'
    --exclude 'test_*.py'
    --exclude '.pytest_cache'
)

notify_user() {
    command -v notify-send >/dev/null 2>&1 && notify-send -a "Dotfiles Sync" "${1}" "${2:-}" >/dev/null 2>&1
}

write_default_config() {
    cat > "${CONFIG_FILE}" <<'JSON'
{
  "version": 1,
  "repo_path": "/media/ahmed/DEV/dotfiles/Linux-Setup",
  "branch": "codex/hyprland-wallpaper-importer",
  "include_assets": false,
  "confirm_push": true
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
        notify_user "Sync settings were reset" "The previous config was invalid JSON."
    fi
}

config_value() {
    ensure_config
    jq -r "${1}" "${CONFIG_FILE}"
}

repo_path() {
    config_value '.repo_path'
}

expected_branch() {
    config_value '.branch'
}

include_assets() {
    config_value '.include_assets == true'
}

new_log_file() {
    printf '%s/dotfiles-sync-%s.log\n' "${LOG_DIR}" "$(date +%Y%m%d-%H%M%S)"
}

log_line() {
    local log_file="${1}"
    shift
    printf '%s\n' "$*" | tee -a "${log_file}"
}

repo_check() {
    local repo
    repo="$(repo_path)"

    if [ ! -d "${repo}/.git" ]; then
        echo "Dotfiles repo not found: ${repo}"
        return 1
    fi

    local branch expected
    branch="$(git -C "${repo}" branch --show-current)"
    expected="$(expected_branch)"

    if [ "${branch}" != "${expected}" ]; then
        echo "Refusing to sync on branch '${branch}'. Expected '${expected}'."
        return 1
    fi
}

rsync_dir() {
    local mode="${1}" src="${2}" dst="${3}" log_file="${4}"
    [ -d "${src}" ] || return 0
    mkdir -p "${dst}"

    log_line "${log_file}" "DIR  ${src} -> ${dst}"
    if [ "${mode}" = "dry-run" ]; then
        rsync -a --delete --dry-run --itemize-changes "${EXCLUDES[@]}" "${src}/" "${dst}/" >> "${log_file}" 2>&1
    else
        rsync -a --delete "${EXCLUDES[@]}" "${src}/" "${dst}/" >> "${log_file}" 2>&1
    fi
}

rsync_file() {
    local mode="${1}" src="${2}" dst="${3}" log_file="${4}"
    [ -f "${src}" ] || return 0
    mkdir -p "$(dirname "${dst}")"

    log_line "${log_file}" "FILE ${src} -> ${dst}"
    if [ "${mode}" = "dry-run" ]; then
        rsync -a --dry-run --itemize-changes "${src}" "${dst}" >> "${log_file}" 2>&1
    else
        rsync -a "${src}" "${dst}" >> "${log_file}" 2>&1
    fi
}

sync_files() {
    ensure_config
    local mode="${1:-dry-run}" repo log_file
    repo="$(repo_path)"
    log_file="$(new_log_file)"

    repo_check | tee -a "${log_file}" || return 1

    log_line "${log_file}" "Mode: ${mode}"
    log_line "${log_file}" "Repo: ${repo}"
    log_line "${log_file}" "Branch: $(git -C "${repo}" branch --show-current)"
    log_line "${log_file}" ""

    for scope in "${CONFIG_SCOPES[@]}"; do
        rsync_dir "${mode}" "${HOME}/.config/${scope}" "${repo}/Home/.config/${scope}" "${log_file}"
    done

    rsync_dir "${mode}" "${HOME}/.local/share/bin" "${repo}/Home/.local/share/bin" "${log_file}"

    for file in "${HOME_FILES[@]}"; do
        rsync_file "${mode}" "${HOME}/${file}" "${repo}/Home/${file}" "${log_file}"
    done

    for dir in "${HOME_DIRS[@]}"; do
        rsync_dir "${mode}" "${HOME}/${dir}" "${repo}/Home/${dir}" "${log_file}"
    done

    if [ "$(include_assets)" = "true" ]; then
        for dir in "${ASSET_DIRS[@]}"; do
            rsync_dir "${mode}" "${HOME}/${dir}" "${repo}/Home/${dir}" "${log_file}"
        done
    else
        log_line "${log_file}" ""
        log_line "${log_file}" "Skipped .themes and .icons. Enable assets in settings to include them."
    fi

    log_line "${log_file}" ""
    log_line "${log_file}" "Log: ${log_file}"
    echo "${log_file}"
}

stage_managed_paths() {
    local repo="${1}"
    local paths=()
    local existing=()

    for scope in "${CONFIG_SCOPES[@]}"; do
        paths+=("Home/.config/${scope}")
    done
    paths+=("Home/.local/share/bin")

    for file in "${HOME_FILES[@]}"; do
        paths+=("Home/${file}")
    done
    for dir in "${HOME_DIRS[@]}"; do
        paths+=("Home/${dir}")
    done
    if [ "$(include_assets)" = "true" ]; then
        for dir in "${ASSET_DIRS[@]}"; do
            paths+=("Home/${dir}")
        done
    fi

    for path in "${paths[@]}"; do
        if [ -e "${repo}/${path}" ] || git -C "${repo}" ls-files --error-unmatch -- "${path}" >/dev/null 2>&1; then
            existing+=("${path}")
        fi
    done

    git -C "${repo}" add -A -- "${existing[@]}" "${GIT_PATH_EXCLUDES[@]}"
}

managed_paths() {
    local paths=()

    for scope in "${CONFIG_SCOPES[@]}"; do
        paths+=("Home/.config/${scope}")
    done
    paths+=("Home/.local/share/bin")

    for file in "${HOME_FILES[@]}"; do
        paths+=("Home/${file}")
    done
    for dir in "${HOME_DIRS[@]}"; do
        paths+=("Home/${dir}")
    done
    if [ "$(include_assets)" = "true" ]; then
        for dir in "${ASSET_DIRS[@]}"; do
            paths+=("Home/${dir}")
        done
    fi

    printf '%s\0' "${paths[@]}"
}

large_file_check() {
    local repo="${1}"
    local large
    large="$(find "${repo}/Home" -type f -size +90M -print -quit 2>/dev/null)"
    if [ -n "${large}" ]; then
        echo "Refusing commit: file larger than 90M found: ${large}"
        return 1
    fi
}

commit_changes() {
    ensure_config
    local message="${1:-sync: update desktop dotfiles}"
    local repo
    repo="$(repo_path)"

    repo_check || return 1
    large_file_check "${repo}" || return 1

    if ! git -C "${repo}" diff --cached --quiet; then
        echo "Refusing commit: staged changes already exist. Clear them first."
        return 1
    fi

    stage_managed_paths "${repo}"

    if git -C "${repo}" diff --cached --quiet; then
        echo "No managed dotfiles changes to commit."
        return 0
    fi

    git -C "${repo}" commit -m "${message}"
}

push_changes() {
    ensure_config
    local yes="${1:-false}" repo
    repo="$(repo_path)"
    repo_check || return 1

    if [ "${yes}" != "true" ] && [ "$(config_value '.confirm_push != false')" = "true" ]; then
        printf 'Push branch %s to origin? [y/N] ' "$(git -C "${repo}" branch --show-current)"
        read -r answer
        case "${answer}" in
            y|Y|yes|YES) ;;
            *) echo "Push cancelled."; return 1 ;;
        esac
    fi

    git -C "${repo}" push
}

status_text() {
    ensure_config
    local repo
    local -a managed
    repo="$(repo_path)"
    echo "Repo: ${repo}"
    if [ -d "${repo}/.git" ]; then
        echo "Branch: $(git -C "${repo}" branch --show-current)"
        echo "Expected: $(expected_branch)"
        echo
        mapfile -d '' -t managed < <(managed_paths)
        echo "Managed tracked changes:"
        git -C "${repo}" diff --name-status --ignore-submodules=all -- "${managed[@]}" "${GIT_PATH_EXCLUDES[@]}" || true
        echo
        echo "Managed untracked files:"
        git -C "${repo}" ls-files --others --exclude-standard -- "${managed[@]}" "${GIT_PATH_EXCLUDES[@]}" || true
    else
        echo "Missing repo."
    fi
}

waybar_status() {
    ensure_config
    local repo branch last_log tooltip
    repo="$(repo_path)"
    branch="missing"
    [ -d "${repo}/.git" ] && branch="$(git -C "${repo}" branch --show-current)"
    last_log="$(ls -t "${LOG_DIR}"/dotfiles-sync-*.log 2>/dev/null | head -1)"
    tooltip="Repo: ${repo}\nBranch: ${branch}\nLeft click: open sync GUI\nRight click: preview sync"
    [ -n "${last_log}" ] && tooltip="${tooltip}\nLast log: ${last_log}"
    jq -n --arg text "Sync" --arg tooltip "${tooltip}" '{text:$text, tooltip:$tooltip, class:"dotfiles-sync"}'
}

waybar_busy() {
    local tooltip="Dotfiles sync is already running.\nLeft click: open sync GUI"
    jq -n --arg text "Sync*" --arg tooltip "${tooltip}" '{text:$text, tooltip:$tooltip, class:"dotfiles-sync-busy"}'
}

show_log_gui() {
    local log_file="${1}"
    yad --text-info --title="Dotfiles Sync Log" --width=900 --height=620 --filename="${log_file}" --button="Close:0" >/dev/null 2>&1 || true
}

settings_gui() {
    ensure_config
    while true; do
        local repo branch assets confirm result code
        repo="$(repo_path)"
        branch="$(expected_branch)"
        assets="$(include_assets)"
        confirm="$(config_value '.confirm_push != false')"

        result="$(yad --form --title="Dotfiles Sync Settings" --width=720 \
            --field="Dotfiles repo" "${repo}" \
            --field="Allowed branch" "${branch}" \
            --field="Include .themes and .icons:CHK" "${assets}" \
            --field="Confirm before push:CHK" "${confirm}" \
            --button="Open Repo:20" --button="Cancel:1" --button="Save:0")"
        code=$?

        case "${code}" in
            0)
                local new_repo new_branch new_assets new_confirm tmp_file
                IFS='|' read -r new_repo new_branch new_assets new_confirm _ <<< "${result}"
                tmp_file="$(mktemp)"
                jq \
                    --arg repo "${new_repo}" \
                    --arg branch "${new_branch}" \
                    --argjson assets "$(printf '%s' "${new_assets}" | tr '[:upper:]' '[:lower:]')" \
                    --argjson confirm "$(printf '%s' "${new_confirm}" | tr '[:upper:]' '[:lower:]')" \
                    '.repo_path = $repo | .branch = $branch | .include_assets = $assets | .confirm_push = $confirm' \
                    "${CONFIG_FILE}" > "${tmp_file}" && mv "${tmp_file}" "${CONFIG_FILE}"
                notify_user "Sync settings saved" "Dotfiles sync settings updated."
                return
                ;;
            20)
                xdg-open "${repo}" >/dev/null 2>&1 || notify_user "Open repo failed" "${repo}"
                ;;
            *)
                return
                ;;
        esac
    done
}

prompt_commit_message() {
    yad --entry --title="Commit Message" --text="Commit message:" --entry-text="sync: update desktop dotfiles" --button="Cancel:1" --button="Commit:0"
}

confirm_gui() {
    local title="${1}" text="${2}" ok="${3:-Continue}"
    yad --question --title="${title}" --text="${text}" --button="Cancel:1" --button="${ok}:0" >/dev/null 2>&1
}

sync_gui() {
    ensure_config
    while true; do
        yad --list --title="Safe Dotfiles Sync" --width=780 --height=470 \
            --column="Action" --column="What it does" \
            "Status" "Show repo branch and dirty state" \
            "Preview sync" "Dry-run copy and show exactly what would change" \
            "Apply sync" "Copy managed dotfiles into the repo after confirmation" \
            "Commit" "Stage managed paths only and commit" \
            "Push" "Push current branch after confirmation" \
            "Full safe flow" "Preview, apply, commit, then ask before push" \
            "Settings" "Repo path, branch guard, assets, push confirmation" \
            --button="Status:10" --button="Preview:20" --button="Apply:30" --button="Commit:40" --button="Push:50" --button="Full Flow:60" --button="Settings:70" --button="Close:0" >/dev/null 2>&1

        case $? in
            10)
                local tmp
                tmp="$(mktemp)"
                status_text > "${tmp}" 2>&1
                show_log_gui "${tmp}"
                rm -f "${tmp}"
                ;;
            20)
                local log_file
                log_file="$(sync_files dry-run | tail -1)"
                show_log_gui "${log_file}"
                ;;
            30)
                confirm_gui "Apply Sync" "Copy managed dotfiles into the repo now?" "Apply" || continue
                local log_file
                log_file="$(sync_files apply | tail -1)"
                show_log_gui "${log_file}"
                ;;
            40)
                local message tmp
                message="$(prompt_commit_message)" || continue
                tmp="$(mktemp)"
                commit_changes "${message}" > "${tmp}" 2>&1
                show_log_gui "${tmp}"
                rm -f "${tmp}"
                ;;
            50)
                confirm_gui "Push Dotfiles" "Push the current dotfiles branch to origin?" "Push" || continue
                local tmp
                tmp="$(mktemp)"
                push_changes true > "${tmp}" 2>&1
                show_log_gui "${tmp}"
                rm -f "${tmp}"
                ;;
            60)
                local log_file message tmp
                log_file="$(sync_files dry-run | tail -1)"
                show_log_gui "${log_file}"
                confirm_gui "Apply Sync" "Apply the dry-run changes now?" "Apply" || continue
                log_file="$(sync_files apply | tail -1)"
                show_log_gui "${log_file}"
                message="$(prompt_commit_message)" || continue
                tmp="$(mktemp)"
                commit_changes "${message}" > "${tmp}" 2>&1
                show_log_gui "${tmp}"
                rm -f "${tmp}"
                confirm_gui "Push Dotfiles" "Push the committed branch to origin?" "Push" || continue
                tmp="$(mktemp)"
                push_changes true > "${tmp}" 2>&1
                show_log_gui "${tmp}"
                rm -f "${tmp}"
                ;;
            70) settings_gui ;;
            *) break ;;
        esac
    done
}

usage() {
    cat <<EOF
Usage: dotfiles-sync.sh <command>

Commands:
  status                  Show repo status
  waybar                  Print Waybar JSON status
  sync --dry-run          Preview managed dotfiles copy
  sync --apply            Copy managed dotfiles into repo
  commit "message"        Stage managed paths and commit
  push [--yes]            Push branch, with confirmation unless --yes
  gui|menu                Open beginner-friendly GUI
  settings                Open settings GUI
EOF
}

main() {
    local command="${1:-gui}"
    shift || true

    exec 9>"${LOCK_FILE}"
    flock -n 9 || {
        if [ "${command}" = "waybar" ]; then
            waybar_busy
            exit 0
        fi
        echo "Another dotfiles sync action is already running."
        exit 1
    }

    case "${command}" in
        status) status_text ;;
        waybar) waybar_status ;;
        sync)
            case "${1:-}" in
                --apply|apply) sync_files apply ;;
                --dry-run|dry-run|"") sync_files dry-run ;;
                *) usage; exit 1 ;;
            esac
            ;;
        commit)
            commit_changes "${1:-sync: update desktop dotfiles}"
            ;;
        push)
            if [ "${1:-}" = "--yes" ]; then
                push_changes true
            else
                push_changes false
            fi
            ;;
        gui|menu) sync_gui ;;
        settings) settings_gui ;;
        help|-h|--help) usage ;;
        *) usage; exit 1 ;;
    esac
}

main "$@"
