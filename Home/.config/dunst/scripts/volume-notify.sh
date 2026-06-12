#!/bin/bash

# Get current volume
volume=$(pamixer --get-volume)
is_muted=$(pamixer --get-mute)

if [ "$is_muted" = "true" ]; then
    icon="🔇"
    status="Muted"
    urgency="normal"
else
    if [ "$volume" -gt 66 ]; then
        icon="🔊"
        urgency="normal"
    elif [ "$volume" -gt 33 ]; then
        icon="🔉"
        urgency="normal"
    else
        icon="🔈"
        urgency="low"
    fi
    status="$volume%"
fi

# Create progress bar
bar_length=20
filled=$(( volume * bar_length / 100 ))
empty=$(( bar_length - filled ))

progress_bar="["
for ((i=0; i<filled; i++)); do
    progress_bar+="█"
done
for ((i=0; i<empty; i++)); do
    progress_bar+="░"
done
progress_bar+="]"

# Send notification
dunstify -a "volume" -u "$urgency" -i "audio-volume-high" -r 2593 \
    -h int:value:"$volume" \
    "$icon Volume" "$status\n$progress_bar"
