#!/home/ahmed/.pyenv/versions/3.12.10/bin/python

import requests
import json
import os
from datetime import datetime, timedelta
import pytz
import time
import subprocess
import logging

# Configuration
CACHE_FILE = os.path.expanduser("~/.cache/waybar-prayertimes.json")
NOTIFICATION_STATE_FILE = os.path.expanduser("~/.cache/prayer-notification-state.json")
STARTUP_FLAG_FILE = os.path.expanduser("~/.cache/waybar-prayertimes-startup-notified.flag")

CACHE_VALIDITY = 12 * 3600  # 12 hours
CAIRO_TZ = pytz.timezone('Africa/Cairo')
NOTIFICATION_ID = "9991"

# Notification thresholds in minutes
NOTIFICATION_THRESHOLDS = [15, 5, 0]

def load_cached_prayers():
    """Load prayer times from cache if valid."""
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
            if time.time() - cache_data['timestamp'] < CACHE_VALIDITY:
                return cache_data['prayers']
    except Exception:
        pass
    return None

def save_prayers_to_cache(prayers):
    """Save prayer times to cache."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump({'timestamp': time.time(), 'prayers': prayers}, f)
    except Exception:
        pass  # Non-critical if caching fails

def fetch_prayer_times():
    """Fetch prayer times from API or cache."""
    # Try cache first
    cached_prayers = load_cached_prayers()
    if cached_prayers:
        return cached_prayers

    # Fetch from API with retries
    for attempt in range(3):
        try:
            url = "https://api.aladhan.com/v1/timingsByCity?city=Cairo&country=Egypt&method=5"
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            data = response.json()
            prayers = {k: v for k, v in data['data']['timings'].items()
                      if k in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']}

            save_prayers_to_cache(prayers)
            return prayers

        except Exception as e:
            if attempt == 2:  # Last attempt
                raise e
            time.sleep(2)

    return None

def format_time_remaining(delta):
    """Format time remaining as hours and minutes."""
    total_minutes = int(delta.total_seconds() / 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def format_time_12hr(time_str):
    """Convert 24-hour format to 12-hour format."""
    time_obj = datetime.strptime(time_str, "%H:%M")
    return time_obj.strftime("%I:%M %p").lstrip("0")

def get_next_prayer_info(prayer_times):
    """Calculate the next prayer and time remaining."""
    now = datetime.now(CAIRO_TZ)
    today = now.date()

    # Convert prayer times to datetime objects
    prayer_datetimes = []
    for prayer, time_str in prayer_times.items():
        try:
            hours, minutes = map(int, time_str.split(':'))
            prayer_dt = CAIRO_TZ.localize(
                datetime.combine(today, datetime.min.time().replace(hour=hours, minute=minutes))
            )

            # If prayer has passed today, schedule for tomorrow
            if prayer_dt <= now:
                prayer_dt += timedelta(days=1)

            prayer_datetimes.append((prayer, prayer_dt))
        except ValueError:
            # Skip invalid time formats
            continue

    if not prayer_datetimes:
        raise ValueError("No valid prayer times found")

    # Find the next prayer
    next_prayer, next_time = min(prayer_datetimes, key=lambda x: x[1])
    time_remaining = next_time - now

    # Ensure positive time remaining
    if time_remaining.total_seconds() < 0:
        time_remaining = timedelta(0)

    # Determine CSS class based on time remaining
    minutes_remaining = time_remaining.total_seconds() / 60
    if minutes_remaining <= 15:
        css_class = "prayer-imminent"
    elif minutes_remaining <= 30:
        css_class = "prayer-approaching"
    else:
        css_class = "prayer-normal"

    return next_prayer, time_remaining, css_class

def load_notification_state():
    """Load the last notification state."""
    try:
        if os.path.exists(NOTIFICATION_STATE_FILE):
            with open(NOTIFICATION_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {"last_prayer": "", "last_threshold": -1, "last_time": 0}

def save_notification_state(prayer, threshold):
    """Save the current notification state."""
    try:
        state = {
            "last_prayer": prayer,
            "last_threshold": threshold,
            "last_time": time.time()
        }
        with open(NOTIFICATION_STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass

def send_prayer_notification(prayer, minutes_remaining):
    """Send prayer notification based on time remaining."""
    try:
        if minutes_remaining == 0:
            message = f"It's time for {prayer}!"
            urgency = "critical"
        elif minutes_remaining <= 5:
            message = f"{prayer} in {minutes_remaining} minute{'s' if minutes_remaining != 1 else ''}"
            urgency = "critical"
        else:
            message = f"{prayer} in {minutes_remaining} minutes"
            urgency = "normal"

        subprocess.run([
            "notify-send", "-u", urgency, "-r", NOTIFICATION_ID,
            "Prayer Reminder", message
        ], timeout=5, check=False)

    except Exception:
        pass  # Non-critical if notification fails

def check_and_send_notifications(prayer, time_remaining):
    """Check if we should send a notification and send it if needed."""
    minutes_remaining = int(time_remaining.total_seconds() / 60)

    # Only notify at specific thresholds
    threshold_to_notify = None
    for threshold in NOTIFICATION_THRESHOLDS:
        if minutes_remaining <= threshold:
            threshold_to_notify = threshold
            break

    if threshold_to_notify is None:
        return

    # Load last notification state
    state = load_notification_state()

    # Check if we've already notified for this prayer at this threshold
    if (state["last_prayer"] == prayer and
        state["last_threshold"] == threshold_to_notify and
        time.time() - state["last_time"] < 300):  # Don't repeat within 5 minutes
        return

    # Send notification and update state
    send_prayer_notification(prayer, minutes_remaining)
    save_notification_state(prayer, threshold_to_notify)

def create_output_json(prayer_times):
    """Create the JSON output for waybar."""
    try:
        next_prayer, time_remaining, css_class = get_next_prayer_info(prayer_times)

        # Check and send notifications
        check_and_send_notifications(next_prayer, time_remaining)

        # Create tooltip
        tooltip = "Prayer Times:\n"
        for prayer, time in prayer_times.items():
            tooltip += f"{prayer}: {format_time_12hr(time)}\n"

        return {
            "text": f" {next_prayer} in {format_time_remaining(time_remaining)}",
            "tooltip": tooltip.strip(),
            "class": f"custom-prayertimes {css_class}",
            "alt": "prayertimes"
        }

    except Exception as e:
        return {
            "text": " Prayer times error",
            "tooltip": f"Error calculating prayer times: {str(e)}",
            "class": "custom-prayertimes-error"
        }

def send_startup_notification():
    """Send one-time startup notification."""
    if not os.path.exists(STARTUP_FLAG_FILE):
        try:
            subprocess.run([
                "notify-send", "-u", "low", "-a", "PrayerTimesWaybar",
                "Prayer Times Module", "Initialized. Prayer reminder system is active."
            ], timeout=5, check=False)

            with open(STARTUP_FLAG_FILE, 'w') as f:
                f.write('notified')
        except Exception:
            pass

def cleanup_old_cache_files():
    """Clean up old cache files to prevent disk space issues."""
    try:
        # Remove startup flag older than 24 hours to allow re-notification after system restart
        if os.path.exists(STARTUP_FLAG_FILE):
            stat = os.stat(STARTUP_FLAG_FILE)
            if time.time() - stat.st_mtime > 24 * 3600:
                os.remove(STARTUP_FLAG_FILE)
    except Exception:
        pass

def main():
    """Main function to run the prayer times module."""
    cleanup_old_cache_files()
    send_startup_notification()

    try:
        prayer_times = fetch_prayer_times()
        if not prayer_times:
            output = {
                "text": " Prayer times unavailable",
                "tooltip": "Could not fetch prayer times and no cache available.",
                "class": "custom-prayertimes-error"
            }
        else:
            output = create_output_json(prayer_times)

    except Exception as e:
        # Try cached data as fallback
        cached_prayers = load_cached_prayers()
        if cached_prayers:
            try:
                output = create_output_json(cached_prayers)
                output["tooltip"] += f"\n\n(Using cached data - Error: {str(e)})"
                output["class"] += " cached"
                output["alt"] = "prayertimes-cached"
            except Exception:
                output = {
                    "text": " Prayer times error",
                    "tooltip": f"Error with cached data: {str(e)}",
                    "class": "custom-prayertimes-error"
                }
        else:
            output = {
                "text": " Prayer times error",
                "tooltip": f"Error: {str(e)}",
                "class": "custom-prayertimes-error"
            }

    print(json.dumps(output))

if __name__ == "__main__":
    main()
