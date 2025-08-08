#!/bin/bash

# Enhanced battery monitor with better debugging
set -e

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

# Power management functions with error checking
apply_power_mode() {
    local mode=$1
    local notify=${2:-true}
    local source=${3:-"Auto"}
    
    log_message "Applying power mode: $mode ($source)"
    
    case "$mode" in
        "performance")
            # Set CPU governor to performance
            if echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1; then
                log_message "CPU governor set to performance"
            else
                log_message "ERROR: Failed to set CPU governor to performance"
            fi
            
            # Re-enable all CPU cores
            for cpu in {1..7}; do
                if echo 1 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; then
                    log_message "Enabled CPU core $cpu"
                fi
            done
            
            # Restore normal brightness
            if command -v brightnessctl > /dev/null; then
                if brightnessctl set 80% > /dev/null 2>&1; then
                    log_message "Brightness set to 80%"
                else
                    log_message "ERROR: Failed to set brightness to 80%"
                fi
            else
                log_message "WARNING: brightnessctl not available"
            fi
            
            if [ "$notify" = "true" ]; then
                notify-send "Power Mode" "Performance Mode Active ($source)" -i "battery-good" -a "System" -u normal
                log_message "Sent performance mode notification"
            fi
            ;;
            
        "powersave")
            # Set CPU governor to powersave
            if echo "powersave" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1; then
                log_message "CPU governor set to powersave"
            else
                log_message "ERROR: Failed to set CPU governor to powersave"
            fi
            
            # Reduce brightness
            if command -v brightnessctl > /dev/null; then
                if brightnessctl set 50% > /dev/null 2>&1; then
                    log_message "Brightness set to 50%"
                else
                    log_message "ERROR: Failed to set brightness to 50%"
                fi
            else
                log_message "WARNING: brightnessctl not available"
            fi
            
            if [ "$notify" = "true" ]; then
                notify-send "Power Mode" "Power Saving Active ($source)" -i "battery-low" -a "System" -u normal
                log_message "Sent power saving mode notification"
            fi
            ;;
            
        "ultra-powersave")
            # Set CPU governor to powersave
            if echo "powersave" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1; then
                log_message "CPU governor set to powersave"
            else
                log_message "ERROR: Failed to set CPU governor to powersave"
            fi
            
            # Disable half of CPU cores
            for cpu in {1..3}; do
                if echo 0 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; then
                    log_message "Disabled CPU core $cpu"
                fi
            done
            
            # Set minimum brightness
            if command -v brightnessctl > /dev/null; then
                if brightnessctl set 20% > /dev/null 2>&1; then
                    log_message "Brightness set to 20%"
                else
                    log_message "ERROR: Failed to set brightness to 20%"
                fi
            else
                log_message "WARNING: brightnessctl not available"
            fi
            
            if [ "$notify" = "true" ]; then
                notify-send "Power Mode" "Ultra Power Saving Active ($source)" -i "battery-caution" -a "System" -u normal
                log_message "Sent ultra power saving mode notification"
            fi
            ;;
            
        "disabled")
            # When power saving is disabled, ensure performance mode
            if echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1; then
                log_message "CPU governor set to performance (disabled mode)"
            else
                log_message "ERROR: Failed to set CPU governor to performance (disabled mode)"
            fi
            
            # Re-enable all CPU cores
            for cpu in {1..7}; do
                if echo 1 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; then
                    log_message "Enabled CPU core $cpu (disabled mode)"
                fi
            done
            
            # Restore normal brightness
            if command -v brightnessctl > /dev/null; then
                if brightnessctl set 80% > /dev/null 2>&1; then
                    log_message "Brightness set to 80% (disabled mode)"
                else
                    log_message "ERROR: Failed to set brightness to 80% (disabled mode)"
                fi
            else
                log_message "WARNING: brightnessctl not available"
            fi
            
            if [ "$notify" = "true" ]; then
                notify-send "Power Mode" "Power Saving Disabled ($source)" -i "battery-full" -a "System" -u normal
                log_message "Sent disabled power saving mode notification"
            fi
            ;;
    esac
    
    # Save current power mode
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
            elif [ "$CURRENT_LEVEL" -gt 60 ]; then
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
                notify-send "Battery Status" "${CURRENT_LEVEL}% - Charging" -i "battery-charging" -a "System" -u normal
                log_message "Sent charging notification"
                ;;
            "Discharging"|"Not charging")
                notify-send "Battery Status" "${CURRENT_LEVEL}% - Discharging" -i "battery" -a "System" -u normal
                log_message "Sent discharging notification"
                ;;
        esac
    fi

    # Check for low battery
    if [[ "$CURRENT_LEVEL" -le 30 && "$CURRENT_STATUS" == "Discharging" ]]; then
        if [[ "$LOW_NOTIFIED" != "true" || "$PREV_LEVEL" -gt 30 || "$PREV_STATUS" != "Discharging" ]]; then
            notify-send "Battery Status" "${CURRENT_LEVEL}% - Low Battery" -i "battery-low" -a "System" -u critical
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
