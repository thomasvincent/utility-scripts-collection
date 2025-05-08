#!/bin/bash
#
# Nagios plugin to check Scribe service status
#
# Usage:
#   check_scribe SSH_USERNAME SSH_HOST
#
# Returns Nagios-compliant exit codes based on the Scribe service status.

# Nagios exit codes
readonly NAGIOS_OK=0
readonly NAGIOS_WARNING=1
readonly NAGIOS_CRITICAL=2
readonly NAGIOS_UNKNOWN=3

# Scribe service states mapped to Nagios codes
readonly SCRIBE_OK="ALIVE"
readonly SCRIBE_WARNING="WARNING"
readonly SCRIBE_CRITICAL="[(STARTING)(STOPPING)(STOPPED)(DEAD)(Failed to get status)]"

# Validate command line arguments
if [[ $# -ne 2 ]]; then
  echo "UNKNOWN - Usage: $0 SSH_USERNAME SSH_HOST"
  exit "${NAGIOS_UNKNOWN}"
fi

# Get Scribe status via SSH
ssh_command="ssh $1@$2 /usr/sbin/scribe_ctrl status"
echo "${ssh_command}"

status_output=$(${ssh_command})

# Check status against known states
if [[ "${status_output}" =~ ${SCRIBE_OK} ]]; then
  echo "OK - Scribe service is alive"
  exit "${NAGIOS_OK}"
elif [[ "${status_output}" =~ ${SCRIBE_WARNING} ]]; then
  echo "WARNING - ${status_output}"
  exit "${NAGIOS_WARNING}"
elif [[ "${status_output}" =~ ${SCRIBE_CRITICAL} ]]; then
  echo "CRITICAL - Scribe service is not running"
  exit "${NAGIOS_CRITICAL}"
else
  echo "UNKNOWN - Scribe daemon is in an unexpected state: ${status_output}"
  exit "${NAGIOS_UNKNOWN}"
fi

