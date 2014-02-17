#!/bin/bash

. zenoss_api.sh

#Get Devices
API_CALL_STRING='{"uid":"/zport/dmd/Devices", "limit": 1000000, "params": {}, "sort":"name"}'
#echo $API_CALL_STRING
zenoss_api device_router DeviceRouter getDevices "$API_CALL_STRING"
echo $resp | jsawk 'return this.result.devices' > ./tmpfile.txt