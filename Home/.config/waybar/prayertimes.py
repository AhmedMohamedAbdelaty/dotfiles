#!/usr/bin/env python3

import requests
import json
import os
from datetime import datetime, timedelta
import pytz
import time
import subprocess

# Cache file path
CACHE_FILE = os.path.expanduser("~/.cache/waybar-prayertimes.json")
CACHE_VALIDITY = 12 * 3600  # 12 hours in seconds

# --- Startup Notification Flag ---
STARTUP_NOTIFICATION_FLAG_FILE = os.path.expanduser("~/.cache/waybar-prayertimes-startup-notified.flag")

def fetch_prayer_times():
    # Check for valid cache first
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                if time.time() - cache_data['timestamp'] < CACHE_VALIDITY:
                    return cache_data['prayers']
        except Exception:
            pass  # If any error with cache, proceed to fetch fresh data

    # Fetch fresh data with retry logic
    retry_count = 3
    while retry_count > 0:
        try:
            url = "http://api.aladhan.com/v1/timingsByCity?city=Cairo&country=Egypt&method=5"
            response = requests.get(url, timeout=10)
            data = response.json()
            prayers = {k: v for k, v in data['data']['timings'].items()
                    if k in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']}

            # Save to cache
            try:
                os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
                with open(CACHE_FILE, 'w') as f:
                    json.dump({'timestamp': time.time(), 'prayers': prayers}, f)
            except Exception:
                pass  # Proceed even if caching fails

            return prayers
        except Exception:
            retry_count -= 1
            if retry_count <= 0:
                raise
            time.sleep(2)  # Wait before retry

def format_time_remaining(delta):
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def format_time_12hr(time_str):
    # Convert 24-hour format to 12-hour format
    time_obj = datetime.strptime(time_str, "%H:%M")
    return time_obj.strftime("%I:%M %p").lstrip("0")

def time_until_next_prayer(prayer_times):
    # Get current time in Cairo timezone
    cairo_tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(cairo_tz)
    current_date = now.date()

    # Convert prayer times to datetime objects
    prayer_datetimes = {}
    for prayer, time_str in prayer_times.items():
        hours, minutes = map(int, time_str.split(':'))
        prayer_time = cairo_tz.localize(
            datetime.combine(current_date, datetime.min.time().replace(hour=hours, minute=minutes))
        )

        # If prayer time has passed for today, add it for tomorrow
        if prayer_time < now:
            prayer_time += timedelta(days=1)

        prayer_datetimes[prayer] = prayer_time

    # Find next prayer
    next_prayer = min(prayer_datetimes.items(), key=lambda x: x[1])
    time_remaining = next_prayer[1] - now

    # Calculate the class based on how close we are to the next prayer
    minutes_remaining = time_remaining.total_seconds() / 60

    # Simplified class logic
    if minutes_remaining < 15:
        prayer_class = "prayer-imminent"
    elif minutes_remaining < 30:
        prayer_class = "prayer-approaching"
    else:
        prayer_class = "prayer-normal"

    # --- FIXED Notification Logic ---
    # Only send notifications at specific intervals, not every execution
    notification_id = "9991"
    prayer_name_str = next_prayer[0]

    # Create a state file to track last notification time
    state_file = os.path.expanduser("~/.cache/prayer-notification-state.json")
    last_notification_time = 0
    last_notification_type = ""

    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                last_notification_time = state.get('last_time', 0)
                last_notification_type = state.get('last_type', '')
    except:
        pass

    current_time = time.time()
    should_notify = False
    notification_type = ""

    # Only notify at specific thresholds and avoid duplicate notifications
    if 0 < minutes_remaining <= 5:
        notification_type = "5min"
        if last_notification_type != notification_type or (current_time - last_notification_time) > 240:  # 4 minutes
            should_notify = True
    elif 5 < minutes_remaining <= 10:
        notification_type = "10min"
        if last_notification_type != notification_type or (current_time - last_notification_time) > 240:
            should_notify = True
    elif minutes_remaining <= 0:
        notification_type = "now"
        if last_notification_type != notification_type or (current_time - last_notification_time) > 60:  # 1 minute
            should_notify = True

    if should_notify:
        try:
            if notification_type == "5min":
                subprocess.run(["notify-send", "-u", "critical", "-r", notification_id,
                                "Prayer Reminder", f"It's almost time for {prayer_name_str} (5 mins)"],
                               timeout=1, check=False)
            elif notification_type == "10min":
                subprocess.run(["notify-send", "-u", "normal", "-r", notification_id,
                                "Prayer Reminder", f"{prayer_name_str} in 10 minutes"],
                               timeout=1, check=False)
            elif notification_type == "now":
                subprocess.run(["notify-send", "-u", "critical", "-r", notification_id,
                                "Prayer Reminder", f"It's time for {prayer_name_str}!"],
                               timeout=1, check=False)

            # Update state file
            try:
                with open(state_file, 'w') as f:
                    json.dump({
                        'last_time': current_time,
                        'last_type': notification_type
                    }, f)
            except:
                pass

        except Exception as e:
            pass # Non-critical

    return next_prayer[0], format_time_remaining(time_remaining), prayer_class

def main():
    # --- Startup Notification Logic ---
    if not os.path.exists(STARTUP_NOTIFICATION_FLAG_FILE):
        try:
            subprocess.run([
                "notify-send",
                "-u", "low",  # Low urgency
                "-a", "PrayerTimesWaybar", # Application name
                "Prayer Times Module",    # Summary/Title
                "Initialized. Prayer reminder system is active."], # Body
                timeout=1, check=False)
            # Create the flag file to prevent repeated notifications
            with open(STARTUP_NOTIFICATION_FLAG_FILE, 'w') as f_flag:
                f_flag.write('notified')
        except Exception:
            pass

    try:
        prayer_times = fetch_prayer_times()
        if not prayer_times: # Handle case where fetching fails and no cache
            output = {
                "text": " Prayer times unavailable",
                "tooltip": "Could not fetch prayer times and no cache available.",
                "class": "custom-prayertimes-error"
            }
            print(json.dumps(output))
            return

        next_prayer, time_remaining, prayer_class = time_until_next_prayer(prayer_times)

        # Create tooltip with 12-hour format
        tooltip = "Prayer Times:\n"
        for prayer, time in prayer_times.items():
            tooltip += f"{prayer}: {format_time_12hr(time)}\n"

        output = {
            "text": f" {next_prayer} in {time_remaining}",
            "tooltip": tooltip,
            "class": f"custom-prayertimes {prayer_class}",
            "alt": "prayertimes"
        }
        print(json.dumps(output))
    except Exception as e:
        # Try to use cached data if available
        error_message = str(e)
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                    prayer_times = cache_data['prayers']
                    next_prayer, time_remaining, prayer_class = time_until_next_prayer(prayer_times)

                    tooltip = "Prayer Times (cached):\n"
                    for prayer, time in prayer_times.items():
                        tooltip += f"{prayer}: {format_time_12hr(time)}\n"
                    tooltip += f"\n(Error fetching: {error_message})"

                    output = {
                        "text": f" {next_prayer} in {time_remaining}",
                        "tooltip": tooltip,
                        "class": f"custom-prayertimes {prayer_class} cached",
                        "alt": "prayertimes-cached"
                    }
                    print(json.dumps(output))
                    return
        except Exception as cache_e:
            error_message = f"Original error: {error_message}, Cache error: {str(cache_e)}"
            pass

        output = {
            "text": " Prayer times error",
            "tooltip": f"Error: {error_message}",
            "class": "custom-prayertimes-error"
        }
        print(json.dumps(output))

if __name__ == "__main__":
    main()
