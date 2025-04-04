#!/usr/bin/env python3

import json
import sys
import os
import time
from datetime import datetime, timedelta

# Pomodoro settings
WORK_MINUTES = 25
SHORT_BREAK_MINUTES = 5
LONG_BREAK_MINUTES = 15
POMODORO_COUNT = 4

# File to store Pomodoro state
STATE_FILE = os.path.expanduser('~/.cache/waybar-pomodoro.json')

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass

    return {
        "active": False,
        "mode": "work",  # work, break
        "start_time": 0,
        "duration": WORK_MINUTES * 60,
        "completed_pomodoros": 0
    }

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"

def get_output(state):
    if not state["active"]:
        return {
            "text": "Pomodoro",
            "tooltip": "Click to start a Pomodoro session",
            "class": "pomodoro-inactive",
            "icon": "inactive"
        }

    elapsed = int(time.time() - state["start_time"])
    remaining = max(0, state["duration"] - elapsed)

    if remaining <= 0:
        # Timer finished
        notification_cmd = f"notify-send 'Pomodoro' '{state['mode'].capitalize()} time is up!'"
        os.system(notification_cmd)

        # Transition to next state
        if state["mode"] == "work":
            state["completed_pomodoros"] += 1
            state["mode"] = "break"

            if state["completed_pomodoros"] % POMODORO_COUNT == 0:
                state["duration"] = LONG_BREAK_MINUTES * 60
                message = "Long break"
            else:
                state["duration"] = SHORT_BREAK_MINUTES * 60
                message = "Short break"
        else:
            state["mode"] = "work"
            state["duration"] = WORK_MINUTES * 60
            message = "Focus time"

        state["start_time"] = time.time()
        save_state(state)

        return {
            "text": message,
            "tooltip": f"Mode: {state['mode'].capitalize()}\nCompleted Pomodoros: {state['completed_pomodoros']}",
            "class": f"pomodoro-{state['mode']}",
            "icon": state["mode"]
        }

    # Timer is active
    emoji = "󱎫" if state["mode"] == "work" else "󰒲"
    return {
        "text": f"{format_time(remaining)}",
        "tooltip": f"Mode: {state['mode'].capitalize()}\nRemaining: {format_time(remaining)}\nCompleted Pomodoros: {state['completed_pomodoros']}",
        "class": f"pomodoro-{state['mode']}-active",
        "icon": state["mode"]
    }

def toggle_pomodoro():
    state = load_state()

    if state["active"]:
        state["active"] = False
    else:
        state["active"] = True
        state["mode"] = "work"
        state["start_time"] = time.time()
        state["duration"] = WORK_MINUTES * 60

    save_state(state)

def end_pomodoro():
    state = load_state()
    state["active"] = False
    save_state(state)

def start_break():
    state = load_state()
    state["active"] = True
    state["mode"] = "break"
    state["start_time"] = time.time()
    state["duration"] = SHORT_BREAK_MINUTES * 60
    save_state(state)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "toggle":
            toggle_pomodoro()
        elif command == "end":
            end_pomodoro()
        elif command == "start-break":
            start_break()
    else:
        state = load_state()
        output = get_output(state)
        print(json.dumps(output))
