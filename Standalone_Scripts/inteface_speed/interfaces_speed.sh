#!/bin/bash

# This script checks for the presence of the 'ethtool' utility, lists non-loopback network interfaces,
# retrieves their speeds, and processes these speeds into a standard format.

# Function to check for command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if ethtool exists
if ! command_exists ethtool; then
    echo "Error: 'ethtool' command not found." >&2
    exit 1
fi

# Get network interfaces excluding the loopback interface
interfaces=$(ifconfig | grep -Ev '^lo' | awk '{print $1}')

for interface_name in $interfaces; do  # Iterate through each interface
    speed=$(ethtool "$interface_name" | grep 'Speed:' | awk '{print $2}')

    if [[ -n "$speed" ]]; then
        if [[ "$speed" == *"Mb/s"* ]]; then
            # Extract and convert Mbit/s to kbit/s
            mbps=$(echo "$speed" | sed 's/Mb\/s//')  # Remove 'Mb/s'
            kbps=$(( mbps * 1000 ))  # Convert Mbit/s to kbit/s
            echo "Interface $interface_name has a speed of $kbps kbit/s."
        elif [[ "$speed" == *"Gb/s"* ]]; then
            # Extract and convert Gbit/s to kbit/s
            gbps=$(echo "$speed" | sed 's/Gb\/s//')  # Remove 'Gb/s'
            kbps=$(( gbps * 1000000 ))  # Convert Gbit/s to kbit/s
            echo "Interface $interface_name has a speed of $kbps kbit/s."
        else
            echo "Unknown speed units for $interface_name."
        fi
    else
        echo "Error: Could not get speed for $interface_name." >&2
    fi
done
