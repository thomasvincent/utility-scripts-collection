#!/bin/bash
#
# Adds devices to Zenoss from an input file and configures their IPs.
#
# This script reads device information from a file and adds them to Zenoss,
# then updates their IP addresses after confirming the background tasks 
# have completed.

# Constants
readonly NEW_DEVICE_CLASS="/Ping"
readonly NEW_DEVICE_COLLECTOR="SpecialCollector"
readonly HOSTS_FILENAME="input.txt"
readonly SEPARATOR="=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*="

# Source the Zenoss API functions
. zenoss_api.sh

# Function to add devices to Zenoss
function add_devices() {
  while read -r line_ip line_host; do
    local api_call="{\"deviceName\": \"${line_host}\", \"title\":\"${line_host}\",\"deviceClass\": \"${NEW_DEVICE_CLASS}\", \"collector\": \"${NEW_DEVICE_COLLECTOR}\"}"
    zenoss_api device_router DeviceRouter addDevice "${api_call}"
    echo "${resp}"
  done < "${HOSTS_FILENAME}"
}

# Function to update device IPs
function update_device_ips() {
  local hashcheck=1
  
  while read -r line_ip line_host; do
    local api_call="{\"hashcheck\":${hashcheck},\"uids\":\"/zport/dmd/Devices${NEW_DEVICE_CLASS}/devices/${line_host}\", \"ip\":\"${line_ip}\"}"
    echo "${api_call}"
    zenoss_api device_router DeviceRouter resetIp "${api_call}"   
    echo "${resp}"
  done < "${HOSTS_FILENAME}"
}

# Main execution

# Step 1: Add devices
add_devices

# Pause for background tasks to complete
echo "${SEPARATOR}"
echo "At this step you should be sure that zenoss background task for devices add has finished running"
echo "If you open infrastructure dashboard, you will be able to see how many background jobs are pending"
echo "Check your zenoss instance then press enter"
read -r
echo "${SEPARATOR}"

# Step 2: Get devices and generate hash
api_call="{\"uid\":\"/zport/dmd/Devices${NEW_DEVICE_CLASS}\", \"limit\": 100000, \"params\": {}, \"sort\":\"name\"}"
zenoss_api device_router DeviceRouter getDevices "${api_call}"
echo "========="
# The following line is commented out as the hashcheck is hardcoded below
# HASHCHECK=$(echo "${resp}" | jsawk 'return this.result.hash')
echo "========="

# Step 3: Update device IPs
update_device_ips

