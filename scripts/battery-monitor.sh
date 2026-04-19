#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_power_mode_actions.sh"

STATE_FILE="/tmp/ax_battery_state"
POWER_MODE_FILE="/tmp/ax_power_mode"
MANUAL_MODE_FILE="/tmp/ax_manual_power_mode"
LOG_FILE="/tmp/battery_monitor.log"

# Logging function
log_message() {
    echo "$(date): $1" | tee -a "$LOG_FILE"
}

# Find correct battery path
find_battery_path() {
    for bat in /sys/class/power_supply/BAT*; do
        if [ -f "$bat/capacity" ]; then
            echo "$bat"
            return
        fi
    done
    echo ""
}

# Find correct AC adapter path
find_ac_path() {
    for ac in /sys/class/power_supply/{AC*,ADP*,ACAD*}; do
        if [ -f "$ac/online" ]; then
            echo "$ac"
            return
        fi
    done
    echo ""
}

BATTERY_PATH=$(find_battery_path)
AC_PATH=$(find_ac_path)

if [ -z "$BATTERY_PATH" ]; then
    log_message "ERROR: No battery found!"
    exit 1
fi

if [ -z "$AC_PATH" ]; then
    log_message "ERROR: No AC adapter found!"
    exit 1
fi

log_message "Using battery: $BATTERY_PATH"
log_message "Using AC adapter: $AC_PATH"

# Power management with shared system actions
apply_power_mode() {
    local mode=$1
    local notify=${2:-true}
    local source=${3:-"Auto"}
    local level=$(cat "$BATTERY_PATH/capacity" 2>/dev/null || echo "?")

    log_message "Applying power mode: $mode ($source)"
    _apply_power_actions "$mode"
    log_message "Applied system settings for $mode"

    if [ "$notify" = "true" ]; then
        case "$mode" in
            performance)
                notify-send "Performance Mode" "Battery: ${level}% · $source" -i "/usr/share/icons/Papirus/24x24/panel/battery-good.svg" -a "System" -u normal ;;
            powersave)
                notify-send "Power Saving" "Battery: ${level}% · $source" -i "/usr/share/icons/Papirus/24x24/panel/battery-low.svg" -a "System" -u normal ;;
            ultra-powersave)
                notify-send "Ultra Power Saving" "Battery: ${level}% · $source" -i "/usr/share/icons/Papirus/24x24/panel/battery-caution.svg" -a "System" -u normal ;;
            disabled)
                notify-send "Power Saving Disabled" "Battery: ${level}% · $source" -i "/usr/share/icons/Papirus/24x24/panel/battery-full.svg" -a "System" -u normal ;;
        esac
        log_message "Sent $mode notification"
    fi

    echo "$mode" > "$POWER_MODE_FILE"
    log_message "Saved power mode: $mode"
}

# Main loop
log_message "Battery monitor starting..."

while true; do
    # Check if we're in manual mode
    MANUAL_MODE="false"
    MANUAL_MODE_VALUE=""
    if [ -f "$MANUAL_MODE_FILE" ]; then
        MANUAL_MODE="true"
        MANUAL_MODE_VALUE=$(cat "$MANUAL_MODE_FILE")
        log_message "Manual mode active: $MANUAL_MODE_VALUE"
    fi

    # Get current power mode
    if [ -f "$POWER_MODE_FILE" ]; then
        CURRENT_POWER_MODE=$(cat "$POWER_MODE_FILE")
    else
        CURRENT_POWER_MODE="performance"
        echo "performance" > "$POWER_MODE_FILE"
    fi

    # Get current status
    CURRENT_LEVEL=$(cat "$BATTERY_PATH/capacity" 2>/dev/null || echo "0")
    BATTERY_STATUS=$(cat "$BATTERY_PATH/status" 2>/dev/null || echo "Unknown")
    AC_ONLINE=$(cat "$AC_PATH/online" 2>/dev/null || echo "0")

    # Determine charging state based on AC adapter and battery status
    if [ "$AC_ONLINE" = "1" ]; then
        CURRENT_STATUS="Charging"
    elif [ "$BATTERY_STATUS" = "Discharging" ]; then
        CURRENT_STATUS="Discharging"
    else
        CURRENT_STATUS="$BATTERY_STATUS"
    fi

    # Debug output
    log_message "Battery Level: $CURRENT_LEVEL%, Status: $BATTERY_STATUS, AC: $AC_ONLINE, Determined: $CURRENT_STATUS, Power Mode: $CURRENT_POWER_MODE, Manual: $MANUAL_MODE"

    # Read previous state
    if [ -f "$STATE_FILE" ]; then
        PREV_STATE=$(cat "$STATE_FILE")
        PREV_STATUS=$(echo "$PREV_STATE" | cut -d: -f1)
        PREV_LEVEL=$(echo "$PREV_STATE" | cut -d: -f2)
        LOW_NOTIFIED=$(echo "$PREV_STATE" | cut -d: -f3)
        PREV_POWER_MODE=$(echo "$PREV_STATE" | cut -d: -f4)
    else
        PREV_STATUS="Unknown"
        PREV_LEVEL="100"
        LOW_NOTIFIED="false"
        PREV_POWER_MODE="performance"
    fi

    NEW_POWER_MODE="$CURRENT_POWER_MODE"

    # Power mode logic
    if [ "$MANUAL_MODE" = "true" ]; then
        if [ "$CURRENT_POWER_MODE" != "$MANUAL_MODE_VALUE" ]; then
            NEW_POWER_MODE="$MANUAL_MODE_VALUE"
            apply_power_mode "$NEW_POWER_MODE" true "Manual"
        fi
    else
        # Automatic power mode switching
        if [ "$CURRENT_STATUS" = "Charging" ]; then
            if [ "$CURRENT_POWER_MODE" != "performance" ]; then
                NEW_POWER_MODE="performance"
                apply_power_mode "$NEW_POWER_MODE" true "Auto"
            fi
        elif [ "$CURRENT_STATUS" = "Discharging" ]; then
            if [ "$CURRENT_LEVEL" -le 15 ]; then
                if [ "$CURRENT_POWER_MODE" != "ultra-powersave" ]; then
                    NEW_POWER_MODE="ultra-powersave"
                    apply_power_mode "$NEW_POWER_MODE" true "Auto"
                fi
            elif [ "$CURRENT_LEVEL" -le 40 ]; then
                if [ "$CURRENT_POWER_MODE" != "powersave" ]; then
                    NEW_POWER_MODE="powersave"
                    apply_power_mode "$NEW_POWER_MODE" true "Auto"
                fi
            elif [ "$CURRENT_LEVEL" -gt 40 ]; then
                if [ "$CURRENT_POWER_MODE" != "performance" ]; then
                    NEW_POWER_MODE="performance"
                    apply_power_mode "$NEW_POWER_MODE" true "Auto"
                fi
            fi
        fi
    fi

    # Check for charger plug/unplug
    if [[ "$CURRENT_STATUS" != "$PREV_STATUS" ]]; then
        log_message "Status changed from $PREV_STATUS to $CURRENT_STATUS"
        case "$CURRENT_STATUS" in
            "Charging")
                notify-send "Charging" "Battery: ${CURRENT_LEVEL}%" -i "/usr/share/icons/Papirus/24x24/panel/battery-000-charging.svg" -a "System" -u normal
                log_message "Sent charging notification"
                ;;
            "Discharging"|"Not charging")
                notify-send "Discharging" "Battery: ${CURRENT_LEVEL}%" -i "/usr/share/icons/Papirus/24x24/panel/battery-good.svg" -a "System" -u normal
                log_message "Sent discharging notification"
                ;;
        esac
    fi

    # Check for low battery
    if [[ "$CURRENT_LEVEL" -le 15 && "$CURRENT_STATUS" == "Discharging" ]]; then
        if [[ "$LOW_NOTIFIED" != "critical" || "$PREV_LEVEL" -gt 15 || "$PREV_STATUS" != "Discharging" ]]; then
            notify-send "Critical Battery" "Battery: ${CURRENT_LEVEL}% · Plug in now" -i "/usr/share/icons/Papirus/24x24/panel/battery-caution.svg" -a "System" -u critical
            log_message "Sent critical low battery notification"
            LOW_NOTIFIED="critical"
        fi
    elif [[ "$CURRENT_LEVEL" -le 30 && "$CURRENT_STATUS" == "Discharging" ]]; then
        if [[ "$LOW_NOTIFIED" != "true" || "$PREV_LEVEL" -gt 30 || "$PREV_STATUS" != "Discharging" ]]; then
            notify-send "Low Battery" "Battery: ${CURRENT_LEVEL}% · Plug in soon" -i "/usr/share/icons/Papirus/24x24/panel/battery-low.svg" -a "System" -u critical
            log_message "Sent low battery notification"
            LOW_NOTIFIED="true"
        fi
    elif [[ "$CURRENT_LEVEL" -gt 30 || "$CURRENT_STATUS" == "Charging" ]]; then
        LOW_NOTIFIED="false"
    fi

    # Save current state
    echo "${CURRENT_STATUS}:${CURRENT_LEVEL}:${LOW_NOTIFIED}:${NEW_POWER_MODE}" > "$STATE_FILE"

    sleep 1
done
