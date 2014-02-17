#!/bin/sh

#USAGE
# check_scribe SSH_USERNAME SSH_HOST

# Nagios exit codes
nagios_ok=0
nagios_warning=1
nagios_critical=2
nagios_unknown=3

# Scribe service states mapped to Nagios codes
scribe_ok="ALIVE"
scribe_warning="WARNING"
scribe_critical="[(STARTING)(STOPPING)(STOPPED)(DEAD)(Failed to get status)]"

admin="ssh $1@$2 /usr/sbin/scribe_ctrl status"
echo $admin

rval=`$admin`

if [[ "$rval" =~ "$scribe_ok" ]]; then
        echo "OK"
        exit $nagios_ok

elif [[ "$rval" =~ "$scribe_warning" ]]; then
        echo "WARNING - $rval"

elif [[ "$rval" =~ "$scribe_critical" ]]; then
        echo "CRITICAL"
        exit $nagios_critical

else
        echo "UNKNOWN - Scribe dameon is in an unknown state: $rval"
        exit $nagios_unknown
fi


