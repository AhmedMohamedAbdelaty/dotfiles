#!/bin/bash

# Script to restart system tray applications after waybar restart
# This ensures tray icons reappear properly

echo "Restarting system tray applications..."

# Kill existing tray applications
killall snixembed blueman-applet nm-applet udiskie 2>/dev/null

# Wait a moment for processes to fully stop
sleep 3

# Start StatusNotifierWatcher and wait for it to be ready
echo "Starting StatusNotifierWatcher..."
snixembed &
SNIX_PID=$!

# Wait for snixembed to be ready (check if it's providing the service)
for i in {1..10}; do
    if dbus-send --session --print-reply --dest=org.kde.StatusNotifierWatcher /StatusNotifierWatcher org.freedesktop.DBus.Introspectable.Introspect 2>/dev/null | grep -q "StatusNotifierWatcher"; then
        echo "StatusNotifierWatcher is ready!"
        break
    fi
    echo "Waiting for StatusNotifierWatcher... ($i/10)"
    sleep 1
done

# Start tray applications in order with proper delays
echo "Starting network manager applet..."
nm-applet --indicator &
sleep 2

echo "Starting bluetooth applet..."
blueman-applet &
sleep 2

echo "Starting removable media manager..."
udiskie --no-automount --smart-tray &
sleep 2

# Restart applications that use tray icons
if pgrep -x "Telegram" > /dev/null; then
    echo "Restarting Telegram for tray..."
    pkill Telegram
    sleep 3
    Telegram &
fi

if pgrep -f "vesktop" > /dev/null; then
    echo "Restarting Vesktop for tray..."
    pkill -f vesktop
    sleep 4
    flatpak run dev.vencord.Vesktop &
fi

echo "System tray restart complete!"
