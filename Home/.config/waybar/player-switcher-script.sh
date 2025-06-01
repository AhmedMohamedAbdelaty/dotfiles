#!/bin/bash
# filepath: /home/ahmed/.config/waybar/player-switcher-script.sh

# Get the list of players
players=$(playerctl -l)

# Check if any players are available
if [ -z "$players" ]; then
    notify-send -a "Media Controller" "No players found" "Please start a media player and try again." -i audio-headphones
    exit 1
fi

# Gather information about all players
declare -a menu_items=()
declare -A player_groups=()

DEFAULT_PLAYER_FILE="$HOME/.cache/waybar/default-player"
DEFAULT_PLAYER_ICON="󰓎 " # nf-md-music_box_outline or similar for default

# Read the default player if the file exists
DEFAULT_PLAYER=""
if [ -f "$DEFAULT_PLAYER_FILE" ]; then
    DEFAULT_PLAYER=$(cat "$DEFAULT_PLAYER_FILE")
fi

for player in $players; do
    status=$(playerctl -p "$player" status 2>/dev/null || echo "Unknown")
    title=$(playerctl -p "$player" metadata title 2>/dev/null || echo "Unknown")
    artist=$(playerctl -p "$player" metadata artist 2>/dev/null || echo "")
    url=$(playerctl -p "$player" metadata xesam:url 2>/dev/null || echo "")

    # Extract base player name and instance
    base_player=$(echo "$player" | cut -d'.' -f1)
    instance=$(echo "$player" | grep -o "instance[0-9]*" | sed 's/instance//')

    # If it's an instance, make a nicer display name
    display_name="$player"
    if [ -n "$instance" ]; then
        # For Firefox/Chromium, try to extract domain from URL for better identification
        domain=""
        if [[ "$url" =~ ^https?:// ]]; then
            domain=$(echo "$url" | sed -E 's|^https?://([^/]+).*|\1|' | sed 's/www\.//')
            display_name="${base_player} [${domain:-instance $instance}]"
        else
            display_name="${base_player} [instance $instance]"
        fi

        # Count instances per base player
        player_groups["$base_player"]=$((${player_groups["$base_player"]:-0} + 1))
    fi

    # Create status indicator
    indicator=""
    case "$status" in
        Playing) indicator="▶";;
        Paused)  indicator="⏸";;
        Stopped) indicator="⏹";;
        *)       indicator="•";;
    esac

    # Enhanced display for multi-instance
    if [ -n "$instance" ]; then
        # For Firefox/Chromium with domain info
        if [[ "$url" =~ ^https?:// ]]; then
            domain=$(echo "$url" | sed -E 's|^https?://([^/]+).*|\1|' | sed 's/www\.//')
            # Add color formatting for rofi
            display_name="<span color='#cba6f7'>${base_player}</span> ⊞ <span color='#fab387'>${domain:-instance $instance}</span>"
        else
            display_name="<span color='#cba6f7'>${base_player}</span> ⊞ <span color='#89b4fa'>instance $instance</span>"
        fi

        # Count instances per base player
        player_groups["$base_player"]=$((${player_groups["$base_player"]:-0} + 1))
    else
        display_name="<span color='#a6e3a1'>${player}</span>"
    fi

    # Format display text with improved styling
    if [ -n "$artist" ]; then
        display_text="$indicator $display_name: $artist - $title"
    else
        display_text="$indicator $display_name: $title"
    fi

    # Add default player indicator
    if [ "$player" = "$DEFAULT_PLAYER" ]; then
        display_text="$DEFAULT_PLAYER_ICON $display_text"
    fi

    # Sort players - playing first, then paused, then others
    sort_priority=0
    if [ "$status" = "Playing" ]; then
        sort_priority=1
    elif [ "$status" = "Paused" ]; then
        sort_priority=2
    fi

    menu_items+=("$sort_priority|$player|$display_text")
done

# Sort items by priority (playing first)
IFS=$'\n' sorted_items=($(sort -r <<<"${menu_items[*]}"))
unset IFS

# Prepare menu options
formatted_items=()

# Add headers for grouped players if they have multiple instances
for base_player in "${!player_groups[@]}"; do
    if [ "${player_groups[$base_player]}" -gt 1 ]; then
        formatted_items+=("<span color='#cba6f7'>⊞ ${base_player^} (${player_groups[$base_player]} instances)</span>")
    fi
done

# If we have any headers, add a separator
if [ ${#formatted_items[@]} -gt 0 ]; then
    formatted_items+=("──────────────────────────────")
fi

# Add all player entries
for item in "${sorted_items[@]}"; do
    display_text=$(echo "$item" | cut -d'|' -f3)
    formatted_items+=("$display_text")
done

# Add action options at the bottom
formatted_items+=("──────────────────────────────")
formatted_items+=("🔄 Refresh players list")
formatted_items+=("⏹️ Stop all players")
formatted_items+=("⏸️ Pause all players")
formatted_items+=("▶️ Play all paused players")

# Add shuffle and repeat toggles for the default player if one is set
if [ -n "$DEFAULT_PLAYER" ] && playerctl -p "$DEFAULT_PLAYER" status &>/dev/null; then # Check if default player is active
    shuffle_status=$(playerctl -p "$DEFAULT_PLAYER" shuffle 2>/dev/null)
    repeat_status=$(playerctl -p "$DEFAULT_PLAYER" loop 2>/dev/null)

    shuffle_indicator="🔀"
    repeat_indicator="🔁"

    if [ "$shuffle_status" = "On" ]; then
        shuffle_text="$shuffle_indicator Shuffle: On (Toggle Off)"
    else
        shuffle_text="$shuffle_indicator Shuffle: Off (Toggle On)"
    fi

    if [ "$repeat_status" = "Track" ] || [ "$repeat_status" = "Playlist" ]; then
        repeat_text="$repeat_indicator Repeat: $repeat_status (Toggle Off)"
    else # None or other status
        repeat_text="$repeat_indicator Repeat: Off (Toggle Track)"
    fi

    formatted_items+=("$shuffle_text")
    formatted_items+=("$repeat_text")
fi

# Use rofi to show enhanced player selection with more info
selection=$(printf '%s\n' "${formatted_items[@]}" | rofi -markup-rows -dmenu -i -p "Media Players" \
    -theme-str 'window {width: 700px; border-radius: 10px;}' \
    -theme-str 'element-text {horizontal-align: 0;}' \
    -theme-str 'listview {lines: 12; dynamic: true;}')

# Early exit if nothing was selected
[ -z "$selection" ] && exit 0

# Handle special commands
case "$selection" in
    "🔄 Refresh players list")
        exec "$0"
        exit 0
        ;;
    "⏹️ Stop all players")
        for player in $players; do
            playerctl -p "$player" stop
        done
        notify-send -a "Media Controller" "All players stopped" -i audio-headphones
        exit 0
        ;;
    "⏸️ Pause all players")
        for player in $players; do
            playerctl -p "$player" pause
        done
        notify-send -a "Media Controller" "All players paused" -i audio-headphones
        exit 0
        ;;
    "▶️ Play all paused players")
        for player in $players; do
            status=$(playerctl -p "$player" status 2>/dev/null || echo "Unknown")
            if [ "$status" = "Paused" ]; then
                playerctl -p "$player" play
            fi
        done
        notify-send -a "Media Controller" "Playing all paused players" -i audio-headphones
        exit 0
        ;;
    *"$shuffle_indicator Shuffle:"*)
        if [ -n "$DEFAULT_PLAYER" ]; then
            playerctl -p "$DEFAULT_PLAYER" shuffle Toggle
            current_shuffle_status=$(playerctl -p "$DEFAULT_PLAYER" shuffle)
            notify-send -a "Media Controller" "Shuffle Toggled" "$DEFAULT_PLAYER shuffle is now: $current_shuffle_status" -i view-media-shuffle
        else
            notify-send -a "Media Controller" "Error" "No default player set for shuffle." -i dialog-error
        fi
        exec "$0" # Refresh the menu
        exit 0
        ;;
    *"$repeat_indicator Repeat:"*)
        if [ -n "$DEFAULT_PLAYER" ]; then
            current_loop_status=$(playerctl -p "$DEFAULT_PLAYER" loop)
            if [ "$current_loop_status" = "None" ]; then
                playerctl -p "$DEFAULT_PLAYER" loop Track
                notify-send -a "Media Controller" "Repeat Toggled" "$DEFAULT_PLAYER repeat is now: Track" -i view-media-repeat
            elif [ "$current_loop_status" = "Track" ]; then
                playerctl -p "$DEFAULT_PLAYER" loop Playlist
                 notify-send -a "Media Controller" "Repeat Toggled" "$DEFAULT_PLAYER repeat is now: Playlist" -i view-media-repeat
            else # Playlist or other
                playerctl -p "$DEFAULT_PLAYER" loop None
                notify-send -a "Media Controller" "Repeat Toggled" "$DEFAULT_PLAYER repeat is now: Off" -i view-media-repeat
            fi
        else
            notify-send -a "Media Controller" "Error" "No default player set for repeat." -i dialog-error
        fi
        exec "$0" # Refresh the menu
        exit 0
        ;;
    *"📑"*) # Header row, ignore
        exec "$0"
        exit 0
        ;;
    "──────────────────────────────") # Separator, ignore
        exec "$0"
        exit 0
        ;;
esac

# Find which player was selected from the regular items
for item in "${sorted_items[@]}"; do
    display_text=$(echo "$item" | cut -d'|' -f3)
    if [ "$selection" = "$display_text" ]; then
        selected_player=$(echo "$item" | cut -d'|' -f2)
        break
    fi
done

# Switch to the selected player and toggle play/pause
playerctl -p "$selected_player" play-pause
new_status=$(playerctl -p "$selected_player" status)

# Extract base player name for icon selection
base_player=$(echo "$selected_player" | cut -d'.' -f1)

# Show notification with icon based on player
icon="audio-headphones"
case "$base_player" in
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

notify-send -a "Media Controller" "Switched to $selected_player" "Player status: $new_status\nSet as default player" -i "$icon"

# Show notification with icon based on player
icon="audio-headphones"
case "$base_player" in
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
