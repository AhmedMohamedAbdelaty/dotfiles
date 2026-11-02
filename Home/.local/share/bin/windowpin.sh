#!/usr/bin/env sh

# enable float
WinFloat=$(hyprctl -j clients | jq '.[] | select(.focusHistoryID == 0) | .floating')
WinPinned=$(hyprctl -j clients | jq '.[] | select(.focusHistoryID == 0) | .pinned')

if [ "${WinFloat}" == "false" ] && [ "${WinPinned}" == "false" ] ; then
    hyprctl dispatch 'hl.dsp.window.float({ action = "toggle" })'
fi

# toggle pin
hyprctl dispatch 'hl.dsp.window.pin()'

# disable float
WinFloat=$(hyprctl -j clients | jq '.[] | select(.focusHistoryID == 0) | .floating')
WinPinned=$(hyprctl -j clients | jq '.[] | select(.focusHistoryID == 0) | .pinned')

if [ "${WinFloat}" == "true" ] && [ "${WinPinned}" == "false" ] ; then
    hyprctl dispatch 'hl.dsp.window.float({ action = "toggle" })'
fi

