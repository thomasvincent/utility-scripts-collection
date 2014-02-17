#!/bin/bash

# Provides a function to connect to the Zenoss JSON API using curl.

# Your Zenoss settings.
ZENOSS_URL="http://localhost:8080"
ZENOSS_USERNAME="admin"
ZENOSS_PASSWORD="zenoss"

# Generic call to make Zenoss JSON API calls easier on the shell.
zenoss_api () {
    ROUTER_ENDPOINT=$1
    ROUTER_ACTION=$2
    ROUTER_METHOD=$3
    DATA=$4

    if [ -z "${DATA}" ]; then
        echo "Usage: zenoss_api <endpoint> <action> <method> <data>"
        return 1
    fi

    resp=`curl \
        -s \
        -u "$ZENOSS_USERNAME:$ZENOSS_PASSWORD" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"action\":\"$ROUTER_ACTION\",\"method\":\"$ROUTER_METHOD\",\"data\":[$DATA], \"tid\":1}" \
        "$ZENOSS_URL/zport/dmd/$ROUTER_ENDPOINT"`
}