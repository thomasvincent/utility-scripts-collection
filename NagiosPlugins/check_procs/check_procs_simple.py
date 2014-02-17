#!/opt/zenoss/bin/python

#Script dependencies:
# pynag, subprocess

import os,sys, subprocess, re
from pynag.Plugins import WARNING, CRITICAL, OK, UNKNOWN, simple as Plugin
from pexpect import ANSI, fdpexpect, FSM, pexpect, pxssh, screen

#Create the plugin option
np = Plugin()

#Configure additional command line arguments
np.add_arg("R", "ssh_host", "Ssh remote machine name to connect to", required=True)
np.add_arg("p", "ssh_password", "Ssh romote host password", required=None)
np.add_arg("u", "ssh_username", "Ssh remote username", required=None)
np.add_arg("P", "ssh_port", "Ssh remote host port (default: 22)", required=None)
np.add_arg("n", "process_name", "Process name to check", required=True)
#Plugin activation
np.activate()



#SSH Section
ssh_port=22
result_ssh=''
if np['ssh_port']:
    ssh_port = np['ssh_port']
else:
    ssh_port = 22

ssh_username= "zenoss"
if np['ssh_username']:
    ssh_username = np['ssh_username']
else:
    ssh_username = "zenoss"

if not np['warning']:
    np['warning'] = 0
if not np['critical']:
    np['critical'] = 0

def mycheck(value):
    #print value
    if value > int(np['critical']):
        print "DNS CRITICAL - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(2)
    if int(np['warning']) == 0 and int(np['critical']) == 0:
        print "DNS CRITICAL - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(2)
    if value in range(int(np['warning']),int(np['critical']),1):
        print "DNS WARNING - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(1)
    if value in range(int(np['critical']),int(np['warning']),-1):
        print "DNS WARNING - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(1)
    if value < int(np['warning']) and value < int(np['critical']):
        print "DNS OK - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(0)
    if not np['warning'] and value < int(np['critical']):
        print "DNS OK - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(0)
    if value > int(np['warning']) and not np['critical']:
        print "DNS WARNING - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(1)
    if not np['critical'] and value < int(np['warning']):
        print "DNS OK - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        exit(0)
    pass

ss = pxssh.pxssh()
COMMANDLINE = "ps -ef | grep "+np['process_name']+" | wc -l"
try:
    if np['ssh_password']:
        ss.login(server=np['ssh_host'], username=ssh_username, password=np['ssh_password'], port=ssh_port)
    else:
        ss.login(server=np['ssh_host'], username=ssh_username, port=ssh_port)
    ss.sendline(COMMANDLINE)
    ss.prompt()
    DIG_RESULT = ss.before
    process_cnt = int(re.compile('(\d+)').search(DIG_RESULT).group(1))
    mycheck(process_cnt)
    #print DIG_RESULT

    ##############################################################################
    ss.logout()
except pxssh.ExceptionPxssh, e:
    print "UNKNOWN - ",e
    exit(3)
