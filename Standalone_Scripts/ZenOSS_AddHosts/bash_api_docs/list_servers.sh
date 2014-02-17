#!/bin/bash

# An example of using the JSON API. Prints out five servers.
#
# $ ./list_devices.sh
# [
#    "austinbot.zenoss.loc (10.87.209.6)",
#    "osx105b.zenoss.loc (10.204.210.24)",
#    "test-aix53-1.zenoss.loc (10.175.210.227)",
#    "test-aix53-2.zenoss.loc (10.175.210.228)",
#    "test-aix61.zenoss.loc (10.175.210.229)"
# ]
#
# Requires jsawk (https://github.com/micha/jsawk)
#      and spidermonkey (yum install js)
#      and the perl JSON module

. zenoss_api.sh
zenoss_api device_router DeviceRouter getDevices '{"uid": "/zport/dmd/Devices/Server", "limit": 5, "params": {}}'
echo $resp | jsawk 'return this.result.devices' | jsawk 'return this.name + " (" + this.ipAddressString + ")"' | ./pprint.sh
