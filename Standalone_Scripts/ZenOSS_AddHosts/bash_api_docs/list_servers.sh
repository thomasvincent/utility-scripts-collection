#!/bin/bash
#
# Lists Zenoss servers using the JSON API.
#
# This script demonstrates using the Zenoss JSON API to retrieve and display
# a list of server devices with their IP addresses.
#
# Example output:
# [
#    "austinbot.zenoss.loc (10.87.209.6)",
#    "osx105b.zenoss.loc (10.204.210.24)",
#    "test-aix53-1.zenoss.loc (10.175.210.227)",
#    "test-aix53-2.zenoss.loc (10.175.210.228)",
#    "test-aix61.zenoss.loc (10.175.210.229)"
# ]
#
# Dependencies:
#   - jsawk (https://github.com/micha/jsawk)
#   - spidermonkey (yum install js)
#   - perl JSON module (for pprint.sh)
#   - zenoss_api.sh utility script

# Source the Zenoss API utility functions
. zenoss_api.sh

# Set up parameters for the API call
readonly DEVICE_LIMIT=5
readonly DEVICE_UID="/zport/dmd/Devices/Server"
readonly API_PARAMS='{"uid": "'"${DEVICE_UID}"'", "limit": '"${DEVICE_LIMIT}"', "params": {}}'

# Call the API and process the results
zenoss_api device_router DeviceRouter getDevices "${API_PARAMS}"
echo "${resp}" | jsawk 'return this.result.devices' | \
  jsawk 'return this.name + " (" + this.ipAddressString + ")"' | \
  ./pprint.sh
