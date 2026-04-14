#!/bin/bash

MODE="${1:-performance}"
BAT=$(cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1 || echo "?")

ICON_POWERSAVE="/usr/share/icons/Papirus/24x24/panel/battery-low.svg"
ICON_ULTRA="/usr/share/icons/Papirus/24x24/panel/battery-caution.svg"
ICON_PERFORMANCE="/usr/share/icons/Papirus/24x24/panel/battery-good.svg"
ICON_FULL="/usr/share/icons/Papirus/24x24/panel/battery-full.svg"

case "$MODE" in
    powersave)
        echo "powersave" > /tmp/ax_manual_power_mode
        echo "powersave" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
        command -v brightnessctl > /dev/null && brightnessctl set 50% > /dev/null 2>&1
        notify-send "Power Saving" "Battery: ${BAT}%" -i "$ICON_POWERSAVE" -a "System"
        ;;
    ultra-powersave)
        echo "ultra-powersave" > /tmp/ax_manual_power_mode
        echo "powersave" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
        for cpu in {1..3}; do echo 0 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; done
        command -v brightnessctl > /dev/null && brightnessctl set 20% > /dev/null 2>&1
        notify-send "Ultra Power Saving" "Battery: ${BAT}%" -i "$ICON_ULTRA" -a "System"
        ;;
    performance)
        echo "performance" > /tmp/ax_manual_power_mode
        echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
        for cpu in {1..7}; do echo 1 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; done
        command -v brightnessctl > /dev/null && brightnessctl set 80% > /dev/null 2>&1
        notify-send "Performance Mode" "Battery: ${BAT}%" -i "$ICON_PERFORMANCE" -a "System"
        ;;
    disabled)
        echo "disabled" > /tmp/ax_manual_power_mode
        echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
        for cpu in {1..7}; do echo 1 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; done
        command -v brightnessctl > /dev/null && brightnessctl set 80% > /dev/null 2>&1
        notify-send "Power Saving Disabled" "Battery: ${BAT}%" -i "$ICON_FULL" -a "System"
        ;;
    auto)
        rm -f /tmp/ax_manual_power_mode
        notify-send "Auto Power Mode" "Battery: ${BAT}%" -i "$ICON_PERFORMANCE" -a "System"
        ;;
esac
