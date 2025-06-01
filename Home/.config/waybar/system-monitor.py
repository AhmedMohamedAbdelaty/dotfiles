#!/usr/bin/env python3

import json
import psutil
import subprocess
import os
import time
from datetime import datetime, timedelta

# Cache file to avoid frequent disk operations
CACHE_FILE = os.path.expanduser("~/.cache/waybar-sysmon.json")
CACHE_VALIDITY = 5  # seconds

def get_temps():
    """Get temperature data in a way that's resilient to errors"""
    temps = {}
    try:
        # Try using psutil first (more reliable)
        if hasattr(psutil, "sensors_temperatures"):
            temps_data = psutil.sensors_temperatures()
            if temps_data:
                for chip, sensors in temps_data.items():
                    for sensor in sensors:
                        if sensor.label and "core" in sensor.label.lower():
                            temps[sensor.label] = sensor.current

                # If we got CPU temps, return them
                if temps:
                    return temps

                # Otherwise, take any temperature sensor
                for chip, sensors in temps_data.items():
                    for sensor in sensors:
                        temps[sensor.label or chip] = sensor.current

        # If psutil didn't give us useful data, try sensors command
        if not temps:
            try:
                output = subprocess.check_output(["sensors", "-j"], text=True)
                data = json.loads(output)

                for chip, values in data.items():
                    for key, subvalues in values.items():
                        if isinstance(subvalues, dict) and "temp1_input" in subvalues:
                            temps[key] = subvalues["temp1_input"]
            except (subprocess.SubprocessError, json.JSONDecodeError):
                pass

        return temps
    except Exception:
        # Return empty dict in case of any issues
        return {}

def get_disk_usage():
    """Get disk usage for the root partition"""
    try:
        usage = psutil.disk_usage("/")
        return {
            "total": usage.total / (1024**3),  # GB
            "used": usage.used / (1024**3),  # GB
            "percent": usage.percent
        }
    except Exception:
        return {"total": 0, "used": 0, "percent": 0}

def get_load_avg():
    """Get system load averages"""
    try:
        return os.getloadavg()
    except Exception:
        return (0.0, 0.0, 0.0)

def get_uptime():
    """Get system uptime in human readable format"""
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        uptime = timedelta(seconds=uptime_seconds)
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h"
        else:
            return f"{hours}h {minutes}m"
    except Exception:
        return "Unknown"

def get_cpu_usage():
    """Get CPU usage percentage"""
    try:
        return psutil.cpu_percent(interval=0.1)
    except Exception:
        return 0.0

def get_memory_usage():
    """Get RAM usage information"""
    try:
        mem = psutil.virtual_memory()
        return {
            "total": mem.total / (1024**3),  # GB
            "used": mem.used / (1024**3),  # GB
            "percent": mem.percent
        }
    except Exception:
        return {"total": 0, "used": 0, "percent": 0}

def format_size(size_bytes):
    """Format bytes to human readable format with appropriate precision"""
    if size_bytes < 1024:
        return f"{size_bytes:.1f} B"

    for unit in ['KB', 'MB', 'GB', 'TB']:
        size_bytes /= 1024.0
        if size_bytes < 1024.0:
            # Use more decimals for smaller values, fewer for larger
            if unit == 'KB':
                return f"{size_bytes:.1f} {unit}"
            elif unit == 'MB':
                return f"{size_bytes:.2f} {unit}"
            else:
                return f"{size_bytes:.2f} {unit}"

    return f"{size_bytes:.2f} PB"

def main():
    try:
        # Get system data
        temps = get_temps()
        cpu_temp = max(temps.values()) if temps else 0
        disk = get_disk_usage()
        load_avg = get_load_avg()
        uptime = get_uptime()
        cpu_usage = get_cpu_usage()
        mem = get_memory_usage()

        # Determine icon and class based on CPU usage
        if cpu_usage > 80:
            cpu_icon = "󰓅"
            cls = "critical"
        elif cpu_usage > 50:
            cpu_icon = "󰒋"
            cls = "warning"
        else:
            cpu_icon = "󰓅"
            cls = "normal"

        # RAM icon based on usage
        if mem['percent'] > 80:
            ram_icon = "󰍛"
        elif mem['percent'] > 50:
            ram_icon = "󰍛"
        else:
            ram_icon = "󰍛"

        # Create tooltip with details
        tooltip = (
            f"CPU Usage: {cpu_usage:.1f}%\n"
            f"RAM: {mem['used']:.1f}GB/{mem['total']:.1f}GB ({mem['percent']}%)\n"
            f"Disk: {disk['used']:.1f}GB/{disk['total']:.1f}GB ({disk['percent']}%)\n"
            f"Load Avg: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}\n"
            f"Uptime: {uptime}"
        )

        if temps:
            tooltip += f"\n\nTemperatures:"
            for sensor, temp in temps.items():
                tooltip += f"\n{sensor}: {temp}°C"

        # Format text with CPU and RAM only
        text = f"{cpu_icon} {cpu_usage:.0f}%  {ram_icon} {mem['percent']}%"

        # Output for waybar
        output = {
            "text": text,
            "tooltip": tooltip,
            "class": f"system-monitor-{cls}",
            "alt": f"CPU: {cpu_usage:.1f}%"
        }

        print(json.dumps(output))

    except Exception as e:
        output = {
            "text": "󰓅 -- • 󰍛 --",
            "tooltip": f"Error: {str(e)}",
            "class": "system-monitor-error"
        }
        print(json.dumps(output))

if __name__ == "__main__":
    main()
