#!/bin/bash

# Function to check for command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if ethtool exists
if ! command_exists ethtool; then
    echo "Error: ethtool command not found." >&2
    exit 1
fi

# Get network interfaces
interfaces=$(ifconfig | grep -Ev '^lo:' | awk '{print $1}')

for interface_name in $interfaces; do  # More descriptive variable
    speed=$(ethtool "$interface_name" | grep Speed | awk '{print $2}')

    if [[ -n "$speed" ]]; then
        # Handle potential variations in speed units
        if [[ $speed == *"Mbit/s"* ]]; then
            mbps=$(echo "$speed" | sed 's/Mbit\/s//') # Remove Mbit/s
            mbps=$(( mbps * 1000 ))  
        elif [[ $speed == *"Gbit/s"* ]]; then
            # Handle Gbit/s if needed
            echo "Handling Gbit/s conversion for $interface_name" 
        else
            echo "Unknown speed units for $interface_name" 
        fi

        # Output with comments
        echo "interface $interface_name 6 $mbps"  # Add comments explaining the values
    else
        echo "Error: Could not get speed for $interface_name" >&2
    fi
done
