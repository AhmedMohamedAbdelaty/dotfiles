#!/usr/bin/env python3

import json
import sys
import os
import time
import subprocess
import argparse
from datetime import datetime, timedelta
from threading import Timer as ThreadTimer
import signal

# File paths
CACHE_DIR = os.path.expanduser('~/.cache/waybar')
STATE_FILE = os.path.join(CACHE_DIR, 'timer-manager.json')
ALARM_STATE_FILE = os.path.join(CACHE_DIR, 'alarm-state.json')

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

class TimerManager:
    def __init__(self):
        self.state = self.load_state()
        self.alarm_state = self.load_alarm_state()
        self.productivity_cache_dir = os.path.join(CACHE_DIR, 'productivity')
        os.makedirs(self.productivity_cache_dir, exist_ok=True)

    def load_state(self):
        """Load timer/stopwatch state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    # Validate and set defaults for missing keys
                    defaults = {
                        "mode": "idle",  # idle, timer, stopwatch, focus, break
                        "start_time": 0,
                        "duration": 0,
                        "paused": False,
                        "pause_start": 0,
                        "total_pause_time": 0,
                        "timer_name": "Timer",
                        "timer_type": "general",  # general, focus, break
                        "session_id": None
                    }
                    for key, default_value in defaults.items():
                        if key not in data:
                            data[key] = default_value
                    return data
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "mode": "idle",
            "start_time": 0,
            "duration": 0,
            "paused": False,
            "pause_start": 0,
            "total_pause_time": 0,
            "timer_name": "Timer",
            "timer_type": "general",
            "session_id": None
        }

    def load_alarm_state(self):
        """Load alarm state from file"""
        if os.path.exists(ALARM_STATE_FILE):
            try:
                with open(ALARM_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    defaults = {
                        "alarms": [],
                        "next_alarm": None,
                        "alarm_name": "Alarm"
                    }
                    for key, default_value in defaults.items():
                        if key not in data:
                            data[key] = default_value
                    return data
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "alarms": [],
            "next_alarm": None,
            "alarm_name": "Alarm"
        }

    def save_state(self):
        """Save current state to file"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            self.send_notification("Timer Error", f"Failed to save state: {e}", "critical")

    def save_alarm_state(self):
        """Save alarm state to file"""
        try:
            with open(ALARM_STATE_FILE, 'w') as f:
                json.dump(self.alarm_state, f, indent=2)
        except IOError as e:
            self.send_notification("Alarm Error", f"Failed to save alarm state: {e}", "critical")

    def send_notification(self, title, message, urgency="normal"):
        """Send desktop notification"""
        try:
            subprocess.Popen(['notify-send', '-u', urgency, '-a', 'Timer Manager', title, message],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def play_sound(self, sound_type="bell"):
        """Play notification sound"""
        sounds = {
            "bell": "bell.oga",
            "alarm": "alarm-clock-elapsed.oga",
            "complete": "complete.oga",
            "message": "message-new-instant.oga"
        }

        sound_file = sounds.get(sound_type, "bell.oga")
        sound_path = f"/usr/share/sounds/freedesktop/stereo/{sound_file}"

        try:
            subprocess.Popen(['paplay', sound_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # Fallback to system beep
            try:
                subprocess.Popen(['aplay', sound_path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def create_session_record(self, duration_minutes, name, session_type):
        """Create a session record for focus/break tracking"""
        import uuid
        session_id = str(uuid.uuid4())[:8]

        session_data = {
            "id": session_id,
            "name": name,
            "type": session_type,  # focus or break
            "planned_duration": duration_minutes / 60,  # Convert to minutes
            "start_time": datetime.now().isoformat(),
            "completed": False,
            "interrupted": False,
            "actual_duration": 0
        }

        # Save to analytics file
        analytics_file = os.path.join(self.productivity_cache_dir, 'analytics.json')
        try:
            if os.path.exists(analytics_file):
                with open(analytics_file, 'r') as f:
                    analytics = json.load(f)
            else:
                analytics = {"focus_sessions": [], "break_sessions": []}

            if session_type == "focus":
                analytics.setdefault("focus_sessions", []).append(session_data)
            else:
                analytics.setdefault("break_sessions", []).append(session_data)

            with open(analytics_file, 'w') as f:
                json.dump(analytics, f, indent=2)

        except Exception as e:
            self.send_notification("Session Error", f"Failed to create session record: {e}", "critical")

        return session_id

    def update_session_record(self, session_id, completed=True, interrupted=False):
        """Update session record when timer completes or is stopped"""
        if not session_id:
            return

        analytics_file = os.path.join(self.productivity_cache_dir, 'analytics.json')
        try:
            if not os.path.exists(analytics_file):
                return

            with open(analytics_file, 'r') as f:
                analytics = json.load(f)

            # Find and update the session
            for session_list in [analytics.get("focus_sessions", []), analytics.get("break_sessions", [])]:
                for session in session_list:
                    if session.get("id") == session_id:
                        session["completed"] = completed
                        session["interrupted"] = interrupted
                        session["end_time"] = datetime.now().isoformat()

                        # Calculate actual duration
                        if self.state["timer_type"] in ["focus", "break"]:
                            elapsed = self.get_current_time()
                            session["actual_duration"] = round(elapsed / 60, 1)  # Convert to minutes

                        # Award points if focus session completed
                        if session["type"] == "focus" and completed and not interrupted:
                            self.award_productivity_points(10)

                        break

            with open(analytics_file, 'w') as f:
                json.dump(analytics, f, indent=2)

        except Exception as e:
            self.send_notification("Session Error", f"Failed to update session: {e}", "critical")

    def award_productivity_points(self, points):
        """Award points to productivity manager"""
        try:
            achievements_file = os.path.join(self.productivity_cache_dir, 'achievements.json')
            daily_stats_file = os.path.join(self.productivity_cache_dir, 'daily_stats.json')

            # Update achievements points
            if os.path.exists(achievements_file):
                with open(achievements_file, 'r') as f:
                    achievements = json.load(f)

                old_points = achievements.get("points", 0)
                achievements["points"] = old_points + points

                # Calculate level
                achievements["level"] = (achievements["points"] // 100) + 1

                with open(achievements_file, 'w') as f:
                    json.dump(achievements, f, indent=2)

            # Update daily stats
            if os.path.exists(daily_stats_file):
                with open(daily_stats_file, 'r') as f:
                    daily_stats = json.load(f)

                if self.state["timer_type"] == "focus":
                    elapsed_minutes = round(self.get_current_time() / 60)
                    daily_stats["focus_time"] = daily_stats.get("focus_time", 0) + elapsed_minutes

                with open(daily_stats_file, 'w') as f:
                    json.dump(daily_stats, f, indent=2)

        except Exception:
            pass  # Fail silently for productivity integration

    def format_time(self, seconds):
        """Format seconds to HH:MM:SS or MM:SS format"""
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def get_current_time(self):
        """Get current time accounting for pauses"""
        current_time = time.time()

        if self.state["paused"]:
            return self.state["pause_start"] - self.state["start_time"] - self.state["total_pause_time"]
        else:
            return current_time - self.state["start_time"] - self.state["total_pause_time"]
    def start_timer(self, duration_seconds, name="Timer", timer_type="general"):
        """Start a countdown timer"""
        session_id = None
        if timer_type in ["focus", "break"]:
            session_id = self.create_session_record(duration_seconds, name, timer_type)

        self.state.update({
            "mode": "timer",
            "start_time": time.time(),
            "duration": duration_seconds,
            "paused": False,
            "pause_start": 0,
            "total_pause_time": 0,
            "timer_name": name,
            "timer_type": timer_type,
            "session_id": session_id
        })
        self.save_state()

        icon = "🧠" if timer_type == "focus" else "☕" if timer_type == "break" else "⏲️"
        self.send_notification(f"{icon} {name} Started", f"{self.format_time(duration_seconds)}")

    def start_stopwatch(self, name="Stopwatch"):
        """Start a stopwatch (count up)"""
        self.state.update({
            "mode": "stopwatch",
            "start_time": time.time(),
            "duration": 0,
            "paused": False,
            "pause_start": 0,
            "total_pause_time": 0,
            "timer_name": name
        })
        self.save_state()
        self.send_notification("Stopwatch Started", f"{name} is running")

    def toggle_pause(self):
        """Toggle pause/resume for timer or stopwatch"""
        if self.state["mode"] == "idle":
            return

        current_time = time.time()

        if self.state["paused"]:
            # Resume
            pause_duration = current_time - self.state["pause_start"]
            self.state["total_pause_time"] += pause_duration
            self.state["paused"] = False
            self.state["pause_start"] = 0
            self.send_notification(f"{self.state['timer_name']} Resumed", "Timer is now running")
        else:
            # Pause
            self.state["paused"] = True
            self.state["pause_start"] = current_time
            self.send_notification(f"{self.state['timer_name']} Paused", "Timer is paused")

        self.save_state()

    def stop_timer(self, interrupted=True):
        """Stop current timer or stopwatch"""
        if self.state["mode"] != "idle":
            name = self.state["timer_name"]
            session_id = self.state.get("session_id")
            timer_type = self.state.get("timer_type", "general")

            # Update session record if this was a focus/break session
            if session_id and timer_type in ["focus", "break"]:
                self.update_session_record(session_id, completed=not interrupted, interrupted=interrupted)

            self.state.update({
                "mode": "idle",
                "start_time": 0,
                "duration": 0,
                "paused": False,
                "pause_start": 0,
                "total_pause_time": 0,
                "timer_name": "Timer",
                "timer_type": "general",
                "session_id": None
            })
            self.save_state()

            if interrupted:
                self.send_notification(f"{name} Stopped", "Timer has been stopped")
            else:
                icon = "🧠" if timer_type == "focus" else "☕" if timer_type == "break" else "⏲️"
                self.send_notification(f"{icon} {name} Complete!", "Timer finished successfully")

    def add_alarm(self, alarm_time, name="Alarm"):
        """Add a new alarm"""
        try:
            # Parse time in HH:MM format
            hour, minute = map(int, alarm_time.split(':'))
            now = datetime.now()
            alarm_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If time has passed today, schedule for tomorrow
            if alarm_datetime <= now:
                alarm_datetime += timedelta(days=1)

            alarm_data = {
                "time": alarm_datetime.isoformat(),
                "name": name,
                "enabled": True,
                "timestamp": alarm_datetime.timestamp()
            }

            self.alarm_state["alarms"].append(alarm_data)
            self.alarm_state["alarms"].sort(key=lambda x: x["timestamp"])
            self.update_next_alarm()
            self.save_alarm_state()

            self.send_notification("Alarm Set", f"{name} at {alarm_time}")
            return True
        except (ValueError, IndexError):
            self.send_notification("Alarm Error", "Invalid time format. Use HH:MM", "critical")
            return False
    def remove_alarm(self, index):
        """Remove alarm by index"""
        try:
            if 0 <= index < len(self.alarm_state["alarms"]):
                removed = self.alarm_state["alarms"].pop(index)
                self.update_next_alarm()
                self.save_alarm_state()
                self.send_notification("Alarm Removed", f"Removed: {removed['name']}")
                return True
        except Exception:
            pass
        return False

    def toggle_alarm(self, index):
        """Toggle alarm on/off by index"""
        try:
            if 0 <= index < len(self.alarm_state["alarms"]):
                alarm = self.alarm_state["alarms"][index]
                alarm["enabled"] = not alarm["enabled"]
                self.update_next_alarm()
                self.save_alarm_state()
                status = "enabled" if alarm["enabled"] else "disabled"
                self.send_notification("Alarm Toggled", f"{alarm['name']} {status}")
                return True
        except Exception:
            pass
        return False

    def update_next_alarm(self):
        """Update the next alarm to trigger"""
        now = time.time()
        next_alarm = None

        for alarm in self.alarm_state["alarms"]:
            if alarm["enabled"] and alarm["timestamp"] > now:
                if next_alarm is None or alarm["timestamp"] < next_alarm["timestamp"]:
                    next_alarm = alarm

        self.alarm_state["next_alarm"] = next_alarm

    def check_alarms(self):
        """Check if any alarms should trigger"""
        now = time.time()
        triggered_alarms = []

        for i, alarm in enumerate(self.alarm_state["alarms"]):
            if alarm["enabled"] and alarm["timestamp"] <= now:
                triggered_alarms.append((i, alarm))

        for index, alarm in triggered_alarms:
            self.trigger_alarm(alarm)
            # Schedule for next day
            alarm_time = datetime.fromisoformat(alarm["time"])
            next_day = alarm_time + timedelta(days=1)
            alarm["time"] = next_day.isoformat()
            alarm["timestamp"] = next_day.timestamp()

        if triggered_alarms:
            self.alarm_state["alarms"].sort(key=lambda x: x["timestamp"])
            self.update_next_alarm()
            self.save_alarm_state()

    def trigger_alarm(self, alarm):
        """Trigger an alarm"""
        self.play_sound("alarm")
        self.send_notification("⏰ ALARM", f"{alarm['name']}", "critical")

        # Also try to show a more prominent notification using zenity if available
        try:
            subprocess.Popen(['zenity', '--warning', '--title=ALARM!',
                            f'--text={alarm["name"]}\n\nAlarm time reached!',
                            '--width=300', '--height=150'])
        except Exception:
            pass
    def get_status(self):
        """Get current status for waybar output"""
        self.check_alarms()  # Check alarms on every status update

        # Handle timer completion
        if self.state["mode"] == "timer" and not self.state["paused"]:
            elapsed = self.get_current_time()
            if elapsed >= self.state["duration"]:
                # Timer completed
                self.play_sound("complete")
                timer_type = self.state.get("timer_type", "general")
                icon = "🧠" if timer_type == "focus" else "☕" if timer_type == "break" else "⏰"
                self.send_notification(f"{icon} Timer Complete!", f"{self.state['timer_name']} finished", "critical")
                self.stop_timer(interrupted=False)  # Mark as completed, not interrupted
                return self.get_idle_status()

        if self.state["mode"] == "idle":
            return self.get_idle_status()
        elif self.state["mode"] == "timer":
            return self.get_timer_status()
        elif self.state["mode"] == "stopwatch":
            return self.get_stopwatch_status()

    def get_idle_status(self):
        """Get status when no timer is running"""
        next_alarm = self.alarm_state.get("next_alarm")

        if next_alarm:
            alarm_time = datetime.fromisoformat(next_alarm["time"])
            now = datetime.now()
            time_until = alarm_time - now

            if time_until.total_seconds() < 3600:  # Less than 1 hour
                minutes = int(time_until.total_seconds() / 60)
                text = f"🔔 {minutes}m"
                tooltip = f"Next alarm: {next_alarm['name']} in {minutes} minutes"
            else:
                text = f"🔔 {alarm_time.strftime('%H:%M')}"
                tooltip = f"Next alarm: {next_alarm['name']} at {alarm_time.strftime('%H:%M')}"

            css_class = "timer-alarm-pending"
        else:
            text = "⏱️"
            tooltip = "Timer Manager\n\nLeft click: Quick timer menu\nRight click: Advanced options"
            css_class = "timer-idle"

        return {
            "text": text,
            "tooltip": tooltip,
            "class": css_class
        }

    def get_timer_status(self):
        """Get timer countdown status"""
        elapsed = self.get_current_time()
        remaining = max(0, self.state["duration"] - elapsed)
        timer_type = self.state.get("timer_type", "general")

        # Choose icon based on timer type and state
        if self.state["paused"]:
            icon = "⏸️"
            css_class = "timer-paused"
        else:
            if timer_type == "focus":
                icon = "🧠"
                css_class = "timer-focus"
            elif timer_type == "break":
                icon = "☕"
                css_class = "timer-break"
            else:
                icon = "⏲️"
                css_class = "timer-active"

        text = f"{icon} {self.format_time(remaining)}"
        progress = min(100, (elapsed / self.state["duration"]) * 100) if self.state["duration"] > 0 else 0

        tooltip = f"{self.state['timer_name']}\n"
        tooltip += f"Remaining: {self.format_time(remaining)}\n"
        tooltip += f"Progress: {int(progress)}%"

        if timer_type in ["focus", "break"]:
            tooltip += f"\nType: {timer_type.title()} Session"

        return {
            "text": text,
            "tooltip": tooltip,
            "class": css_class
        }

    def get_stopwatch_status(self):
        """Get stopwatch status"""
        elapsed = self.get_current_time()

        if self.state["paused"]:
            text = f"⏸️ {self.format_time(elapsed)}"
            css_class = "stopwatch-paused"
        else:
            text = f"⏱️ {self.format_time(elapsed)}"
            css_class = "stopwatch-active"

        tooltip = f"Stopwatch: {self.state['timer_name']}\n"
        tooltip += f"Elapsed: {self.format_time(elapsed)}"

        return {
            "text": text,
            "tooltip": tooltip,
            "class": css_class
        }

def show_quick_menu():
    """Show quick timer menu using rofi"""
    options = [
        "🧠 Focus Session (25m)",
        "🧠 Deep Focus (50m)",
        "☕ Short Break (5m)",
        "☕ Long Break (15m)",
        "🍽️ Lunch break (30m)",
        "⏱️ Custom timer",
        "🏃 Start stopwatch",
        "⏰ Set alarm",
        "📋 Manage alarms",
        "⏹️ Stop current"
    ]

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Timer Manager',
                                '-theme-str', 'window {width: 300px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()
            tm = TimerManager()

            if "Focus Session (25m)" in selection:
                tm.start_timer(25 * 60, "Focus Session", "focus")
            elif "Deep Focus (50m)" in selection:
                tm.start_timer(50 * 60, "Deep Focus", "focus")
            elif "Short Break (5m)" in selection:
                tm.start_timer(5 * 60, "Short Break", "break")
            elif "Long Break (15m)" in selection:
                tm.start_timer(15 * 60, "Long Break", "break")
            elif "Lunch break" in selection:
                tm.start_timer(30 * 60, "Lunch Break")
            elif "Custom timer" in selection:
                show_custom_timer_dialog()
            elif "Start stopwatch" in selection:
                tm.start_stopwatch()
            elif "Set alarm" in selection:
                show_alarm_dialog()
            elif "Manage alarms" in selection:
                show_alarm_manager()
            elif "Stop current" in selection:
                tm.stop_timer()

    except Exception as e:
        tm = TimerManager()
        tm.send_notification("Menu Error", f"Failed to show menu: {e}", "critical")

def show_custom_timer_dialog():
    """Show dialog for custom timer"""
    try:
        # Get duration
        result = subprocess.run(['zenity', '--entry', '--title=Custom Timer',
                                '--text=Enter duration (e.g., 10m, 1h30m, 90s):',
                                '--entry-text=10m'],
                               capture_output=True, text=True)

        if result.returncode == 0:
            duration_str = result.stdout.strip().lower()

            # Parse duration
            total_seconds = 0
            if 'h' in duration_str:
                parts = duration_str.split('h')
                total_seconds += int(parts[0]) * 3600
                if len(parts) > 1 and parts[1]:
                    remaining = parts[1].replace('m', '').replace('s', '')
                    if 'm' in parts[1]:
                        total_seconds += int(remaining.replace('m', '')) * 60
                    elif remaining:
                        total_seconds += int(remaining)
            elif 'm' in duration_str:
                total_seconds = int(duration_str.replace('m', '')) * 60
            elif 's' in duration_str:
                total_seconds = int(duration_str.replace('s', ''))
            else:
                total_seconds = int(duration_str) * 60  # Default to minutes

            # Get name
            name_result = subprocess.run(['zenity', '--entry', '--title=Timer Name',
                                         '--text=Enter timer name:',
                                         '--entry-text=Custom Timer'],
                                        capture_output=True, text=True)

            name = "Custom Timer"
            if name_result.returncode == 0:
                name = name_result.stdout.strip() or "Custom Timer"

            tm = TimerManager()
            tm.start_timer(total_seconds, name)

    except Exception as e:
        tm = TimerManager()
        tm.send_notification("Timer Error", f"Invalid duration format: {e}", "critical")

def show_alarm_dialog():
    """Show dialog for setting alarm"""
    try:
        result = subprocess.run(['zenity', '--entry', '--title=Set Alarm',
                                '--text=Enter alarm time (HH:MM):',
                                '--entry-text=' + datetime.now().strftime('%H:%M')],
                               capture_output=True, text=True)

        if result.returncode == 0:
            alarm_time = result.stdout.strip()

            # Get name
            name_result = subprocess.run(['zenity', '--entry', '--title=Alarm Name',
                                         '--text=Enter alarm name:',
                                         '--entry-text=Wake up'],
                                        capture_output=True, text=True)

            name = "Wake up"
            if name_result.returncode == 0:
                name = name_result.stdout.strip() or "Wake up"

            tm = TimerManager()
            tm.add_alarm(alarm_time, name)

    except Exception as e:
        tm = TimerManager()
        tm.send_notification("Alarm Error", f"Failed to set alarm: {e}", "critical")

def show_alarm_manager():
    """Show alarm management interface"""
    tm = TimerManager()

    if not tm.alarm_state["alarms"]:
        tm.send_notification("No Alarms", "No alarms are currently set")
        return

    options = []
    for i, alarm in enumerate(tm.alarm_state["alarms"]):
        alarm_time = datetime.fromisoformat(alarm["time"])
        status = "✅" if alarm["enabled"] else "❌"
        options.append(f"{status} {alarm['name']} - {alarm_time.strftime('%H:%M')}")

    options.append("➕ Add new alarm")

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Manage Alarms',
                                '-theme-str', 'window {width: 400px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Add new alarm" in selection:
                show_alarm_dialog()
            else:
                # Find selected alarm index
                for i, option in enumerate(options[:-1]):
                    if option == selection:
                        # Show alarm options
                        alarm_options = [
                            "🔄 Toggle on/off",
                            "🗑️ Delete alarm"
                        ]

                        action_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Alarm Action'],
                                                     input='\n'.join(alarm_options), text=True,
                                                     capture_output=True)

                        if action_result.returncode == 0:
                            action = action_result.stdout.strip()
                            if "Toggle" in action:
                                tm.toggle_alarm(i)
                            elif "Delete" in action:
                                tm.remove_alarm(i)
                        break

    except Exception as e:
        tm.send_notification("Manager Error", f"Failed to show alarm manager: {e}", "critical")

def main():
    parser = argparse.ArgumentParser(description='Timer Manager for Waybar')
    parser.add_argument('action', nargs='?', default='status',
                       choices=['status', 'toggle', 'stop', 'menu', 'pause', 'quick-timer', 'start-focus', 'start-break'])
    parser.add_argument('--duration', type=int, help='Timer duration in minutes')
    parser.add_argument('--name', type=str, default='Timer', help='Timer name')
    parser.add_argument('--alarm', type=str, help='Set alarm time (HH:MM)')

    args = parser.parse_args()
    tm = TimerManager()

    if args.action == 'status':
        status = tm.get_status()
        print(json.dumps(status))

    elif args.action == 'toggle':
        tm.toggle_pause()

    elif args.action == 'stop':
        tm.stop_timer()

    elif args.action == 'menu':
        show_quick_menu()

    elif args.action == 'pause':
        tm.toggle_pause()

    elif args.action == 'start-focus':
        duration = args.duration or 25
        name = args.name if args.name != 'Timer' else 'Focus Session'
        tm.start_timer(duration * 60, name, "focus")

    elif args.action == 'start-break':
        duration = args.duration or 5
        name = args.name if args.name != 'Timer' else 'Break'
        tm.start_timer(duration * 60, name, "break")

    elif args.action == 'quick-timer':
        if args.duration:
            # Convert minutes to seconds
            total_seconds = args.duration * 60
            tm.start_timer(total_seconds, args.name)

if __name__ == "__main__":
    # Handle signals gracefully
    def signal_handler(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    main()
