alias neofetch='fastfetch'
alias vscode-fork='/home/ahmed/.local/bin/vscode-fork'

# source antidote
source /home/ahmed/.antidote/antidote.zsh

# Define missing ZLE widgets
zle -N insert-unambiguous-or-complete
zle -N menu-search
zle -N recent-paths

# initialize plugins statically with ${ZDOTDIR:-~}/.zsh_plugins.txt
antidote load
export BROWSER=/usr/bin/brave
export OLLAMA_MODELS="/media/ahmed/DEV/ollama/models"

IDEA_DIR=$(ls -d /opt/idea-IU-* 2>/dev/null | head -n 1)
if [ -n "$IDEA_DIR" ]; then
  export PATH="$IDEA_DIR/bin:$PATH"
fi

export JAVA_HOME="$HOME/.jdks/openjdk-23.0.2"
export PATH="$JAVA_HOME/bin:$PATH"

. "/home/ahmed/.deno/env"

export PATH="/media/ahmed/DEV/SDKs/npm-global/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"
export WINEPREFIX="/media/ahmed/DEV/SDKs/wine_prefix"

export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - zsh)"
eval "$(pyenv virtualenv-init -)"

# Auto-setup display environment for GUI applications (Hyprland/Wayland)
if [[ -z "$XDG_RUNTIME_DIR" ]]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi

if [[ -z "$DISPLAY" ]] && [[ -z "$WAYLAND_DISPLAY" ]]; then
    # Set up Wayland display
    if [[ -S "$XDG_RUNTIME_DIR/wayland-1" ]]; then
        export WAYLAND_DISPLAY="wayland-1"
    elif [[ -S "$XDG_RUNTIME_DIR/wayland-0" ]]; then
        export WAYLAND_DISPLAY="wayland-0"
    fi
    
    # Set up X11 display for XWayland compatibility
    export DISPLAY=":0"
    
    # Set session type
    export XDG_SESSION_TYPE="wayland"
    export XDG_CURRENT_DESKTOP="Hyprland"
fi

export ANTHROPIC_API_KEY="sk-antigravity"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8045"

#export ANTHROPIC_BASE_URL="http://localhost:8080"
export ANTHROPIC_AUTH_TOKEN="test"
export CODEX_CLI_PATH=$(which codex)
export PATH="$HOME/.local/bin:$PATH"
