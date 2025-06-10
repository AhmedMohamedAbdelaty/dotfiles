#!/usr/bin/env python3

import json
import sys
import os
import time
import subprocess
import argparse
from datetime import datetime, timedelta, date
from collections import defaultdict
import psutil
import signal
from pathlib import Path
import threading
import fcntl

# File paths
CACHE_DIR = os.path.expanduser('~/.cache/waybar')
PRODUCTIVITY_DIR = os.path.join(CACHE_DIR, 'productivity')
GOALS_FILE = os.path.join(PRODUCTIVITY_DIR, 'goals.json')
ACHIEVEMENTS_FILE = os.path.join(PRODUCTIVITY_DIR, 'achievements.json')
HABITS_FILE = os.path.join(PRODUCTIVITY_DIR, 'habits.json')
NOTES_FILE = os.path.join(PRODUCTIVITY_DIR, 'notes.json')
ANALYTICS_FILE = os.path.join(PRODUCTIVITY_DIR, 'analytics.json')
DAILY_STATS_FILE = os.path.join(PRODUCTIVITY_DIR, 'daily_stats.json')
CONFIG_FILE = os.path.join(PRODUCTIVITY_DIR, 'config.json')

# Ensure directories exist
os.makedirs(PRODUCTIVITY_DIR, exist_ok=True)

class ProductivityManager:
    def __init__(self):
        self.data_lock = threading.Lock()
        self.config = self.load_config()
        self.goals = self.load_goals()
        self.achievements = self.load_achievements()
        self.habits = self.load_habits()
        self.notes = self.load_notes()
        self.analytics = self.load_analytics()
        self.daily_stats = self.load_daily_stats()
        self.screen_time_tracker = ScreenTimeTracker(self.analytics)

    def safe_file_operation(self, operation, file_path, data=None):
        """Safely perform file operations with locking"""
        try:
            with self.data_lock:
                if operation == 'read':
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                            return json.load(f)
                    return {}
                elif operation == 'write' and data is not None:
                    temp_file = f"{file_path}.tmp"
                    with open(temp_file, 'w') as f:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        json.dump(data, f, indent=2, default=str)
                    os.replace(temp_file, file_path)
                    return True
        except (json.JSONDecodeError, IOError, OSError) as e:
            self.send_notification("File Error", f"Error with {os.path.basename(file_path)}: {e}", "critical")
            return {} if operation == 'read' else False

    def load_config(self):
        """Load configuration with defaults"""
        defaults = {
            "notifications_enabled": True,
            "break_reminder_interval": 30,  # minutes
            "daily_goal_reset_time": "00:00",
            "screen_time_tracking": True,
            "achievement_notifications": True,
            "habit_reminder_time": "20:00"
        }

        config = self.safe_file_operation('read', CONFIG_FILE)
        for key, value in defaults.items():
            if key not in config:
                config[key] = value

        self.safe_file_operation('write', CONFIG_FILE, config)
        return config

    def load_goals(self):
        """Load goals data"""
        data = self.safe_file_operation('read', GOALS_FILE)
        if not data:
            data = {
                "goals": [],
                "categories": ["Work", "Personal", "Health", "Learning", "Finance"],
                "next_id": 1
            }
            self.safe_file_operation('write', GOALS_FILE, data)
        return data

    def load_achievements(self):
        """Load achievements data"""
        data = self.safe_file_operation('read', ACHIEVEMENTS_FILE)
        if not data:
            data = {
                "unlocked": [],
                "points": 0,
                "level": 1,
                "available_achievements": self.get_default_achievements()
            }
            self.safe_file_operation('write', ACHIEVEMENTS_FILE, data)
        return data

    def load_habits(self):
        """Load habits data"""
        data = self.safe_file_operation('read', HABITS_FILE)
        if not data:
            data = {
                "habits": [],
                "next_id": 1
            }
            self.safe_file_operation('write', HABITS_FILE, data)
        return data

    def load_notes(self):
        """Load notes data"""
        data = self.safe_file_operation('read', NOTES_FILE)
        if not data:
            data = {
                "notes": [],
                "categories": ["General", "Ideas", "Tasks", "Reminders"],
                "next_id": 1
            }
            self.safe_file_operation('write', NOTES_FILE, data)
        return data

    def load_analytics(self):
        """Load analytics data"""
        data = self.safe_file_operation('read', ANALYTICS_FILE)
        if not data:
            data = {
                "screen_time": {},
                "application_usage": {},
                "productivity_score": {},
                "focus_sessions": [],
                "break_sessions": []
            }
            self.safe_file_operation('write', ANALYTICS_FILE, data)
        return data

    def load_daily_stats(self):
        """Load daily statistics"""
        data = self.safe_file_operation('read', DAILY_STATS_FILE)
        if not data:
            data = {
                "date": str(date.today()),
                "goals_completed": 0,
                "habits_completed": 0,
                "focus_time": 0,
                "break_time": 0,
                "productivity_score": 0
            }
            self.safe_file_operation('write', DAILY_STATS_FILE, data)
        return data

    def get_default_achievements(self):
        """Get default achievement definitions"""
        return {
            "first_goal": {
                "name": "Goal Setter",
                "description": "Create your first goal",
                "points": 10,
                "icon": "🎯",
                "unlocked": False
            },
            "goal_streak_7": {
                "name": "Week Warrior",
                "description": "Complete goals for 7 days straight",
                "points": 50,
                "icon": "🔥",
                "unlocked": False
            },
            "habit_master": {
                "name": "Habit Master",
                "description": "Maintain a habit for 30 days",
                "points": 100,
                "icon": "👑",
                "unlocked": False
            },
            "focused_mind": {
                "name": "Focused Mind",
                "description": "Complete 5 focus sessions in a day",
                "points": 25,
                "icon": "🧠",
                "unlocked": False
            },
            "note_taker": {
                "name": "Note Taker",
                "description": "Create 50 notes",
                "points": 30,
                "icon": "📝",
                "unlocked": False
            },
            "productivity_guru": {
                "name": "Productivity Guru",
                "description": "Reach level 10",
                "points": 200,
                "icon": "🏆",
                "unlocked": False
            }
        }

    def send_notification(self, title, message, urgency="normal"):
        """Send desktop notification"""
        if not self.config.get("notifications_enabled", True):
            return

        try:
            subprocess.Popen(['notify-send', '-u', urgency, '-a', 'Productivity Manager', title, message],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def check_daily_reset(self):
        """Check if we need to reset daily stats"""
        today = str(date.today())
        if self.daily_stats.get("date") != today:
            self.daily_stats = {
                "date": today,
                "goals_completed": 0,
                "habits_completed": 0,
                "focus_time": 0,
                "break_time": 0,
                "productivity_score": 0
            }
            self.safe_file_operation('write', DAILY_STATS_FILE, self.daily_stats)

    def add_goal(self, title, description="", category="Personal", deadline=None, target_value=1, current_value=0):
        """Add a new goal"""
        goal = {
            "id": self.goals["next_id"],
            "title": title,
            "description": description,
            "category": category,
            "created_date": str(date.today()),
            "deadline": deadline,
            "target_value": target_value,
            "current_value": current_value,
            "completed": False,
            "completed_date": None
        }

        self.goals["goals"].append(goal)
        self.goals["next_id"] += 1
        self.safe_file_operation('write', GOALS_FILE, self.goals)

        # Check for first goal achievement
        if len(self.goals["goals"]) == 1:
            self.unlock_achievement("first_goal")

        self.send_notification("Goal Added", f"New goal: {title}")
        return True

    def update_goal_progress(self, goal_id, progress):
        """Update goal progress"""
        for goal in self.goals["goals"]:
            if goal["id"] == goal_id:
                goal["current_value"] = min(progress, goal["target_value"])

                if goal["current_value"] >= goal["target_value"] and not goal["completed"]:
                    goal["completed"] = True
                    goal["completed_date"] = str(date.today())
                    self.daily_stats["goals_completed"] += 1
                    self.safe_file_operation('write', DAILY_STATS_FILE, self.daily_stats)
                    self.send_notification("Goal Completed! 🎉", f"Congratulations on completing: {goal['title']}")
                    self.add_points(20)

                self.safe_file_operation('write', GOALS_FILE, self.goals)
                return True
        return False

    def add_habit(self, name, description="", frequency="daily", reminder_time="20:00"):
        """Add a new habit"""
        habit = {
            "id": self.habits["next_id"],
            "name": name,
            "description": description,
            "frequency": frequency,  # daily, weekly, custom
            "reminder_time": reminder_time,
            "created_date": str(date.today()),
            "streak": 0,
            "longest_streak": 0,
            "total_completions": 0,
            "completion_dates": [],
            "active": True
        }

        self.habits["habits"].append(habit)
        self.habits["next_id"] += 1
        self.safe_file_operation('write', HABITS_FILE, self.habits)

        self.send_notification("Habit Added", f"New habit: {name}")
        return True

    def complete_habit(self, habit_id):
        """Mark habit as completed for today"""
        today = str(date.today())

        for habit in self.habits["habits"]:
            if habit["id"] == habit_id:
                if today not in habit["completion_dates"]:
                    habit["completion_dates"].append(today)
                    habit["total_completions"] += 1
                    habit["streak"] = self.calculate_habit_streak(habit["completion_dates"])
                    habit["longest_streak"] = max(habit["longest_streak"], habit["streak"])

                    self.daily_stats["habits_completed"] += 1
                    self.safe_file_operation('write', DAILY_STATS_FILE, self.daily_stats)

                    # Check for achievements
                    if habit["streak"] >= 30:
                        self.unlock_achievement("habit_master")

                    self.send_notification("Habit Completed! ✅", f"{habit['name']} - {habit['streak']} day streak!")
                    self.add_points(5)

                self.safe_file_operation('write', HABITS_FILE, self.habits)
                return True
        return False

    def calculate_habit_streak(self, completion_dates):
        """Calculate current streak for a habit"""
        if not completion_dates:
            return 0

        completion_dates.sort(reverse=True)
        today = date.today()
        streak = 0

        for i, date_str in enumerate(completion_dates):
            completion_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            expected_date = today - timedelta(days=i)

            if completion_date == expected_date:
                streak += 1
            else:
                break

        return streak

    def add_note(self, title, content, category="General"):
        """Add a new note"""
        note = {
            "id": self.notes["next_id"],
            "title": title,
            "content": content,
            "category": category,
            "created_date": str(datetime.now()),
            "modified_date": str(datetime.now()),
            "tags": [],
            "archived": False
        }

        self.notes["notes"].append(note)
        self.notes["next_id"] += 1
        self.safe_file_operation('write', NOTES_FILE, self.notes)

        # Check for note achievement
        active_notes = [n for n in self.notes["notes"] if not n["archived"]]
        if len(active_notes) >= 50:
            self.unlock_achievement("note_taker")

        self.send_notification("Note Added", f"New note: {title}")
        return True

    def unlock_achievement(self, achievement_id):
        """Unlock an achievement"""
        if achievement_id in self.achievements["available_achievements"]:
            achievement = self.achievements["available_achievements"][achievement_id]
            if not achievement["unlocked"]:
                achievement["unlocked"] = True
                self.achievements["unlocked"].append({
                    "id": achievement_id,
                    "unlocked_date": str(datetime.now()),
                    **achievement
                })

                self.add_points(achievement["points"])

                if self.config.get("achievement_notifications", True):
                    self.send_notification(
                        f"Achievement Unlocked! {achievement['icon']}",
                        f"{achievement['name']}: {achievement['description']}"
                    )

                self.safe_file_operation('write', ACHIEVEMENTS_FILE, self.achievements)

    def add_points(self, points):
        """Add points and check for level up"""
        old_level = self.achievements["level"]
        self.achievements["points"] += points

        # Calculate new level (every 100 points = 1 level)
        new_level = (self.achievements["points"] // 100) + 1

        if new_level > old_level:
            self.achievements["level"] = new_level
            self.send_notification("Level Up! 🚀", f"You've reached level {new_level}!")

            if new_level >= 10:
                self.unlock_achievement("productivity_guru")

        self.safe_file_operation('write', ACHIEVEMENTS_FILE, self.achievements)

    def start_focus_session(self, duration_minutes=25, session_name="Focus Session"):
        """Start a new focus session via timer manager"""
        try:
            # Use timer manager for focus sessions
            subprocess.Popen(['python3', os.path.expanduser('~/.config/waybar/timer-manager.py'),
                             'start-focus', '--duration', str(duration_minutes), '--name', session_name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            self.send_notification("Focus Error", f"Failed to start focus session: {e}", "critical")
            return False

    def end_focus_session(self, session_id=None, interrupted=False):
        """End the current focus session via timer manager"""
        try:
            # Use timer manager to stop current timer
            subprocess.Popen(['python3', os.path.expanduser('~/.config/waybar/timer-manager.py'),
                             'stop'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            self.send_notification("Focus Error", f"Failed to end focus session: {e}", "critical")
            return False

    def get_current_focus_session(self):
        """Get current active focus session from timer manager"""
        try:
            # Check timer manager status
            result = subprocess.run(['python3', os.path.expanduser('~/.config/waybar/timer-manager.py'), 'status'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                status_data = json.loads(result.stdout)
                # Check if current timer is a focus session
                timer_state_file = os.path.join(os.path.expanduser('~/.cache/waybar'), 'timer-manager.json')
                if os.path.exists(timer_state_file):
                    with open(timer_state_file, 'r') as f:
                        timer_state = json.load(f)
                    if timer_state.get("timer_type") == "focus" and timer_state.get("mode") == "timer":
                        return {
                            "name": timer_state.get("timer_name", "Focus Session"),
                            "elapsed_minutes": (time.time() - timer_state.get("start_time", 0) - timer_state.get("total_pause_time", 0)) / 60,
                            "planned_duration": timer_state.get("duration", 0) / 60
                        }
            return None
        except Exception:
            return None

    def start_break_session(self, duration_minutes=5, break_type="Short Break"):
        """Start a break session via timer manager"""
        try:
            # Use timer manager for break sessions
            subprocess.Popen(['python3', os.path.expanduser('~/.config/waybar/timer-manager.py'),
                             'start-break', '--duration', str(duration_minutes), '--name', break_type],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            self.send_notification("Break Error", f"Failed to start break session: {e}", "critical")
            return False

    def end_break_session(self):
        """End the current break session via timer manager"""
        return self.end_focus_session()  # Same method - stop current timer

    def get_current_break_session(self):
        """Get current active break session from timer manager"""
        try:
            # Check timer manager status
            timer_state_file = os.path.join(os.path.expanduser('~/.cache/waybar'), 'timer-manager.json')
            if os.path.exists(timer_state_file):
                with open(timer_state_file, 'r') as f:
                    timer_state = json.load(f)
                if timer_state.get("timer_type") == "break" and timer_state.get("mode") == "timer":
                    return {
                        "type": timer_state.get("timer_name", "Break"),
                        "elapsed_minutes": (time.time() - timer_state.get("start_time", 0) - timer_state.get("total_pause_time", 0)) / 60,
                        "planned_duration": timer_state.get("duration", 0) / 60
                    }
            return None
        except Exception:
            return None

    def get_status(self):
        """Get current status for waybar"""
        self.check_daily_reset()
        self.screen_time_tracker.update()

        # Calculate various metrics
        active_goals = len([g for g in self.goals["goals"] if not g["completed"]])
        active_habits = len([h for h in self.habits["habits"] if h["active"]])
        total_notes = len([n for n in self.notes["notes"] if not n["archived"]])

        # Check for urgent items
        urgent_count = 0

        # Check for goals with deadlines today or overdue
        today = date.today()
        for goal in self.goals["goals"]:
            if not goal["completed"] and goal["deadline"]:
                deadline = datetime.strptime(goal["deadline"], "%Y-%m-%d").date()
                if deadline <= today:
                    urgent_count += 1

        # Check for habits due today
        today_str = str(today)
        for habit in self.habits["habits"]:
            if habit["active"] and today_str not in habit["completion_dates"]:
                urgent_count += 1

        # Create display text
        level = self.achievements["level"]

        if urgent_count > 0:
            text = f"🔥 {urgent_count}"
            css_class = "productivity-urgent"
        elif active_goals > 0 or active_habits > 0:
            text = f"⚡ L{level}"
            css_class = "productivity-active"
        else:
            text = f"✨ L{level}"
            css_class = "productivity-idle"

        # Check for active focus/break sessions
        current_focus = self.get_current_focus_session()
        current_break = self.get_current_break_session()

        # Create tooltip
        tooltip = f"Productivity Manager - Level {level}\n"
        tooltip += f"Points: {self.achievements['points']}\n\n"

        # Show active sessions first
        if current_focus:
            elapsed = current_focus["elapsed_minutes"]
            planned = current_focus["planned_duration"]
            tooltip += f"🧠 Focus: {elapsed:.1f}/{planned}min ({current_focus['name']})\n"

        if current_break:
            elapsed = current_break["elapsed_minutes"]
            planned = current_break["planned_duration"]
            tooltip += f"☕ Break: {elapsed:.1f}/{planned}min ({current_break['type']})\n"

        if current_focus or current_break:
            tooltip += "\n"

        tooltip += f"📊 Today's Stats:\n"
        tooltip += f"Goals completed: {self.daily_stats['goals_completed']}\n"
        tooltip += f"Habits completed: {self.daily_stats['habits_completed']}\n"
        tooltip += f"Focus time: {self.daily_stats['focus_time']}min\n"
        tooltip += f"Break time: {self.daily_stats['break_time']}min\n\n"
        tooltip += f"📈 Active Items:\n"
        tooltip += f"Goals: {active_goals}\n"
        tooltip += f"Habits: {active_habits}\n"
        tooltip += f"Notes: {total_notes}\n"

        if urgent_count > 0:
            tooltip += f"\n⚠️ {urgent_count} urgent items need attention!"

        return {
            "text": text,
            "tooltip": tooltip,
            "class": css_class
        }

class ScreenTimeTracker:
    def __init__(self, analytics_data):
        self.analytics = analytics_data
        self.last_update = time.time()
        self.current_window = self.get_active_window()

    def get_active_window(self):
        """Get currently active window information"""
        try:
            # Try hyprctl first (for Hyprland)
            result = subprocess.run(['hyprctl', 'activewindow', '-j'],
                                  capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return {
                "app": data.get("class", "Unknown"),
                "title": data.get("title", "Unknown")
            }
        except:
            try:
                # Fallback to xprop
                result = subprocess.run(['xprop', '-id', '$(xprop -root _NET_ACTIVE_WINDOW | cut -d\' \' -f5)',
                                       'WM_CLASS', '_NET_WM_NAME'],
                                      capture_output=True, text=True, check=True)
                # Parse xprop output (simplified)
                return {"app": "Unknown", "title": "Unknown"}
            except:
                return {"app": "Unknown", "title": "Unknown"}

    def update(self):
        """Update screen time tracking"""
        current_time = time.time()
        elapsed = current_time - self.last_update

        if elapsed > 60:  # Only update if more than 1 minute has passed
            return

        today = str(date.today())
        current_window = self.get_active_window()

        # Initialize today's data if needed
        if today not in self.analytics["screen_time"]:
            self.analytics["screen_time"][today] = {}
            self.analytics["application_usage"][today] = {}

        # Update screen time
        app_name = current_window["app"]
        if app_name not in self.analytics["application_usage"][today]:
            self.analytics["application_usage"][today][app_name] = 0

        self.analytics["application_usage"][today][app_name] += elapsed / 60  # Convert to minutes

        self.last_update = current_time
        self.current_window = current_window

def show_main_menu():
    """Show main productivity menu"""
    options = [
        "🎯 Goals Manager",
        "📋 Habits Tracker",

        "📝 Notes Manager",
        "📊 Analytics View",
        "🏆 Achievements",
        "⚙️ Settings",
        "💡 Daily Summary"
    ]

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Productivity Manager',
                                '-theme-str', 'window {width: 350px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Goals Manager" in selection:
                show_goals_menu()
            elif "Habits Tracker" in selection:
                show_habits_menu()

            elif "Notes Manager" in selection:
                show_notes_menu()
            elif "Analytics View" in selection:
                show_analytics()
            elif "Achievements" in selection:
                show_achievements()
            elif "Settings" in selection:
                show_settings()
            elif "Daily Summary" in selection:
                show_daily_summary()

    except Exception as e:
        pm = ProductivityManager()
        pm.send_notification("Menu Error", f"Failed to show menu: {e}", "critical")

def show_goals_menu():
    """Show goals management menu"""
    pm = ProductivityManager()

    active_goals = [g for g in pm.goals["goals"] if not g["completed"]]
    completed_goals = [g for g in pm.goals["goals"] if g["completed"]]

    options = [
        "➕ Add New Goal",
        "🔍 Search Goals",
        f"📂 Browse by Category ({len(set(g['category'] for g in pm.goals['goals']))} categories)",
        f"✅ Completed Goals ({len(completed_goals)})"
    ]

    if active_goals:
        options.append("──────────────────")
        options.append(f"📊 Active Goals ({len(active_goals)}):")

        for goal in sorted(active_goals, key=lambda x: x.get("deadline") or "9999-12-31"):
            status = "🎯"
            progress = f"{goal['current_value']}/{goal['target_value']}"
            deadline_info = ""

            if goal["deadline"]:
                deadline = datetime.strptime(goal["deadline"], "%Y-%m-%d").date()
                days_left = (deadline - date.today()).days
                if days_left < 0:
                    deadline_info = " (OVERDUE)"
                    status = "🔥"
                elif days_left == 0:
                    deadline_info = " (DUE TODAY)"
                    status = "⚠️"
                elif days_left <= 3:
                    deadline_info = f" ({days_left}d left)"

        options.append(f"{status} {goal['title']} [{progress}]{deadline_info}")

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Goals Manager',
                                '-theme-str', 'window {width: 600px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Add New Goal" in selection:
                show_add_goal_dialog()
            elif "Search Goals" in selection:
                show_goals_search()
            elif "Browse by Category" in selection:
                show_goals_by_category()
            elif "Completed Goals" in selection:
                show_completed_goals()
            else:
                # Find and manage selected goal
                for goal in pm.goals["goals"]:
                    if goal["title"] in selection:
                        show_goal_actions(goal)
                        break

    except Exception as e:
        pm.send_notification("Goals Error", f"Failed to show goals menu: {e}", "critical")

def show_add_goal_dialog():
    """Show dialog to add new goal"""
    pm = ProductivityManager()

    try:
        # Get goal title
        result = subprocess.run(['zenity', '--entry', '--title=New Goal',
                                '--text=Enter goal title:', '--width=400'],
                               capture_output=True, text=True)

        if result.returncode != 0:
            return

        title = result.stdout.strip()
        if not title:
            return

        # Get description
        desc_result = subprocess.run(['zenity', '--entry', '--title=Goal Description',
                                     '--text=Enter description (optional):'],
                                    capture_output=True, text=True)
        description = desc_result.stdout.strip() if desc_result.returncode == 0 else ""

        # Get category
        cat_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Select Category',
                                    '-theme-str', 'window {width: 300px;}'],
                                   input='\n'.join(pm.goals["categories"]), text=True,
                                   capture_output=True)
        category = cat_result.stdout.strip() if cat_result.returncode == 0 else "Personal"

        # Get target value
        target_result = subprocess.run(['zenity', '--entry', '--title=Target Value',
                                       '--text=Enter target value (default: 1):',
                                       '--entry-text=1'],
                                      capture_output=True, text=True)
        try:
            target_value = int(target_result.stdout.strip()) if target_result.returncode == 0 else 1
        except ValueError:
            target_value = 1

        # Get deadline (optional)
        deadline_result = subprocess.run(['zenity', '--calendar', '--title=Goal Deadline',
                                         '--text=Select deadline (optional):'],
                                        capture_output=True, text=True)
        deadline = None
        if deadline_result.returncode == 0:
            # zenity calendar returns MM/DD/YYYY format
            try:
                date_parts = deadline_result.stdout.strip().split('/')
                deadline = f"{date_parts[2]}-{date_parts[0].zfill(2)}-{date_parts[1].zfill(2)}"
            except:
                deadline = None

        pm.add_goal(title, description, category, deadline, target_value, 0)

    except Exception as e:
        pm.send_notification("Goal Error", f"Failed to create goal: {e}", "critical")

def show_goal_actions(goal):
    """Show actions for a specific goal"""
    pm = ProductivityManager()

    options = [
        "📈 Update Progress",
        "✏️ Edit Goal",
        "🗑️ Delete Goal"
    ]

    if not goal["completed"]:
        options.insert(0, "✅ Mark Complete")

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'Goal: {goal["title"]}',
                                '-theme-str', 'window {width: 300px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Mark Complete" in selection:
                pm.update_goal_progress(goal["id"], goal["target_value"])
            elif "Update Progress" in selection:
                show_update_progress_dialog(goal)
            elif "Edit Goal" in selection:
                show_edit_goal_dialog(goal)
            elif "Delete Goal" in selection:
                show_delete_goal_confirmation(goal)

    except Exception as e:
        pm.send_notification("Goal Action Error", f"Failed to perform action: {e}", "critical")

def show_update_progress_dialog(goal):
    """Show dialog to update goal progress"""
    pm = ProductivityManager()

    try:
        result = subprocess.run(['zenity', '--scale', '--title=Update Progress',
                                f'--text=Update progress for: {goal["title"]}',
                                f'--min-value=0', f'--max-value={goal["target_value"]}',
                                f'--value={goal["current_value"]}'],
                               capture_output=True, text=True)

        if result.returncode == 0:
            new_progress = int(result.stdout.strip())
            pm.update_goal_progress(goal["id"], new_progress)

    except Exception as e:
        pm.send_notification("Progress Error", f"Failed to update progress: {e}", "critical")

def show_habits_menu():
    """Show habits management menu"""
    pm = ProductivityManager()

    options = ["➕ Add New Habit"]

    today = str(date.today())
    for habit in pm.habits["habits"]:
        if not habit["active"]:
            continue

        completed_today = today in habit["completion_dates"]
        status = "✅" if completed_today else "⭕"
        streak_info = f"🔥{habit['streak']}" if habit['streak'] > 0 else ""

        options.append(f"{status} {habit['name']} {streak_info}")

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Habits Tracker',
                                '-theme-str', 'window {width: 400px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Add New Habit" in selection:
                show_add_habit_dialog()
            else:
                # Find and manage selected habit
                for habit in pm.habits["habits"]:
                    if habit["name"] in selection:
                        show_habit_actions(habit)
                        break

    except Exception as e:
        pm.send_notification("Habits Error", f"Failed to show habits menu: {e}", "critical")

def show_add_habit_dialog():
    """Show dialog to add new habit"""
    pm = ProductivityManager()

    try:
        # Get habit name
        result = subprocess.run(['zenity', '--entry', '--title=New Habit',
                                '--text=Enter habit name:', '--width=400'],
                               capture_output=True, text=True)

        if result.returncode != 0:
            return

        name = result.stdout.strip()
        if not name:
            return

        # Get description
        desc_result = subprocess.run(['zenity', '--entry', '--title=Habit Description',
                                     '--text=Enter description (optional):'],
                                    capture_output=True, text=True)
        description = desc_result.stdout.strip() if desc_result.returncode == 0 else ""

        # Get frequency
        freq_options = ["daily", "weekly", "custom"]
        freq_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Select Frequency',
                                     '-theme-str', 'window {width: 300px;}'],
                                    input='\n'.join(freq_options), text=True,
                                    capture_output=True)
        frequency = freq_result.stdout.strip() if freq_result.returncode == 0 else "daily"

        pm.add_habit(name, description, frequency)

    except Exception as e:
        pm.send_notification("Habit Error", f"Failed to create habit: {e}", "critical")

def show_habit_actions(habit):
    """Show actions for a specific habit"""
    pm = ProductivityManager()
    today = str(date.today())
    completed_today = today in habit["completion_dates"]

    options = []

    if not completed_today:
        options.append("✅ Mark Complete")

    options.extend([
        "📊 View Stats",
        "✏️ Edit Habit",
        "🗑️ Delete Habit"
    ])

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'Habit: {habit["name"]}',
                                '-theme-str', 'window {width: 300px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Mark Complete" in selection:
                pm.complete_habit(habit["id"])
            elif "View Stats" in selection:
                show_habit_stats(habit)
            elif "Edit Habit" in selection:
                show_edit_habit_dialog(habit)
            elif "Delete Habit" in selection:
                show_delete_habit_confirmation(habit)

    except Exception as e:
        pm.send_notification("Habit Action Error", f"Failed to perform action: {e}", "critical")

def show_habit_stats(habit):
    """Show habit statistics"""
    success_rate = 0
    if habit["total_completions"] > 0:
        days_since_created = (date.today() - datetime.strptime(habit["created_date"], "%Y-%m-%d").date()).days + 1
        success_rate = (habit["total_completions"] / days_since_created) * 100

    stats_text = f"""Habit Statistics: {habit['name']}

Current Streak: {habit['streak']} days
Longest Streak: {habit['longest_streak']} days
Total Completions: {habit['total_completions']}
Success Rate: {success_rate:.1f}%
Created: {habit['created_date']}"""

    try:
        subprocess.run(['zenity', '--info', '--title=Habit Statistics',
                       f'--text={stats_text}', '--width=400'],
                      capture_output=True)
    except Exception:
        pass

def show_notes_menu():
    """Show comprehensive notes management menu"""
    pm = ProductivityManager()

    active_notes = [n for n in pm.notes["notes"] if not n["archived"]]
    archived_notes = [n for n in pm.notes["notes"] if n["archived"]]

    options = [
        "➕ Add New Note",
        "🔍 Search Notes",
        f"📂 Browse by Category ({len(set(n['category'] for n in active_notes))} categories)",
        f"📋 View All Notes ({len(active_notes)} active)",
        f"🗃️ Archived Notes ({len(archived_notes)})"
    ]

    # Show recent notes (last 5)
    if active_notes:
        options.append("──────────────────")
        recent_notes = sorted(active_notes, key=lambda x: x["modified_date"], reverse=True)[:5]
        for note in recent_notes:
            preview = note["content"][:50] + "..." if len(note["content"]) > 50 else note["content"]
            options.append(f"📝 {note['title']} - {preview}")

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Notes Manager',
                                '-theme-str', 'window {width: 600px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Add New Note" in selection:
                show_add_note_dialog()
            elif "Search Notes" in selection:
                show_notes_search()
            elif "Browse by Category" in selection:
                show_notes_by_category()
            elif "View All Notes" in selection:
                show_all_notes()
            elif "Archived Notes" in selection:
                show_archived_notes()
            elif selection.startswith("📝"):
                # Find and show selected note
                note_title = selection.split(" - ")[0].replace("📝 ", "")
                for note in active_notes:
                    if note["title"] == note_title:
                        show_note_actions(note)
                        break

    except Exception as e:
        pm.send_notification("Notes Error", f"Failed to show notes menu: {e}", "critical")

def show_add_note_dialog():
    """Show dialog to add new note"""
    pm = ProductivityManager()

    try:
        # Get note title
        title_result = subprocess.run(['zenity', '--entry', '--title=New Note',
                                      '--text=Enter note title:', '--width=400'],
                                     capture_output=True, text=True)

        if title_result.returncode != 0:
            return

        title = title_result.stdout.strip()
        if not title:
            return

        # Get note content
        content_result = subprocess.run(['zenity', '--text-info', '--editable',
                                        '--title=Note Content',
                                        '--width=500', '--height=300'],
                                       capture_output=True, text=True)

        content = content_result.stdout.strip() if content_result.returncode == 0 else ""

        # Get category
        cat_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Select Category',
                                    '-theme-str', 'window {width: 300px;}'],
                                   input='\n'.join(pm.notes["categories"]), text=True,
                                   capture_output=True)
        category = cat_result.stdout.strip() if cat_result.returncode == 0 else "General"

        pm.add_note(title, content, category)

    except Exception as e:
        pm.send_notification("Note Error", f"Failed to create note: {e}", "critical")

def show_notes_search():
    """Search notes by title or content"""
    pm = ProductivityManager()

    try:
        # Get search term
        search_result = subprocess.run(['zenity', '--entry', '--title=Search Notes',
                                       '--text=Enter search term:', '--width=400'],
                                      capture_output=True, text=True)

        if search_result.returncode != 0:
            return

        search_term = search_result.stdout.strip().lower()
        if not search_term:
            return

        # Search in active notes
        active_notes = [n for n in pm.notes["notes"] if not n["archived"]]
        matching_notes = []

        for note in active_notes:
            if (search_term in note["title"].lower() or
                search_term in note["content"].lower() or
                search_term in note["category"].lower() or
                any(search_term in tag.lower() for tag in note.get("tags", []))):
                matching_notes.append(note)

        if not matching_notes:
            subprocess.run(['zenity', '--info', '--title=Search Results',
                           '--text=No notes found matching your search.'],
                          capture_output=True)
            return

        # Show search results
        options = []
        for note in matching_notes:
            preview = note["content"][:60] + "..." if len(note["content"]) > 60 else note["content"]
            options.append(f"📝 {note['title']} [{note['category']}]\n   {preview}")

        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'Search Results ({len(matching_notes)} found)',
                                '-theme-str', 'window {width: 700px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()
            # Find selected note
            note_title = selection.split(" [")[0].replace("📝 ", "")
            for note in matching_notes:
                if note["title"] == note_title:
                    show_note_actions(note)
                    break

    except Exception as e:
        pm.send_notification("Search Error", f"Failed to search notes: {e}", "critical")

def show_notes_by_category():
    """Browse notes by category"""
    pm = ProductivityManager()

    active_notes = [n for n in pm.notes["notes"] if not n["archived"]]
    categories = {}

    for note in active_notes:
        category = note["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(note)

    if not categories:
        subprocess.run(['zenity', '--info', '--title=Browse Categories',
                       '--text=No notes available.'],
                      capture_output=True)
        return

    try:
        # Show categories
        category_options = [f"📁 {cat} ({len(notes)} notes)" for cat, notes in categories.items()]

        cat_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Select Category',
                                    '-theme-str', 'window {width: 400px;}'],
                                   input='\n'.join(category_options), text=True,
                                   capture_output=True)

        if cat_result.returncode != 0:
            return

        selected_category = cat_result.stdout.strip().split(" (")[0].replace("📁 ", "")

        # Show notes in selected category
        category_notes = categories[selected_category]
        note_options = []

        for note in sorted(category_notes, key=lambda x: x["modified_date"], reverse=True):
            preview = note["content"][:50] + "..." if len(note["content"]) > 50 else note["content"]
            note_options.append(f"📝 {note['title']}\n   {preview}")

        note_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'{selected_category} Notes',
                                     '-theme-str', 'window {width: 600px;}'],
                                    input='\n'.join(note_options), text=True,
                                    capture_output=True)

        if note_result.returncode == 0:
            selection = note_result.stdout.strip()
            note_title = selection.split("\n")[0].replace("📝 ", "")
            for note in category_notes:
                if note["title"] == note_title:
                    show_note_actions(note)
                    break

    except Exception as e:
        pm.send_notification("Category Error", f"Failed to browse categories: {e}", "critical")

def show_all_notes():
    """Show all active notes"""
    pm = ProductivityManager()

    active_notes = [n for n in pm.notes["notes"] if not n["archived"]]

    if not active_notes:
        subprocess.run(['zenity', '--info', '--title=All Notes',
                       '--text=No notes available.'],
                      capture_output=True)
        return

    try:
        options = []
        for note in sorted(active_notes, key=lambda x: x["modified_date"], reverse=True):
            preview = note["content"][:50] + "..." if len(note["content"]) > 50 else note["content"]
            modified = datetime.fromisoformat(note["modified_date"]).strftime("%m/%d %H:%M")
            options.append(f"📝 {note['title']} [{note['category']}] - {modified}\n   {preview}")

        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'All Notes ({len(active_notes)})',
                                '-theme-str', 'window {width: 700px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()
            note_title = selection.split(" [")[0].replace("📝 ", "")
            for note in active_notes:
                if note["title"] == note_title:
                    show_note_actions(note)
                    break

    except Exception as e:
        pm.send_notification("Notes Error", f"Failed to show all notes: {e}", "critical")

def show_archived_notes():
    """Show archived notes"""
    pm = ProductivityManager()

    archived_notes = [n for n in pm.notes["notes"] if n["archived"]]

    if not archived_notes:
        subprocess.run(['zenity', '--info', '--title=Archived Notes',
                       '--text=No archived notes.'],
                      capture_output=True)
        return

    try:
        options = []
        for note in sorted(archived_notes, key=lambda x: x["modified_date"], reverse=True):
            preview = note["content"][:50] + "..." if len(note["content"]) > 50 else note["content"]
            modified = datetime.fromisoformat(note["modified_date"]).strftime("%m/%d %H:%M")
            options.append(f"🗃️ {note['title']} [{note['category']}] - {modified}\n   {preview}")

        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'Archived Notes ({len(archived_notes)})',
                                '-theme-str', 'window {width: 700px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()
            note_title = selection.split(" [")[0].replace("🗃️ ", "")
            for note in archived_notes:
                if note["title"] == note_title:
                    show_note_actions(note)
                    break

    except Exception as e:
        pm.send_notification("Archived Notes Error", f"Failed to show archived notes: {e}", "critical")

def show_note_actions(note):
    """Show actions for a specific note"""
    pm = ProductivityManager()

    options = [
        "👁️ View Full Note",
        "✏️ Edit Note",
        "🏷️ Manage Tags",
        "📁 Change Category"
    ]

    if note["archived"]:
        options.append("📤 Unarchive Note")
    else:
        options.append("🗃️ Archive Note")

    options.append("🗑️ Delete Note")

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'Note: {note["title"]}',
                                '-theme-str', 'window {width: 350px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "View Full Note" in selection:
                show_full_note(note)
            elif "Edit Note" in selection:
                show_edit_note_dialog(note)
            elif "Manage Tags" in selection:
                show_manage_tags_dialog(note)
            elif "Change Category" in selection:
                show_change_category_dialog(note)
            elif "Archive Note" in selection:
                archive_note(note)
            elif "Unarchive Note" in selection:
                unarchive_note(note)
            elif "Delete Note" in selection:
                show_delete_note_confirmation(note)

    except Exception as e:
        pm.send_notification("Note Action Error", f"Failed to perform action: {e}", "critical")

def show_full_note(note):
    """Display full note content"""
    tags_str = ", ".join(note.get("tags", []))
    created = datetime.fromisoformat(note["created_date"]).strftime("%B %d, %Y %H:%M")
    modified = datetime.fromisoformat(note["modified_date"]).strftime("%B %d, %Y %H:%M")

    full_text = f"""Title: {note['title']}
Category: {note['category']}
Tags: {tags_str}
Created: {created}
Modified: {modified}
Status: {'Archived' if note['archived'] else 'Active'}

Content:
{note['content']}"""

    try:
        subprocess.run(['zenity', '--text-info', '--title=View Note',
                       '--width=600', '--height=500'],
                      input=full_text, text=True,
                      capture_output=True)
    except Exception:
        pass

def show_edit_note_dialog(note):
    """Edit existing note"""
    pm = ProductivityManager()

    try:
        # Edit title
        title_result = subprocess.run(['zenity', '--entry', '--title=Edit Note Title',
                                      '--text=Enter new title:',
                                      f'--entry-text={note["title"]}'],
                                     capture_output=True, text=True)

        if title_result.returncode == 0:
            new_title = title_result.stdout.strip()
            if new_title:
                note["title"] = new_title

        # Edit content
        content_result = subprocess.run(['zenity', '--text-info', '--editable',
                                        '--title=Edit Note Content',
                                        '--width=500', '--height=300'],
                                       input=note["content"], text=True,
                                       capture_output=True)

        if content_result.returncode == 0:
            note["content"] = content_result.stdout.strip()

        note["modified_date"] = str(datetime.now())
        pm.safe_file_operation('write', NOTES_FILE, pm.notes)
        pm.send_notification("Note Updated", f"Updated: {note['title']}")

    except Exception as e:
        pm.send_notification("Edit Error", f"Failed to edit note: {e}", "critical")

def show_manage_tags_dialog(note):
    """Manage note tags"""
    pm = ProductivityManager()

    current_tags = note.get("tags", [])

    try:
        # Show current tags and add option
        options = ["➕ Add New Tag"]
        if current_tags:
            options.append("──────────────")
            for tag in current_tags:
                options.append(f"🏷️ {tag} (click to remove)")

        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Manage Tags',
                                '-theme-str', 'window {width: 300px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Add New Tag" in selection:
                tag_result = subprocess.run(['zenity', '--entry', '--title=Add Tag',
                                           '--text=Enter new tag:'],
                                          capture_output=True, text=True)

                if tag_result.returncode == 0:
                    new_tag = tag_result.stdout.strip()
                    if new_tag and new_tag not in current_tags:
                        note.setdefault("tags", []).append(new_tag)
                        note["modified_date"] = str(datetime.now())
                        pm.safe_file_operation('write', NOTES_FILE, pm.notes)
                        pm.send_notification("Tag Added", f"Added tag: {new_tag}")

            elif "🏷️" in selection:
                tag_to_remove = selection.replace("🏷️ ", "").split(" (")[0]
                if tag_to_remove in current_tags:
                    current_tags.remove(tag_to_remove)
                    note["modified_date"] = str(datetime.now())
                    pm.safe_file_operation('write', NOTES_FILE, pm.notes)
                    pm.send_notification("Tag Removed", f"Removed tag: {tag_to_remove}")

    except Exception as e:
        pm.send_notification("Tags Error", f"Failed to manage tags: {e}", "critical")

def show_change_category_dialog(note):
    """Change note category"""
    pm = ProductivityManager()

    try:
        cat_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Select New Category',
                                    '-theme-str', 'window {width: 300px;}'],
                                   input='\n'.join(pm.notes["categories"]), text=True,
                                   capture_output=True)

        if cat_result.returncode == 0:
            new_category = cat_result.stdout.strip()
            if new_category and new_category != note["category"]:
                old_category = note["category"]
                note["category"] = new_category
                note["modified_date"] = str(datetime.now())
                pm.safe_file_operation('write', NOTES_FILE, pm.notes)
                pm.send_notification("Category Changed", f"Moved from {old_category} to {new_category}")

    except Exception as e:
        pm.send_notification("Category Error", f"Failed to change category: {e}", "critical")

def archive_note(note):
    """Archive a note"""
    pm = ProductivityManager()

    note["archived"] = True
    note["modified_date"] = str(datetime.now())
    pm.safe_file_operation('write', NOTES_FILE, pm.notes)
    pm.send_notification("Note Archived", f"Archived: {note['title']}")

def unarchive_note(note):
    """Unarchive a note"""
    pm = ProductivityManager()

    note["archived"] = False
    note["modified_date"] = str(datetime.now())
    pm.safe_file_operation('write', NOTES_FILE, pm.notes)
    pm.send_notification("Note Unarchived", f"Unarchived: {note['title']}")

def show_delete_note_confirmation(note):
    """Show confirmation dialog for note deletion"""
    pm = ProductivityManager()

    try:
        result = subprocess.run(['zenity', '--question', '--title=Delete Note',
                                f'--text=Are you sure you want to delete "{note["title"]}"?\n\nThis action cannot be undone.'],
                               capture_output=True)

        if result.returncode == 0:  # User clicked Yes
            pm.notes["notes"] = [n for n in pm.notes["notes"] if n["id"] != note["id"]]
            pm.safe_file_operation('write', NOTES_FILE, pm.notes)
            pm.send_notification("Note Deleted", f"Deleted: {note['title']}")

    except Exception as e:
        pm.send_notification("Delete Error", f"Failed to delete note: {e}", "critical")

def show_analytics():
    """Show analytics and statistics"""
    pm = ProductivityManager()

    # Calculate analytics
    total_goals = len(pm.goals["goals"])
    completed_goals = len([g for g in pm.goals["goals"] if g["completed"]])
    total_habits = len(pm.habits["habits"])
    total_notes = len([n for n in pm.notes["notes"] if not n["archived"]])

    # Today's screen time
    today = str(date.today())
    today_screen_time = 0
    top_apps = []

    if today in pm.analytics["application_usage"]:
        app_usage = pm.analytics["application_usage"][today]
        total_time = sum(app_usage.values())
        today_screen_time = int(total_time)

        sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        top_apps = [f"{app}: {int(time)}min" for app, time in sorted_apps]

    analytics_text = f"""Productivity Analytics

📊 Overview:
Goals: {completed_goals}/{total_goals} completed
Active Habits: {total_habits}
Notes: {total_notes}
Current Level: {pm.achievements['level']}
Points: {pm.achievements['points']}

📱 Today's Screen Time: {today_screen_time} minutes

🔝 Top Apps Today:
{chr(10).join(top_apps[:3]) if top_apps else 'No data available'}

🏆 Recent Achievements: {len(pm.achievements['unlocked'])}"""

    try:
        subprocess.run(['zenity', '--info', '--title=Productivity Analytics',
                       f'--text={analytics_text}', '--width=450', '--height=400'],
                      capture_output=True)
    except Exception:
        pass

def show_achievements():
    """Show achievements"""
    pm = ProductivityManager()

    unlocked_text = "🏆 Unlocked Achievements:\n\n"
    for achievement in pm.achievements["unlocked"]:
        unlocked_text += f"{achievement['icon']} {achievement['name']}\n"
        unlocked_text += f"   {achievement['description']} (+{achievement['points']} pts)\n\n"

    if not pm.achievements["unlocked"]:
        unlocked_text += "No achievements unlocked yet!\n\n"

    available_text = "🎯 Available Achievements:\n\n"
    for aid, achievement in pm.achievements["available_achievements"].items():
        if not achievement["unlocked"]:
            available_text += f"{achievement['icon']} {achievement['name']}\n"
            available_text += f"   {achievement['description']} (+{achievement['points']} pts)\n\n"

    full_text = unlocked_text + available_text

    try:
        subprocess.run(['zenity', '--info', '--title=Achievements',
                       f'--text={full_text}', '--width=500', '--height=600'],
                      capture_output=True)
    except Exception:
        pass



def show_daily_summary():
    """Show daily summary"""
    pm = ProductivityManager()

    # Get today's stats
    goals_today = [g for g in pm.goals["goals"]
                   if g["completed"] and g["completed_date"] == str(date.today())]

    habits_today = []
    today_str = str(date.today())
    for habit in pm.habits["habits"]:
        if today_str in habit["completion_dates"]:
            habits_today.append(habit)

    # Focus sessions today
    today_focus_sessions = [s for s in pm.analytics["focus_sessions"]
                           if s.get("start_time", "").startswith(today_str) and s.get("completed")]

    summary_text = f"""📅 Daily Summary - {date.today().strftime('%B %d, %Y')}

✅ Goals Completed Today: {len(goals_today)}
{chr(10).join([f"  • {g['title']}" for g in goals_today[:5]])}

🔥 Habits Completed Today: {len(habits_today)}
{chr(10).join([f"  • {h['name']}" for h in habits_today[:5]])}

🧠 Focus Sessions Today: {len(today_focus_sessions)}

📊 Today's Stats:
Focus Time: {pm.daily_stats.get('focus_time', 0)} minutes
Break Time: {pm.daily_stats.get('break_time', 0)} minutes
Productivity Score: {pm.daily_stats.get('productivity_score', 0)}/100

🏆 Level: {pm.achievements['level']} | Points: {pm.achievements['points']}"""

    try:
        subprocess.run(['zenity', '--info', '--title=Daily Summary',
                       f'--text={summary_text}', '--width=450', '--height=400'],
                      capture_output=True)
    except Exception:
        pass

def show_settings():
    """Show settings menu"""
    pm = ProductivityManager()

    settings_options = [
        f"🔔 Notifications: {'ON' if pm.config['notifications_enabled'] else 'OFF'}",
        f"📊 Screen Time Tracking: {'ON' if pm.config['screen_time_tracking'] else 'OFF'}",
        f"🏆 Achievement Notifications: {'ON' if pm.config['achievement_notifications'] else 'OFF'}",
        f"⏰ Break Reminder: {pm.config['break_reminder_interval']} min",
        f"🕐 Habit Reminder: {pm.config['habit_reminder_time']}",
        "🗑️ Clear All Data",
        "📤 Export Data",
        "📥 Import Data"
    ]

    try:
        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Settings',
                                '-theme-str', 'window {width: 400px;}'],
                               input='\n'.join(settings_options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()

            if "Notifications:" in selection:
                pm.config["notifications_enabled"] = not pm.config["notifications_enabled"]
                pm.safe_file_operation('write', CONFIG_FILE, pm.config)
                pm.send_notification("Settings", f"Notifications {'enabled' if pm.config['notifications_enabled'] else 'disabled'}")

            elif "Screen Time Tracking:" in selection:
                pm.config["screen_time_tracking"] = not pm.config["screen_time_tracking"]
                pm.safe_file_operation('write', CONFIG_FILE, pm.config)
                pm.send_notification("Settings", f"Screen time tracking {'enabled' if pm.config['screen_time_tracking'] else 'disabled'}")

            elif "Achievement Notifications:" in selection:
                pm.config["achievement_notifications"] = not pm.config["achievement_notifications"]
                pm.safe_file_operation('write', CONFIG_FILE, pm.config)
                pm.send_notification("Settings", f"Achievement notifications {'enabled' if pm.config['achievement_notifications'] else 'disabled'}")

            elif "Break Reminder:" in selection:
                show_break_reminder_setting()

            elif "Habit Reminder:" in selection:
                show_habit_reminder_setting()

            elif "Clear All Data" in selection:
                show_clear_data_confirmation()

            elif "Export Data" in selection:
                export_data()

            elif "Import Data" in selection:
                import_data()

    except Exception as e:
        pm.send_notification("Settings Error", f"Failed to show settings: {e}", "critical")

def show_break_reminder_setting():
    """Show break reminder interval setting"""
    pm = ProductivityManager()

    try:
        result = subprocess.run(['zenity', '--entry', '--title=Break Reminder',
                                '--text=Enter break reminder interval (minutes):',
                                f'--entry-text={pm.config["break_reminder_interval"]}'],
                               capture_output=True, text=True)

        if result.returncode == 0:
            try:
                interval = int(result.stdout.strip())
                if interval > 0:
                    pm.config["break_reminder_interval"] = interval
                    pm.safe_file_operation('write', CONFIG_FILE, pm.config)
                    pm.send_notification("Settings", f"Break reminder set to {interval} minutes")
            except ValueError:
                pm.send_notification("Settings Error", "Invalid interval value", "critical")

    except Exception as e:
        pm.send_notification("Settings Error", f"Failed to update break reminder: {e}", "critical")

def show_habit_reminder_setting():
    """Show habit reminder time setting"""
    pm = ProductivityManager()

    try:
        result = subprocess.run(['zenity', '--entry', '--title=Habit Reminder',
                                '--text=Enter habit reminder time (HH:MM):',
                                f'--entry-text={pm.config["habit_reminder_time"]}'],
                               capture_output=True, text=True)

        if result.returncode == 0:
            time_str = result.stdout.strip()
            try:
                # Validate time format
                datetime.strptime(time_str, "%H:%M")
                pm.config["habit_reminder_time"] = time_str
                pm.safe_file_operation('write', CONFIG_FILE, pm.config)
                pm.send_notification("Settings", f"Habit reminder set to {time_str}")
            except ValueError:
                pm.send_notification("Settings Error", "Invalid time format. Use HH:MM", "critical")

    except Exception as e:
        pm.send_notification("Settings Error", f"Failed to update habit reminder: {e}", "critical")

def show_edit_goal_dialog(goal):
    """Show dialog to edit existing goal"""
    pm = ProductivityManager()

    try:
        # Edit title
        title_result = subprocess.run(['zenity', '--entry', '--title=Edit Goal Title',
                                      '--text=Enter new title:',
                                      f'--entry-text={goal["title"]}'],
                                     capture_output=True, text=True)

        if title_result.returncode == 0:
            new_title = title_result.stdout.strip()
            if new_title:
                goal["title"] = new_title

        # Edit description
        desc_result = subprocess.run(['zenity', '--entry', '--title=Edit Goal Description',
                                     '--text=Enter new description:',
                                     f'--entry-text={goal["description"]}'],
                                    capture_output=True, text=True)

        if desc_result.returncode == 0:
            goal["description"] = desc_result.stdout.strip()

        # Edit target value
        target_result = subprocess.run(['zenity', '--entry', '--title=Edit Target Value',
                                       '--text=Enter new target value:',
                                       f'--entry-text={goal["target_value"]}'],
                                      capture_output=True, text=True)

        if target_result.returncode == 0:
            try:
                new_target = int(target_result.stdout.strip())
                if new_target > 0:
                    goal["target_value"] = new_target
                    # Ensure current value doesn't exceed new target
                    goal["current_value"] = min(goal["current_value"], new_target)
            except ValueError:
                pm.send_notification("Edit Error", "Invalid target value", "critical")
                return

        pm.safe_file_operation('write', GOALS_FILE, pm.goals)
        pm.send_notification("Goal Updated", f"Updated: {goal['title']}")

    except Exception as e:
        pm.send_notification("Edit Error", f"Failed to edit goal: {e}", "critical")

def show_delete_goal_confirmation(goal):
    """Show confirmation dialog for goal deletion"""
    pm = ProductivityManager()

    try:
        result = subprocess.run(['zenity', '--question', '--title=Delete Goal',
                                f'--text=Are you sure you want to delete "{goal["title"]}"?\n\nThis action cannot be undone.'],
                               capture_output=True)

        if result.returncode == 0:  # User clicked Yes
            pm.goals["goals"] = [g for g in pm.goals["goals"] if g["id"] != goal["id"]]
            pm.safe_file_operation('write', GOALS_FILE, pm.goals)
            pm.send_notification("Goal Deleted", f"Deleted: {goal['title']}")

    except Exception as e:
        pm.send_notification("Delete Error", f"Failed to delete goal: {e}", "critical")

def show_edit_habit_dialog(habit):
    """Show dialog to edit existing habit"""
    pm = ProductivityManager()

    try:
        # Edit name
        name_result = subprocess.run(['zenity', '--entry', '--title=Edit Habit Name',
                                     '--text=Enter new name:',
                                     f'--entry-text={habit["name"]}'],
                                    capture_output=True, text=True)

        if name_result.returncode == 0:
            new_name = name_result.stdout.strip()
            if new_name:
                habit["name"] = new_name

        # Edit description
        desc_result = subprocess.run(['zenity', '--entry', '--title=Edit Habit Description',
                                     '--text=Enter new description:',
                                     f'--entry-text={habit["description"]}'],
                                    capture_output=True, text=True)

        if desc_result.returncode == 0:
            habit["description"] = desc_result.stdout.strip()

        # Edit frequency
        freq_options = ["daily", "weekly", "custom"]
        freq_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Select New Frequency',
                                     '-theme-str', 'window {width: 300px;}'],
                                    input='\n'.join(freq_options), text=True,
                                    capture_output=True)

        if freq_result.returncode == 0:
            habit["frequency"] = freq_result.stdout.strip()

        # Edit reminder time
        time_result = subprocess.run(['zenity', '--entry', '--title=Edit Reminder Time',
                                     '--text=Enter reminder time (HH:MM):',
                                     f'--entry-text={habit["reminder_time"]}'],
                                    capture_output=True, text=True)

        if time_result.returncode == 0:
            time_str = time_result.stdout.strip()
            try:
                datetime.strptime(time_str, "%H:%M")
                habit["reminder_time"] = time_str
            except ValueError:
                pm.send_notification("Edit Error", "Invalid time format. Use HH:MM", "critical")
                return

        pm.safe_file_operation('write', HABITS_FILE, pm.habits)
        pm.send_notification("Habit Updated", f"Updated: {habit['name']}")

    except Exception as e:
        pm.send_notification("Edit Error", f"Failed to edit habit: {e}", "critical")

def show_delete_habit_confirmation(habit):
    """Show confirmation dialog for habit deletion"""
    pm = ProductivityManager()

    try:
        result = subprocess.run(['zenity', '--question', '--title=Delete Habit',
                                f'--text=Are you sure you want to delete "{habit["name"]}"?\n\nThis will permanently remove all streak data.\nThis action cannot be undone.'],
                               capture_output=True)

        if result.returncode == 0:  # User clicked Yes
            pm.habits["habits"] = [h for h in pm.habits["habits"] if h["id"] != habit["id"]]
            pm.safe_file_operation('write', HABITS_FILE, pm.habits)
            pm.send_notification("Habit Deleted", f"Deleted: {habit['name']}")

    except Exception as e:
        pm.send_notification("Delete Error", f"Failed to delete habit: {e}", "critical")

def show_clear_data_confirmation():
    """Show confirmation dialog for clearing all data"""
    pm = ProductivityManager()

    try:
        result = subprocess.run(['zenity', '--question', '--title=Clear All Data',
                                '--text=⚠️ WARNING ⚠️\n\nThis will permanently delete:\n• All goals\n• All habits and streaks\n• All notes\n• All achievements and progress\n• All analytics data\n\nThis action CANNOT be undone!\n\nAre you absolutely sure?'],
                               capture_output=True)

        if result.returncode == 0:  # User clicked Yes
            # Double confirmation
            confirm_result = subprocess.run(['zenity', '--question', '--title=Final Confirmation',
                                           '--text=Type "DELETE ALL" to confirm:'],
                                          capture_output=True)

            if confirm_result.returncode == 0:
                # Clear all data files
                for file_path in [GOALS_FILE, ACHIEVEMENTS_FILE, HABITS_FILE, NOTES_FILE, ANALYTICS_FILE, DAILY_STATS_FILE]:
                    try:
                        os.remove(file_path)
                    except FileNotFoundError:
                        pass

                pm.send_notification("Data Cleared", "All productivity data has been cleared", "critical")

    except Exception as e:
        pm.send_notification("Clear Error", f"Failed to clear data: {e}", "critical")

def export_data():
    """Export all productivity data to a JSON file"""
    pm = ProductivityManager()

    try:
        export_data = {
            "export_date": str(datetime.now()),
            "goals": pm.goals,
            "achievements": pm.achievements,
            "habits": pm.habits,
            "notes": pm.notes,
            "analytics": pm.analytics,
            "daily_stats": pm.daily_stats,
            "config": pm.config
        }

        # Let user choose export location
        result = subprocess.run(['zenity', '--file-selection', '--save',
                                '--title=Export Productivity Data',
                                '--filename=productivity_data_export.json'],
                               capture_output=True, text=True)

        if result.returncode == 0:
            export_path = result.stdout.strip()
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            pm.send_notification("Export Complete", f"Data exported to: {export_path}")

    except Exception as e:
        pm.send_notification("Export Error", f"Failed to export data: {e}", "critical")

def import_data():
    """Import productivity data from a JSON file"""
    pm = ProductivityManager()

    try:
        # Let user choose import file
        result = subprocess.run(['zenity', '--file-selection',
                                '--title=Import Productivity Data',
                                '--file-filter=JSON files | *.json'],
                               capture_output=True, text=True)

        if result.returncode == 0:
            import_path = result.stdout.strip()

            # Confirm import
            confirm_result = subprocess.run(['zenity', '--question', '--title=Import Data',
                                           '--text=⚠️ This will overwrite all current data!\n\nAre you sure you want to import?'],
                                          capture_output=True)

            if confirm_result.returncode == 0:
                with open(import_path, 'r') as f:
                    import_data = json.load(f)

                # Restore data
                if "goals" in import_data:
                    pm.safe_file_operation('write', GOALS_FILE, import_data["goals"])
                if "achievements" in import_data:
                    pm.safe_file_operation('write', ACHIEVEMENTS_FILE, import_data["achievements"])
                if "habits" in import_data:
                    pm.safe_file_operation('write', HABITS_FILE, import_data["habits"])
                if "notes" in import_data:
                    pm.safe_file_operation('write', NOTES_FILE, import_data["notes"])
                if "analytics" in import_data:
                    pm.safe_file_operation('write', ANALYTICS_FILE, import_data["analytics"])
                if "daily_stats" in import_data:
                    pm.safe_file_operation('write', DAILY_STATS_FILE, import_data["daily_stats"])
                if "config" in import_data:
                    pm.safe_file_operation('write', CONFIG_FILE, import_data["config"])

                pm.send_notification("Import Complete", "Data imported successfully")

    except Exception as e:
        pm.send_notification("Import Error", f"Failed to import data: {e}", "critical")

def show_goals_search():
    """Search goals by title or description"""
    pm = ProductivityManager()

    try:
        # Get search term
        search_result = subprocess.run(['zenity', '--entry', '--title=Search Goals',
                                       '--text=Enter search term:', '--width=400'],
                                      capture_output=True, text=True)

        if search_result.returncode != 0:
            return

        search_term = search_result.stdout.strip().lower()
        if not search_term:
            return

        # Search in goals
        matching_goals = []

        for goal in pm.goals["goals"]:
            if (search_term in goal["title"].lower() or
                search_term in goal["description"].lower() or
                search_term in goal["category"].lower()):
                matching_goals.append(goal)

        if not matching_goals:
            subprocess.run(['zenity', '--info', '--title=Search Results',
                           '--text=No goals found matching your search.'],
                          capture_output=True)
            return

        # Show search results
        options = []
        for goal in matching_goals:
            status = "✅" if goal["completed"] else "🎯"
            progress = f"{goal['current_value']}/{goal['target_value']}"
            options.append(f"{status} {goal['title']} [{goal['category']}] - {progress}")

        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'Search Results ({len(matching_goals)} found)',
                                '-theme-str', 'window {width: 600px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()
            # Find selected goal
            goal_title = selection.split(" [")[0].replace("✅ ", "").replace("🎯 ", "")
            for goal in matching_goals:
                if goal["title"] == goal_title:
                    show_goal_actions(goal)
                    break

    except Exception as e:
        pm.send_notification("Search Error", f"Failed to search goals: {e}", "critical")

def show_goals_by_category():
    """Browse goals by category"""
    pm = ProductivityManager()

    categories = {}

    for goal in pm.goals["goals"]:
        category = goal["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(goal)

    if not categories:
        subprocess.run(['zenity', '--info', '--title=Browse Categories',
                       '--text=No goals available.'],
                      capture_output=True)
        return

    try:
        # Show categories
        category_options = [f"📁 {cat} ({len(goals)} goals)" for cat, goals in categories.items()]

        cat_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', 'Select Category',
                                    '-theme-str', 'window {width: 400px;}'],
                                   input='\n'.join(category_options), text=True,
                                   capture_output=True)

        if cat_result.returncode != 0:
            return

        selected_category = cat_result.stdout.strip().split(" (")[0].replace("📁 ", "")

        # Show goals in selected category
        category_goals = categories[selected_category]
        goal_options = []

        for goal in sorted(category_goals, key=lambda x: x.get("deadline") or "9999-12-31"):
            status = "✅" if goal["completed"] else "🎯"
            progress = f"{goal['current_value']}/{goal['target_value']}"
            goal_options.append(f"{status} {goal['title']} - {progress}")

        goal_result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'{selected_category} Goals',
                                     '-theme-str', 'window {width: 500px;}'],
                                    input='\n'.join(goal_options), text=True,
                                    capture_output=True)

        if goal_result.returncode == 0:
            selection = goal_result.stdout.strip()
            goal_title = selection.split(" - ")[0].replace("✅ ", "").replace("🎯 ", "")
            for goal in category_goals:
                if goal["title"] == goal_title:
                    show_goal_actions(goal)
                    break

    except Exception as e:
        pm.send_notification("Category Error", f"Failed to browse categories: {e}", "critical")

def show_completed_goals():
    """Show completed goals"""
    pm = ProductivityManager()

    completed_goals = [g for g in pm.goals["goals"] if g["completed"]]

    if not completed_goals:
        subprocess.run(['zenity', '--info', '--title=Completed Goals',
                       '--text=No completed goals yet.'],
                      capture_output=True)
        return

    try:
        options = []
        for goal in sorted(completed_goals, key=lambda x: x["completed_date"], reverse=True):
            completed_date = datetime.strptime(goal["completed_date"], "%Y-%m-%d").strftime("%m/%d/%Y")
            progress = f"{goal['current_value']}/{goal['target_value']}"
            options.append(f"✅ {goal['title']} [{goal['category']}] - Completed {completed_date}")

        result = subprocess.run(['rofi', '-dmenu', '-i', '-p', f'Completed Goals ({len(completed_goals)})',
                                '-theme-str', 'window {width: 600px;}'],
                               input='\n'.join(options), text=True,
                               capture_output=True)

        if result.returncode == 0:
            selection = result.stdout.strip()
            goal_title = selection.split(" [")[0].replace("✅ ", "")
            for goal in completed_goals:
                if goal["title"] == goal_title:
                    show_goal_actions(goal)
                    break

    except Exception as e:
        pm.send_notification("Completed Goals Error", f"Failed to show completed goals: {e}", "critical")

def main():
    parser = argparse.ArgumentParser(description='Productivity Manager for Waybar')
    parser.add_argument('action', nargs='?', default='status',
                       choices=['status', 'menu', 'goals', 'habits', 'notes', 'analytics', 'focus', 'quick-goal', 'start-focus', 'end-focus'])
    parser.add_argument('--title', type=str, help='Title for quick actions')
    parser.add_argument('--content', type=str, help='Content for quick actions')
    parser.add_argument('--duration', type=int, help='Duration in minutes for focus sessions')

    args = parser.parse_args()

    if args.action == 'status':
        pm = ProductivityManager()
        status = pm.get_status()
        print(json.dumps(status))

    elif args.action == 'menu':
        show_main_menu()

    elif args.action == 'goals':
        show_goals_menu()

    elif args.action == 'habits':
        show_habits_menu()

    elif args.action == 'notes':
        show_notes_menu()

    elif args.action == 'focus':
        show_focus_menu()

    elif args.action == 'start-focus':
        pm = ProductivityManager()
        duration = args.duration or 25
        name = args.title or "Quick Focus"
        pm.start_focus_session(duration, name)

    elif args.action == 'end-focus':
        pm = ProductivityManager()
        pm.end_focus_session()

    elif args.action == 'analytics':
        show_analytics()

    elif args.action == 'quick-goal':
        if args.title:
            pm = ProductivityManager()
            pm.add_goal(args.title, args.content or "", "Personal")

if __name__ == "__main__":
    # Handle signals gracefully
    def signal_handler(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    main()
