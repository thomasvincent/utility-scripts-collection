#!/bin/bash

# Get a list of network interfaces (excluding loopback)
interfaces=( $(ifconfig | grep -Ev '^lo:' | awk '{print $1}') )

# Loop through each interface
for interface in "${interfaces[@]}"; do
  # Get the link speed using ethtool (handle potential errors)
  speed=$(ethtool "$interface" | grep Speed | awk -F':' '{print $2}' || true)

  # Check if speed is retrieved successfully
  if [[ -n "$speed" ]]; then
    # Convert speed to Mbps (assuming Mbit/s format)
    mbps=$(( speed * 1000000 ))
    echo "interface $interface 6 $mbps"  # Assuming format "interface <name> <duplex> <speed>"
  fi
done
