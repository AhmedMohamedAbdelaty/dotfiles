#!/bin/bash

# Pomodoro timer script
WORK_TIME=25
BREAK_TIME=5
LONG_BREAK_TIME=15

case "$1" in
    work)
        dunstify -a "pomodoro" -u "normal" -i "tomato" -t 5000 \
            "🍅 Pomodoro Started" "Work time: $WORK_TIME minutes\nStay focused!"
        sleep $((WORK_TIME * 60))
        dunstify -a "pomodoro" -u "critical" -i "tomato" -t 0 \
            "🍅 Work Session Complete "Time for a break!\nClick to start break."
        ;;
    break)
        dunstify -a "pomodoro" -u "normal" -i "coffee" -t 5000 \
            "☕ Break Started" "Break time: $BREAK_TIME minutes\nRelax and recharge!"
        sleep $((BREAK_TIME * 60))
        dunstify -a "pomodoro" -u "normal" -i "coffee" -t 0 \
            "☕ Break Complete "Ready for another session?\nClick to start work."
        ;;
    longbreak)
        dunstify -a "pomodoro" -u "normal" -i "coffee" -t 5000 \
            "🛋️ Long Break Started" "Long break: $LONG_BREAK_TIME minutes\nYou deserve this!"
        sleep $((LONG_BREAK_TIME * 60))
        dunstify -a "pomodoro" -u "normal" -i "coffee" -t 0 \
            "🛋️ Long Break Complete "Refreshed and ready!\nClick to start work."
        ;;
    *)
        echo "Usage: $0 {work|break|longbreak}"
        exit 1
        ;;
esac
