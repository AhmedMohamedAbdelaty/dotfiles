#!/usr/bin/env python3

import json
import sys
import os
import time
import subprocess
import configparser
from datetime import datetime, timedelta

# File paths
CONFIG_DIR = os.path.expanduser('~/.config/waybar')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'pomodoro.conf')
STATE_FILE = os.path.expanduser('~/.cache/waybar-pomodoro.json')
STATS_FILE = os.path.expanduser('~/.cache/waybar-pomodoro-stats.json')

# Default Pomodoro settings
DEFAULT_SETTINGS = {
    'General': {
        'work_minutes': '25',
        'short_break_minutes': '5',
        'long_break_minutes': '15',
        'pomodoros_until_long_break': '4',
        'auto_start_breaks': 'true',
        'auto_start_work': 'true',
        'sound_notifications': 'true',
        'notification_volume': '70',
        'show_seconds': 'true',
        'show_progress_bar': 'true',
        'focus_mode': 'false'
    }
}

def load_config():
    """Load configuration from file or create default if it doesn't exist"""
    config = configparser.ConfigParser()

    if not os.path.exists(CONFIG_FILE):
        config.read_dict(DEFAULT_SETTINGS)
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE)

    return config

def load_state():
    """Load the current state of the Pomodoro timer"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)

                # Add missing keys with defaults if they don't exist
                defaults = {
                    "active": False,
                    "paused": False,
                    "pause_time": 0,
                    "mode": "work",
                    "start_time": 0,
                    "duration": int(get_setting('work_minutes')) * 60,
                    "elapsed_pause_time": 0,
                    "completed_pomodoros": 0,
                    "completed_today": 0,
                    "last_completed_date": "",
                    "current_task": "Focus",
                    "focus_mode": False,
                    "focus_apps": []
                }

                # Update the state with any missing default values
                for key, value in defaults.items():
                    if key not in state:
                        state[key] = value

                return state
        except:
            pass

    return {
        "active": False,
        "paused": False,
        "pause_time": 0,
        "mode": "work",  # work, short_break, long_break
        "start_time": 0,
        "duration": int(get_setting('work_minutes')) * 60,
        "elapsed_pause_time": 0,
        "completed_pomodoros": 0,
        "completed_today": 0,
        "last_completed_date": "",
        "current_task": "Focus",
        "focus_mode": False,
        "focus_apps": []
    }

def load_stats():
    """Load session statistics"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass

    return {
        "total_completed": 0,
        "total_work_time": 0,
        "daily_stats": {},
        "tasks": {},
        "streaks": {
            "current": 0,
            "longest": 0,
            "last_date": ""
        }
    }

def update_stats(state, completed=False):
    """Update session statistics"""
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")

    # Initialize daily stats if not exist
    if today not in stats["daily_stats"]:
        stats["daily_stats"][today] = {
            "completed": 0,
            "work_time": 0
        }

    # Update streaks
    if completed and state["mode"] == "work":
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Check if we have a continuing streak
        if stats["streaks"]["last_date"] == yesterday:
            stats["streaks"]["current"] += 1
        elif stats["streaks"]["last_date"] != today:  # Not today and not yesterday = streak broken
            stats["streaks"]["current"] = 1

        # Only update if we haven't already counted today
        if stats["streaks"]["last_date"] != today:
            stats["streaks"]["last_date"] = today

        # Update longest streak if current is bigger
        if stats["streaks"]["current"] > stats["streaks"]["longest"]:
            stats["streaks"]["longest"] = stats["streaks"]["current"]

    # Update completed count if a pomodoro was completed
    if completed and state["mode"] == "work":
        stats["total_completed"] += 1
        stats["daily_stats"][today]["completed"] += 1

        # Update task stats
        task = state.get("current_task", "Focus")
        if task not in stats["tasks"]:
            stats["tasks"][task] = {
                "completed": 0,
                "work_time": 0
            }
        stats["tasks"][task]["completed"] += 1
        stats["tasks"][task]["work_time"] += int(get_setting('work_minutes')) * 60

        # Add work time
        work_minutes = int(get_setting('work_minutes'))
        stats["total_work_time"] += work_minutes * 60
        stats["daily_stats"][today]["work_time"] += work_minutes * 60

    # Save updated stats
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

def save_state(state):
    """Save the current state of the Pomodoro timer"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def get_setting(setting_name):
    """Get a setting value from config"""
    config = load_config()
    section = 'General'

    if setting_name == 'work_minutes':
        return config.get(section, setting_name, fallback='25')
    elif setting_name == 'short_break_minutes':
        return config.get(section, setting_name, fallback='5')
    elif setting_name == 'long_break_minutes':
        return config.get(section, setting_name, fallback='15')
    elif setting_name == 'pomodoros_until_long_break':
        return config.get(section, setting_name, fallback='4')
    elif setting_name == 'auto_start_breaks':
        return config.getboolean(section, setting_name, fallback=True)
    elif setting_name == 'auto_start_work':
        return config.getboolean(section, setting_name, fallback=True)
    elif setting_name == 'sound_notifications':
        return config.getboolean(section, setting_name, fallback=True)
    elif setting_name == 'notification_volume':
        return config.get(section, setting_name, fallback='70')
    elif setting_name == 'show_seconds':
        return config.getboolean(section, setting_name, fallback=True)
    elif setting_name == 'show_progress_bar':
        return config.getboolean(section, setting_name, fallback=True)
    elif setting_name == 'focus_mode':
        return config.getboolean(section, setting_name, fallback=False)

    return None

def format_time(seconds):
    """Format seconds to mm:ss or mm depending on settings"""
    minutes, seconds = divmod(max(0, int(seconds)), 60)

    if get_setting('show_seconds'):
        return f"{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}m"

def play_notification_sound(sound_type):
    """Play notification sound based on type"""
    if not get_setting('sound_notifications'):
        return

    volume = get_setting('notification_volume')
    sounds = {
        'work_complete': 'bell',
        'break_complete': 'message',
        'start': 'message-new-instant',
        'focus_on': 'suspend-error',
        'focus_off': 'complete'
    }

    sound = sounds.get(sound_type, 'bell')
    try:
        subprocess.Popen(['paplay', '-v', volume, f'/usr/share/sounds/freedesktop/stereo/{sound}.oga'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except:
        # Fallback to other sound methods
        try:
            subprocess.Popen(['aplay', '-q', f'/usr/share/sounds/freedesktop/stereo/{sound}.oga'],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        except:
            pass

def send_notification(title, message, urgency="normal"):
    """Send desktop notification"""
    try:
        subprocess.Popen(['notify-send', '-u', urgency, title, message],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except:
        pass

def calculate_progress(state):
    """Calculate progress percentage for the current session"""
    if not state["active"] or state["paused"]:
        if state["paused"] and state["start_time"] > 0:
            elapsed = state["pause_time"] - state["start_time"] - state["elapsed_pause_time"]
            return min(100, max(0, (elapsed / state["duration"]) * 100))
        return 0

    elapsed = int(time.time() - state["start_time"] - state["elapsed_pause_time"])
    return min(100, max(0, (elapsed / state["duration"]) * 100))

def get_remaining_time(state):
    """Calculate remaining time in seconds"""
    if not state["active"]:
        return 0

    if state["paused"]:
        elapsed = state["pause_time"] - state["start_time"] - state["elapsed_pause_time"]
    else:
        elapsed = int(time.time() - state["start_time"] - state["elapsed_pause_time"])

    return max(0, state["duration"] - elapsed)

def get_emoji_for_progress(progress, mode):
    """Return emoji based on progress and mode"""
    if mode == "work":
        if progress < 25:
            return "󱎫"  # Start of work
        elif progress < 50:
            return "󱎪"  # Quarter through
        elif progress < 75:
            return "󱎭"  # Half through
        else:
            return "󱎬"  # Almost done
    else:
        if progress < 33:
            return "󰒲"  # Start of break
        elif progress < 66:
            return "󰒳"  # Middle of break
        else:
            return "󰒱"  # End of break

def toggle_focus_mode(enable=None):
    """Toggle focus mode to minimize distractions"""
    state = load_state()

    if enable is None:
        # Toggle the current state
        state["focus_mode"] = not state["focus_mode"]
    else:
        state["focus_mode"] = enable

    if state["focus_mode"]:
        # Enable focus mode
        try:
            # Store list of currently open apps to restore later
            result = subprocess.run(['hyprctl', 'clients', '-j'], stdout=subprocess.PIPE, text=True)
            if result.returncode == 0:
                clients = json.loads(result.stdout)
                state["focus_apps"] = [client['address'] for client in clients
                                      if not (client.get('title', '').startswith('waybar') or
                                             client.get('class', '').startswith('waybar'))]

            # Minimize all apps except current one
            subprocess.run(['hyprctl', 'dispatch', 'togglespecialworkspace', 'focus'])

            play_notification_sound('focus_on')
            send_notification('Focus Mode Enabled', 'Distractions minimized. Stay focused!', 'normal')
        except Exception as e:
            send_notification('Focus Mode Error', f'Could not enable focus mode: {str(e)}', 'critical')
    else:
        # Disable focus mode
        try:
            # Restore minimized apps
            subprocess.run(['hyprctl', 'dispatch', 'togglespecialworkspace', 'focus'])

            play_notification_sound('focus_off')
            send_notification('Focus Mode Disabled', 'Normal workspace restored.', 'normal')
        except Exception as e:
            send_notification('Focus Mode Error', f'Could not disable focus mode: {str(e)}', 'critical')

    save_state(state)

def get_output(state):
    """Generate output for waybar"""
    # Check if it's a new day, reset completed_today if needed
    today = datetime.now().strftime("%Y-%m-%d")
    if state["last_completed_date"] != today:
        state["completed_today"] = 0
        state["last_completed_date"] = today
        save_state(state)

    if not state["active"]:
        return {
            "text": f"{state['completed_today']}",
            "tooltip": f"Pomodoro Timer\n\nCompleted today: {state['completed_today']}\nClick to start a work session",
            "class": "pomodoro-inactive",
            "icon": "inactive",
            "progress": 0
        }

    # Calculate remaining time and progress
    remaining = get_remaining_time(state)
    progress = calculate_progress(state)

    # Format status text based on state
    if state["paused"]:
        status_text = f"{format_time(remaining)} ⏸"
        class_suffix = "paused"
    else:
        status_text = format_time(remaining)
        class_suffix = "active"

    # Get emoji for progress
    emoji = get_emoji_for_progress(progress, state["mode"])

    # Add focus mode indicator
    if state["focus_mode"]:
        status_text = f"🔍 {status_text}"

    mode_name = state["mode"].replace("_", " ").title()

    # Handle completed timer
    if remaining <= 0 and not state["paused"]:
        # Timer finished
        completed = False
        if state["mode"] == "work":
            state["completed_pomodoros"] += 1
            state["completed_today"] += 1
            completed = True

            # Update stats
            update_stats(state, completed=True)

            # Play notification and send alert
            play_notification_sound('work_complete')
            send_notification('Pomodoro Complete!', f'Great job! You\'ve completed {state["completed_today"]} pomodoros today.', 'critical')

            # If focus mode is enabled and this is the end of work session, disable it
            if state["focus_mode"]:
                toggle_focus_mode(False)

            # Determine next mode
            if state["completed_pomodoros"] % int(get_setting('pomodoros_until_long_break')) == 0:
                state["mode"] = "long_break"
                state["duration"] = int(get_setting('long_break_minutes')) * 60
                message = "Time for a long break!"
            else:
                state["mode"] = "short_break"
                state["duration"] = int(get_setting('short_break_minutes')) * 60
                message = "Time for a short break!"

            # Auto-start break if enabled
            if get_setting('auto_start_breaks'):
                state["start_time"] = time.time()
                state["elapsed_pause_time"] = 0
                state["paused"] = False
            else:
                state["active"] = False

        else:  # Break is over
            play_notification_sound('break_complete')
            send_notification('Break Complete!', 'Time to focus again!', 'normal')

            state["mode"] = "work"
            state["duration"] = int(get_setting('work_minutes')) * 60
            message = "Back to work!"

            # Auto-start work if enabled
            if get_setting('auto_start_work'):
                state["start_time"] = time.time()
                state["elapsed_pause_time"] = 0
                state["paused"] = False

                # Auto-enable focus mode if configured
                if get_setting('focus_mode') and not state["focus_mode"]:
                    toggle_focus_mode(True)
            else:
                state["active"] = False

        save_state(state)

        # If state is now inactive, return inactive status
        if not state["active"]:
            return {
                "text": f"{state['completed_today']} | {message}",
                "tooltip": f"Pomodoro Timer\n\n{message}\nCompleted today: {state['completed_today']}\nClick to start a new session",
                "class": "pomodoro-inactive",
                "icon": "inactive",
                "progress": 0
            }

    # For active timer, return appropriate status
    current_task = state.get("current_task", "Focus")

    # Load stats for streak information
    stats = load_stats()
    streak = stats.get("streaks", {}).get("current", 0)

    tooltip_lines = [
        f"Mode: {mode_name}",
        f"Task: {current_task}",
        f"Remaining: {format_time(remaining)}",
        f"Completed today: {state['completed_today']}",
        f"Current streak: {streak} days",
        f"Progress: {int(progress)}%"
    ]

    if state["focus_mode"]:
        tooltip_lines.append("Focus mode: Enabled")

    if state["mode"] == "work":
        tooltip_lines.append(f"Pomodoro #{state['completed_pomodoros'] + 1}")

    tooltip = "\n".join(tooltip_lines)

    return {
        "text": status_text,
        "tooltip": tooltip,
        "class": f"pomodoro-{state['mode']}-{class_suffix}{' pomodoro-focus' if state['focus_mode'] else ''}",
        "icon": state["mode"],
        "progress": int(progress)
    }

def toggle_pomodoro():
    """Start or stop the Pomodoro timer"""
    state = load_state()

    if state["active"]:
        state["active"] = False

        # If we're stopping and focus mode is enabled, disable it
        if state["focus_mode"]:
            toggle_focus_mode(False)

        play_notification_sound('start')
        send_notification('Pomodoro Stopped', 'Timer has been stopped')
    else:
        state["active"] = True
        state["paused"] = False
        state["mode"] = "work"
        state["start_time"] = time.time()
        state["elapsed_pause_time"] = 0
        state["duration"] = int(get_setting('work_minutes')) * 60

        # Auto-enable focus mode if configured
        if get_setting('focus_mode'):
            toggle_focus_mode(True)

        play_notification_sound('start')
        send_notification('Pomodoro Started', f'Focus time: {get_setting("work_minutes")} minutes')

    save_state(state)

def pause_resume_pomodoro():
    """Pause or resume the current Pomodoro session"""
    state = load_state()

    if not state["active"]:
        return

    if state["paused"]:
        # Resume timer
        elapsed_pause = int(time.time() - state["pause_time"])
        state["elapsed_pause_time"] += elapsed_pause
        state["paused"] = False
        send_notification('Pomodoro Resumed', 'Timer is now running')
    else:
        # Pause timer
        state["paused"] = True
        state["pause_time"] = time.time()
        send_notification('Pomodoro Paused', 'Timer has been paused')

    save_state(state)

def end_pomodoro():
    """End the current Pomodoro session"""
    state = load_state()

    if state["active"]:
        state["active"] = False

        # If focus mode is enabled, disable it
        if state["focus_mode"]:
            toggle_focus_mode(False)

        send_notification('Pomodoro Ended', 'The session has been ended')

    save_state(state)

def start_break():
    """Manually start a break session"""
    state = load_state()
    state["active"] = True
    state["paused"] = False

    # If focus mode is enabled, disable it for breaks
    if state["focus_mode"]:
        toggle_focus_mode(False)

    # Determine break type based on completed pomodoros
    if state["completed_pomodoros"] % int(get_setting('pomodoros_until_long_break')) == 0:
        state["mode"] = "long_break"
        state["duration"] = int(get_setting('long_break_minutes')) * 60
        message = "Long break"
    else:
        state["mode"] = "short_break"
        state["duration"] = int(get_setting('short_break_minutes')) * 60
        message = "Short break"

    state["start_time"] = time.time()
    state["elapsed_pause_time"] = 0

    play_notification_sound('start')
    send_notification('Break Started', f'{message} time: {state["duration"] // 60} minutes')

    save_state(state)

def start_work():
    """Manually start a work session"""
    state = load_state()
    state["active"] = True
    state["paused"] = False
    state["mode"] = "work"
    state["start_time"] = time.time()
    state["elapsed_pause_time"] = 0
    state["duration"] = int(get_setting('work_minutes')) * 60

    # Auto-enable focus mode if configured
    if get_setting('focus_mode') and not state["focus_mode"]:
        toggle_focus_mode(True)

    play_notification_sound('start')
    send_notification('Work Session Started', f'Focus time: {get_setting("work_minutes")} minutes')

    save_state(state)

def set_task(task_name=None):
    """Set the current task name"""
    state = load_state()

    if task_name is None:
        # Prompt for task name using zenity
        try:
            result = subprocess.run(['zenity', '--entry', '--title=Pomodoro Task',
                                    '--text=What are you working on?',
                                    '--entry-text=' + state.get("current_task", "Focus")],
                                   stdout=subprocess.PIPE, text=True)
            if result.returncode == 0:
                task_name = result.stdout.strip()
        except:
            return

    if task_name and task_name.strip():
        state["current_task"] = task_name.strip()
        save_state(state)
        send_notification('Task Updated', f'Current task: {state["current_task"]}')

def show_stats():
    """Display Pomodoro statistics"""
    stats = load_stats()
    state = load_state()

    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = stats["daily_stats"].get(today, {"completed": 0, "work_time": 0})

    # Format work time
    total_time_str = format_time(stats["total_work_time"])
    today_time_str = format_time(today_stats["work_time"])

    # Get streak information
    current_streak = stats.get("streaks", {}).get("current", 0)
    longest_streak = stats.get("streaks", {}).get("longest", 0)

    # Create message
    message = f"Pomodoro Statistics\n\n"
    message += f"Today: {state['completed_today']} pomodoros ({today_time_str})\n"
    message += f"All time: {stats['total_completed']} pomodoros ({total_time_str})\n"
    message += f"Current streak: {current_streak} days\n"
    message += f"Longest streak: {longest_streak} days\n\n"

    # Add recent tasks
    message += "Recent tasks:\n"

    # Sort tasks by completion count
    sorted_tasks = sorted(stats["tasks"].items(), key=lambda x: x[1]["completed"], reverse=True)
    for task, task_stats in sorted_tasks[:5]:  # Show top 5 tasks
        task_time = format_time(task_stats["work_time"])
        message += f"- {task}: {task_stats['completed']} ({task_time})\n"

    try:
        subprocess.Popen(['zenity', '--info', '--title=Pomodoro Statistics',
                         '--text=' + message, '--width=400', '--height=300'])
    except:
        send_notification('Pomodoro Statistics', message)

def toggle_focus():
    """Toggle focus mode"""
    toggle_focus_mode()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "toggle":
            toggle_pomodoro()
        elif command == "pause":
            pause_resume_pomodoro()
        elif command == "end":
            end_pomodoro()
        elif command == "start-break":
            start_break()
        elif command == "start-work":
            start_work()
        elif command == "set-task":
            task = sys.argv[2] if len(sys.argv) > 2 else None
            set_task(task)
        elif command == "stats":
            show_stats()
        elif command == "focus":
            toggle_focus()
    else:
        state = load_state()
        output = get_output(state)
        print(json.dumps(output))
