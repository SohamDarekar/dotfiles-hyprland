#!/bin/bash
STATE_FILE="/tmp/ax_battery_state"

if [ -f "$STATE_FILE" ]; then
    IFS=':' read -r STATUS LEVEL NOTIFIED MODE < "$STATE_FILE"
    # Simple notification without icons or app-name to ensure delivery
    notify-send "Battery: ${LEVEL}%" "Status: $STATUS | Mode: $MODE"
else
    notify-send "Battery Error" "Monitor not running"
fi