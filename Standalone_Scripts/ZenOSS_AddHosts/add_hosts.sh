#!/bin/bash
NEW_DEVICE_CLASS="/Ping"
NEW_DEVICE_COLLECTOR="SpecialCollector"
HOSTS_FILENAME="input.txt"

. zenoss_api.sh
cat $HOSTS_FILENAME | while read line_ip line_host; do
    API_CALL_STRING='{"deviceName": "'$line_host'", "title":"'$line_host'","deviceClass": "'$NEW_DEVICE_CLASS'", "collector": "'$NEW_DEVICE_COLLECTOR'"}'
    zenoss_api device_router DeviceRouter addDevice "$API_CALL_STRING"
    echo $resp
done


#Pause for user input
echo "=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*="
echo "At this step you should be sure that zenoss background task for devices add has finished running"
echo "Of you open infrastructure dashboard, you will be able to see how much backgorund jobs pending"
echo "Check your zenoss instance then press enter"
read
echo "=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*="


#Get Devices
API_CALL_STRING='{"uid":"/zport/dmd/Devices'$NEW_DEVICE_CLASS'", "limit": 100000, "params": {}, "sort":"name"}'
#echo $API_CALL_STRING
zenoss_api device_router DeviceRouter getDevices "$API_CALL_STRING"
echo "========="
HASHCHECK=`echo $resp | jsawk 'return this.result.hash'`
echo "========="
#list=`echo $resp | jsawk 'return this.result.devices' | jsawk  'return this.uid' | tr "," "\n" | tr -d "[" | tr -d "]"`

#updating ips
HASHCHECK=1
cat $HOSTS_FILENAME | while read line_ip line_host; do
    API_CALL_STRING='{"hashcheck":'$HASHCHECK',"uids":"/zport/dmd/Devices'$NEW_DEVICE_CLASS'/devices/'$line_host'", "ip":"'$line_ip'"}'
    echo $API_CALL_STRING
    zenoss_api device_router DeviceRouter resetIp "$API_CALL_STRING"   
    echo $resp
done

#####################################################
#. zenoss_api.sh
##echo $API_CALL_STRING

#zenoss_api device_router DeviceRouter addDevice "$API_CALL_STRING"
#echo $resp

