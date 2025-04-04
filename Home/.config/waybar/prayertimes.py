#!/usr/bin/env python3

import requests
import json
import os
from datetime import datetime, timedelta
import pytz
import time

# Cache file path
CACHE_FILE = os.path.expanduser("~/.cache/waybar-prayertimes.json")
CACHE_VALIDITY = 12 * 3600  # 12 hours in seconds

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
    if minutes_remaining < 15:
        prayer_class = "prayer-imminent"
    elif minutes_remaining < 30:
        prayer_class = "prayer-approaching"
    else:
        prayer_class = "prayer-normal"

    return next_prayer[0], format_time_remaining(time_remaining), prayer_class

def main():
    try:
        prayer_times = fetch_prayer_times()
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
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                    prayer_times = cache_data['prayers']
                    next_prayer, time_remaining, prayer_class = time_until_next_prayer(prayer_times)

                    tooltip = "Prayer Times (cached):\n"
                    for prayer, time in prayer_times.items():
                        tooltip += f"{prayer}: {format_time_12hr(time)}\n"

                    output = {
                        "text": f" {next_prayer} in {time_remaining}",
                        "tooltip": tooltip + "\n(Using cached data)",
                        "class": f"custom-prayertimes {prayer_class} cached",
                        "alt": "prayertimes-cached"
                    }
                    print(json.dumps(output))
                    return
        except Exception:
            pass

        output = {
            "text": " Prayer times",
            "tooltip": f"Error: {str(e)}",
            "class": "custom-prayertimes-error"
        }
        print(json.dumps(output))

if __name__ == "__main__":
    main()
