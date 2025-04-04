#!/bin/bash

# Get the list of players
players=$(playerctl -l)

# Check if any players are available
if [ -z "$players" ]; then
    notify-send -a "Media Controller" "No players found" "Please start a media player and try again." -i audio-headphones
    exit 1
fi

# Get currently active player (if any)
current_player=$(playerctl -l | head -n 1)
current_status="$(playerctl -p "$current_player" status 2>/dev/null || echo "Unknown")"

# Use rofi to select a player with better styling
selected_player=$(echo "$players" | rofi -dmenu -i -p "Select media player" \
    -theme-str 'window {width: 400px; border-radius: 10px;}' \
    -theme-str 'element-text {horizontal-align: 0.5;}' \
    -theme-str 'listview {lines: 6; dynamic: true;}')

# Check if a player was selected
if [ -n "$selected_player" ]; then
    # Switch to the selected player and toggle play/pause
    playerctl -p "$selected_player" play-pause
    new_status=$(playerctl -p "$selected_player" status)

    # Show notification with icon based on player
    icon="audio-headphones"
    case "$selected_player" in
        spotify*)
            icon="spotify"
            ;;
        firefox*)
            icon="firefox"
            ;;
        chrome*|chromium*)
            icon="chrome"
            ;;
        vlc*)
            icon="vlc"
            ;;
    esac

    notify-send -a "Media Controller" "Switched to $selected_player" "Player status: $new_status" -i "$icon"
else
    notify-send -a "Media Controller" "No player selected" "Operation cancelled" -i audio-headphones
fi
