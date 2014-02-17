#!/opt/zenoss/bin/python

import sys, os
import subprocess as sp
import shlex
############################################################################################################

def main():
    cmd1 = """select count(*) from nodes where node_state = 'DOWN';"""
    cmd2 = """select count(*) from active_events where event_code_description = 'Too Many ROS Containers';"""
    cmd3 = """select count(*) from active_events where event_code_description = 'Recovery Failure';"""
    cmd4 = """select count(*) from active_events where event_code_description = 'Stale Checkpoint';"""

    cmd1_prepared = "/opt/vertica/bin/vsql -h vertica01 -U zenoss -w blahbalh -c" + cmd1
    cmd1_prepared = shlex.split(cmd1_prepared)

    cmd2_prepared = "/opt/vertica/bin/vsql -h vertica01 -U zenoss -w blahbalh -c" + cmd2
    #cmd2_prepared = shlex.split(cmd2_prepared)

    cmd3_prepared = "/opt/vertica/bin/vsql -h vertica01 -U zenoss -w blahbalh -c" + cmd3
    #cmd3_prepared = shlex.split(cmd3_prepared)

    cmd4_prepared = "/opt/vertica/bin/vsql -h vertica01 -U zenoss -w blahbalh -c" + cmd4
    #cmd4_prepared = shlex.split(cmd4_prepared)

    vertica = sp.Popen(cmd1_prepared, stdout=sp.PIPE, stderr=sp.PIPE)
    result1 = vertica.stdout.read()

    vertica = sp.Popen(cmd2_prepared, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    result2 = vertica.stdout.read()

    vertica = sp.Popen(cmd3_prepared, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    result3 = vertica.stdout.read()

    vertica = sp.Popen(cmd4_prepared, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    result4 = vertica.stdout.read()

    print "R1 :", result1
    print "R2 :", result2
    print "R3 :", result3
    print "R4 :", result4

    sys.exit(1)
    '''
    if result1 == 0 and result2 == 0 and result3 == 0 and result4 == 0:
        print "COUNTERS OK - No errors found"
        sys.exit(0)
    else:
        if result1 != 0:
            print "COUNTERS WARNING - There are %s nodes has state DOWN." % (result1)
            sys.exit(1)
        else:
            if result2 != 0:
                print "COUNTERS WARNING - There are %s events 'Too Many ROS Containers' present." % (result2)
                sys.exit(1)
            else:
                if result3 != 0:
                    print "COUNTERS WARNING - There are %s events 'Recovery failure' present." % (result3)
                    sys.exit(1)
                else:
                    if result4 != 0:
                        print "COUNTERS WARNING - There are %s events 'Stale Checkpoint' present." % (result4)
                        sys.exit(1)

'''
main()