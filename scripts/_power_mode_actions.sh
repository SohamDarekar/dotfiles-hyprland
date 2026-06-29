#!/bin/bash
# Shared power mode system actions (governor, cores, brightness).
# Source this file; call: _apply_power_actions <mode>

_apply_power_actions() {
    local mode=$1
    case "$mode" in
        performance|disabled)
            echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1
            for cpu in {1..7}; do echo 1 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; done
            command -v brightnessctl > /dev/null && brightnessctl set 100% > /dev/null 2>&1
            ;;
        powersave)
            echo "powersave" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1
            command -v brightnessctl > /dev/null && brightnessctl set 50% > /dev/null 2>&1
            ;;
        ultra-powersave)
            echo "powersave" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1
            for cpu in {1..3}; do echo 0 | sudo tee /sys/devices/system/cpu/cpu$cpu/online > /dev/null 2>&1; done
            command -v brightnessctl > /dev/null && brightnessctl set 20% > /dev/null 2>&1
            ;;
    esac
}
