#!/usr/bin/env python3

import subprocess
import json
import sys
import os

def get_dunst_count():
    """Get the number of notifications from dunst"""
    try:
        # Check if dunst is running
        result = subprocess.run(['pgrep', 'dunst'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            return {"text": "󰂛", "tooltip": "Dunst not running", "class": "disabled"}
        
        # Get notification count from dunst history
        result = subprocess.run(['dunstctl', 'count', 'history'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            count = int(result.stdout.strip())
        else:
            count = 0
        
        # Check if dunst is paused (DND mode)
        result = subprocess.run(['dunstctl', 'is-paused'], 
                              capture_output=True, text=True)
        is_paused = result.returncode == 0 and result.stdout.strip().lower() == 'true'
        
        # Format output based on state
        if is_paused:
            icon = "󰂛"
            css_class = "dnd"
            tooltip = "Do Not Disturb mode enabled"
        elif count > 0:
            icon = f"󰂚"
            css_class = "notification"
            tooltip = f"{count} notification{'s' if count != 1 else ''} in history"
        else:
            icon = "󰂚"
            css_class = "normal"
            tooltip = "No notifications"
        
        return {
            "text": icon,
            "tooltip": tooltip,
            "class": css_class,
            "alt": str(count)
        }
    
    except Exception as e:
        return {"text": "󰂛", "tooltip": f"Error: {str(e)}", "class": "error"}

if __name__ == "__main__":
    result = get_dunst_count()
    print(json.dumps(result))
