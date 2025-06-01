#!/usr/bin/env python3

import json
import subprocess
import sys
import os
import time

def get_notification_count():
    """Get the number of notifications from swaync"""
    try:
        result = subprocess.run(['swaync-client', '-c'],
                              capture_output=True, text=True, check=True)
        count = int(result.stdout.strip())
        return count
    except (subprocess.CalledProcessError, ValueError):
        return 0

def get_dnd_status():
    """Check if Do Not Disturb is enabled"""
    try:
        result = subprocess.run(['swaync-client', '-D'],
                              capture_output=True, text=True, check=True)
        return result.stdout.strip() == 'true'
    except subprocess.CalledProcessError:
        return False

def main():
    count = get_notification_count()
    dnd = get_dnd_status()

    # State file to prevent unnecessary notifications
    state_file = os.path.expanduser("~/.cache/waybar-notifications-state.json")
    last_state = {}

    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                last_state = json.load(f)
    except:
        pass

    current_state = {'count': count, 'dnd': dnd}

    # Only update state file if something actually changed
    if current_state != last_state:
        try:
            with open(state_file, 'w') as f:
                json.dump(current_state, f)
        except:
            pass

    if dnd:
        icon = "󰂛"  # Bell with slash icon
        text = "DND"
        tooltip = "Do Not Disturb is enabled"
        css_class = "notifications-dnd"
    elif count == 0:
        icon = "󰂚"  # Bell icon
        text = ""
        tooltip = "No notifications"
        css_class = "notifications-none"
    else:
        icon = "󰂞"  # Bell with notification icon
        text = str(count)
        tooltip = f"{count} notification{'s' if count != 1 else ''}"
        css_class = "notifications-available"

    output = {
        "text": f"{icon} {text}".strip(),
        "tooltip": tooltip,
        "class": css_class
    }

    print(json.dumps(output))

if __name__ == "__main__":
    main()
