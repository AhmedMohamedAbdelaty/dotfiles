#!/bin/bash

# Get system information
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
memory_usage=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
disk_usage=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
uptime=$(uptime -p | sed 's/up //')

# Create system info notification
info="🖥️ CPU: ${cpu_usage}%
💾 RAM: ${memory_usage}%
💿 Disk: ${disk_usage}%
⏱️ Uptime: ${uptime}"

# Send notification
dunstify -a "system" -u "normal" -i "computer" -t 10000 \
    "🔧 System Info" "$info"
