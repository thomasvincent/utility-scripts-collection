#!/bin/bash
#
# Checks Vertica database for various potential issues
#
# This script connects to a Vertica database and checks for:
# - DOWN nodes
# - Too Many ROS Containers events
# - Recovery Failure events
# - Stale Checkpoint events
#
# Usage: ./check_counters_db.sh

# Database connection credentials
readonly DB_USER="zenoss"
readonly DB_PASS="blah"
readonly DB_HOST="vertica01"
readonly VSQL="/opt/vertica/bin/vsql"

# Function to execute a query and extract the count
function run_query() {
  local query="$1"
  local result

  # Run the query
  local output
  output=$("${VSQL}" -h "${DB_HOST}" -U "${DB_USER}" -w "${DB_PASS}" -c "${query}")
  
  # Extract numeric result
  result=$(echo "${output}" | sed "s/[^0-9]/ /g" | cut -d' ' -f1)
  echo "${result}"
}

# Main execution

# Check for DOWN nodes
nodes_down_query="select count(*) from nodes where node_state = 'DOWN';"
nodes_down=$(run_query "${nodes_down_query}")
echo "DOWN nodes: ${nodes_down}"

# Check for Too Many ROS Containers events
ros_events_query="select count(*) from active_events where event_code_description = 'Too Many ROS Containers';"
ros_events=$(run_query "${ros_events_query}")
echo "Too Many ROS Containers events: ${ros_events}"

# Check for Recovery Failure events
recovery_events_query="select count(*) from active_events where event_code_description = 'Recovery Failure';"
recovery_events=$(run_query "${recovery_events_query}")
echo "Recovery Failure events: ${recovery_events}"

# Check for Stale Checkpoint events
checkpoint_events_query="select count(*) from active_events where event_code_description = 'Stale Checkpoint';"
checkpoint_events=$(run_query "${checkpoint_events_query}")
echo "Stale Checkpoint events: ${checkpoint_events}"