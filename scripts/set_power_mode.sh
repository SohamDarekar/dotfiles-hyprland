#!/bin/bash

MODE="${1:-performance}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_power_mode_actions.sh"

BAT=$(cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1 || echo "?")

ICON_POWERSAVE="/usr/share/icons/Papirus/24x24/panel/battery-low.svg"
ICON_ULTRA="/usr/share/icons/Papirus/24x24/panel/battery-caution.svg"
ICON_PERFORMANCE="/usr/share/icons/Papirus/24x24/panel/battery-good.svg"
ICON_FULL="/usr/share/icons/Papirus/24x24/panel/battery-full.svg"

case "$MODE" in
    powersave)
        echo "powersave" > /tmp/ax_manual_power_mode
        _apply_power_actions powersave
        notify-send "Power Saving" "Battery: ${BAT}%" -i "$ICON_POWERSAVE" -a "System"
        ;;
    ultra-powersave)
        echo "ultra-powersave" > /tmp/ax_manual_power_mode
        _apply_power_actions ultra-powersave
        notify-send "Ultra Power Saving" "Battery: ${BAT}%" -i "$ICON_ULTRA" -a "System"
        ;;
    performance)
        echo "performance" > /tmp/ax_manual_power_mode
        _apply_power_actions performance
        notify-send "Performance Mode" "Battery: ${BAT}%" -i "$ICON_PERFORMANCE" -a "System"
        ;;
    disabled)
        echo "disabled" > /tmp/ax_manual_power_mode
        _apply_power_actions disabled
        notify-send "Power Saving Disabled" "Battery: ${BAT}%" -i "$ICON_FULL" -a "System"
        ;;
    auto)
        rm -f /tmp/ax_manual_power_mode
        notify-send "Auto Power Mode" "Battery: ${BAT}%" -i "$ICON_PERFORMANCE" -a "System"
        ;;
esac
