#!/bin/bash

USER="zenoss"
PASS="blah"

cmd1=`/opt/vertica/bin/vsql -h vertica01 -U $USER -w $PASS -c "select count(*) from nodes where node_state = 'DOWN';"`
cmd2=`/opt/vertica/bin/vsql -h vertica01 -U $USER -w $PASS -c "select count(*) from active_events where event_code_description = 'Too Many ROS Containers';"`
cmd3=`/opt/vertica/bin/vsql -h vertica01 -U $USER -w $PASS -c "select count(*) from active_events where event_code_description = 'Recovery Failure';"`
cmd4=`/opt/vertica/bin/vsql -h vertica01 -U $USER -w $PASS -c "select count(*) from active_events where event_code_description = 'Stale Checkpoint';"`

#echo $cmd1
#echo $cmd2
#echo $cmd3
#echo $cmd4

#str="count\n   ----- \n    0   \n (1 row) \n"
#newstr=$(echo "$str" | sed "s/[^0-9]/ /g")
#echo $(echo $newstr | cut -d' ' -f1)
result1=$(echo "$cmd1" | sed "s/[^0-9]/ /g" | cut -d' ' -f1)
echo $result1

result2=$(echo "$cmd2" | sed "s/[^0-9]/ /g" | cut -d' ' -f1)
echo $result2

result3=$(echo "$cmd3" | sed "s/[^0-9]/ /g" | cut -d' ' -f1)
echo $result3

result4=$(echo "$cmd4" | sed "s/[^0-9]/ /g" | cut -d' ' -f1)
echo $result4