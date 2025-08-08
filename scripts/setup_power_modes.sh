#!/bin/bash

# Make scripts executable
chmod +x ~/.config/Ax-Shell/scripts/battery-monitor.sh

# Create sudoers entry for CPU frequency scaling without password
echo "Creating sudoers entry for power management..."
sudo tee /etc/sudoers.d/power-management << INNER_EOF
# Allow user to change CPU frequency scaling without password
$USER ALL=(root) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
$USER ALL=(root) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/cpu*/online
INNER_EOF

# Verify required tools are installed
if ! command -v brightnessctl &> /dev/null; then
    echo "Installing brightnessctl..."
    # For Arch-based systems
    if command -v pacman &> /dev/null; then
        sudo pacman -S brightnessctl
    # For Debian/Ubuntu-based systems
    elif command -v apt &> /dev/null; then
        sudo apt install brightnessctl
    fi
fi

echo "Setup complete! Restart Hyprland to apply changes."
