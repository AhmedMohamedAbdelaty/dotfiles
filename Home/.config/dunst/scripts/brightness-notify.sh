#!/bin/bash

# Get current brightness
brightness=$(brightnessctl get)
max_brightness=$(brightnessctl max)
percentage=$(( brightness * 100 / max_brightness ))

# Icon based on brightness level
if [ "$percentage" -gt 75 ]; then
    icon="☀️"
elif [ "$percentage" -gt 50 ]; then
    icon="🌤️"
elif [ "$percentage" -gt 25 ]; then
    icon="🌥️"
else
    icon="🌑"
fi

# Create progress bar
bar_length=20
filled=$(( percentage * bar_length / 100 ))
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
dunstify -a "brightness" -u "low" -i "brightness-display" -r 2594 \
    -h int:value:"$percentage" \
    "$icon Brightness" "$percentage%\n$progress_bar"
