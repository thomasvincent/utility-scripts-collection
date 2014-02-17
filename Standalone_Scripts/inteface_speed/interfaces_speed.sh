#!/bin/bash

INTERFACE_LIST=`ifconfig | grep '^[a-z0-9]' | awk '{print $1}'`

arr=$(echo $INTERFACE_LIST | tr " " "\n")

for x in $arr
do
    SPEED=`ethtool $x | grep Speed | tr -d '[A-Za-z]' | tr -d ' ' | tr -d ':' | tr -d '/'  `
    if [ $SPEED ] ; then
	echo "interface "$x "6" $(($SPEED * 1000000))
    fi
done