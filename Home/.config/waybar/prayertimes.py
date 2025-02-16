#!/usr/bin/env python3

import requests
import json
from datetime import datetime, timedelta
import pytz

def fetch_prayer_times():
    url = "http://api.aladhan.com/v1/timingsByCity?city=Cairo&country=Egypt&method=5"
    response = requests.get(url)
    data = response.json()
    return {k: v for k, v in data['data']['timings'].items()
            if k in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']}

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

    return next_prayer[0], format_time_remaining(time_remaining)

def main():
    try:
        prayer_times = fetch_prayer_times()
        next_prayer, time_remaining = time_until_next_prayer(prayer_times)

        # Create tooltip with 12-hour format
        tooltip = "Prayer Times:\n"
        for prayer, time in prayer_times.items():
            tooltip += f"{prayer}: {format_time_12hr(time)}\n"

        output = {
            "text": f"{next_prayer} in {time_remaining}",
            "tooltip": tooltip,
            "class": "custom-prayertimes",
            "alt": "prayertimes"
        }
        print(json.dumps(output))
    except Exception as e:
        output = {
            "text": "Prayer times unavailable",
            "tooltip": str(e),
            "class": "custom-prayertimes-error"
        }
        print(json.dumps(output))

if __name__ == "__main__":
    main()
