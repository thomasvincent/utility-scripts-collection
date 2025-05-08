#!/bin/bash
#
# Zenoss API utility function for shell scripts.
#
# Provides a function to connect to the Zenoss JSON API using curl.
# This script should be sourced by other scripts that need to interact
# with the Zenoss API.

# Your Zenoss settings
readonly ZENOSS_URL="http://192.168.171.128:8080"
readonly ZENOSS_USERNAME="admin"
readonly ZENOSS_PASSWORD="zenoss"

# Generic call to make Zenoss JSON API calls easier on the shell.
# 
# Usage:
#   zenoss_api <endpoint> <action> <method> <data>
#
# Args:
#   endpoint: The API endpoint (router) to use (e.g., device_router)
#   action: The router action name (e.g., DeviceRouter)
#   method: The method to call on the router (e.g., addDevice)
#   data: JSON data to pass to the method
#
# Returns:
#   Sets the global variable resp with the API response
function zenoss_api() {
  local router_endpoint="$1"
  local router_action="$2"
  local router_method="$3"
  local data="$4"

  if [[ -z "${data}" ]]; then
    echo "Usage: zenoss_api <endpoint> <action> <method> <data>"
    return 1
  fi

  resp=$(curl \
    -s \
    -u "${ZENOSS_USERNAME}:${ZENOSS_PASSWORD}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"action\":\"${router_action}\",\"method\":\"${router_method}\",\"data\":[${data}], \"tid\":1}" \
    "${ZENOSS_URL}/zport/dmd/${router_endpoint}")
}