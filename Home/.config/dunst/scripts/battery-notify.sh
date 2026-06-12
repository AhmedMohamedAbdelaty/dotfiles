#!/bin/bash

# Get battery info
battery_info=$(acpi -b | head -1)
battery_percentage=$(echo "$battery_info" | grep -o '[0-9]\+%' | tr -d '%')
battery_status=$(echo "$battery_info" | awk '{print $3}' | tr -d ',')

# Determine icon and urgency
if [ "$battery_status" = "Charging" ]; then
    icon="🔌"
    urgency="normal"
    status="Charging"
elif [ "$battery_status" = "Full" ]; then
    icon="🔋"
    urgency="low"
    status="Full"
else
    if [ "$battery_percentage" -le 10 ]; then
        icon="🪫"
        urgency="critical"
        status="Critical"
    elif [ "$battery_percentage" -le 20 ]; then
        icon="🔋"
        urgency="normal"
        status="Low"
    else
        icon="��"
        urgency="low"
        status="Discharging"
    fi
fi

# Create battery bar
bar_length=20
filled=$(( battery_percentage * bar_length / 100 ))
empty=$(( bar_length - filled ))

battery_bar="["
for ((i=0; i<filled; i++)); do
    battery_bar+="█"
done
for ((i=0; i<empty; i++)); do
    battery_bar+="░"
done
battery_bar+="]"

# Send notification
dunstify -a "battery" -u "$urgency" -i "battery" -r 2595 \
    -h int:value:"$battery_percentage" \
    "$icon Battery" "$status - $battery_percentage%\n$battery_bar"
