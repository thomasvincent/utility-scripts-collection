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
np.add_arg("P", "ssh_password", "Ssh romote host password", required=None)
np.add_arg("U", "ssh_username", "Ssh remote username", required=None)
np.add_arg("s", "ssh_port", "Ssh remote host port (default: 22)", required=None)
np.add_arg("l", "query_address", "Machine name to lookup", required=True)
np.add_arg("p", "port", "DNS Server port number (default: 53)", required=None)
np.add_arg("T", "record_type", "Record type to lookup (default: A)", required=None)
np.add_arg("a", "expected_address", "An address expected to be in the answer section. If not set, uses whatever was in query address", required=None)
np.add_arg("A", "dig-arguments", "Pass the STRING as argument(s) to dig", required=None)

#Plugin activation
np.activate()

#Main script logic 8-)
CMD_ITEM_1 = "dig"
CMD_ITEM_2 = " "             #Here we should insert a servername/ip
CMD_ITEM_3 = " "        #Here should be the port for a server/ip (default: 53)
CMD_ITEM_4 = " "             #Machine name to lookup
CMD_ITEM_5 = " "            #Record type
CMD_ITEM_6 = " "             #Dig additional args

#Data gathering
if np['query_address']:
    CMD_ITEM_4 = np['query_address']

if  (np['host'] and np['port']):
    CMD_ITEM_2 = "@"+np['host']
    CMD_ITEM_3 = "-p "+np['port']

if np['record_type']:
    CMD_ITEM_5 = "-t "+np['record_type']

if np['dig-arguments']:
    CMD_ITEM_6 = np['dig-arguments']


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
    if value > int(np['critical']) and np['critical']:
        print "DNS CRITICAL - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(2)
    if int(np['warning']) == 0 and int(np['critical']) == 0:
        print "DNS CRITICAL - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(2)
    if value in range(int(np['warning']),int(np['critical']),1):
        print "DNS WARNING - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(1)
    if value in range(int(np['critical']),int(np['warning']),-1):
        print "DNS WARNING - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(1)
    if value < int(np['warning']) and value < int(np['critical']):
        print "DNS OK - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(0)
    if not np['warning'] and value < int(np['critical']):
        print "DNS OK - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(0)
    if value > int(np['warning']) and not np['critical']:
        print "DNS WARNING - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(1)
    if not np['critical'] and value < int(np['warning']):
        print "DNS OK - "+str(value)+"s response time|time="+str(value)+"s;"+str(float(np['warning']))+";;"+str(float(np['critical']))
        sys.exit(0)


DIG_COMMANDLINE = CMD_ITEM_1+CMD_ITEM_2+CMD_ITEM_3+CMD_ITEM_4+CMD_ITEM_5+CMD_ITEM_6

ss = pxssh.pxssh()
try:
    if np['ssh_password']:
        ss.login(server=np['ssh_host'], username=ssh_username, password=np['ssh_password'], port=ssh_port)
    else:
        ss.login(server=np['ssh_host'], username=ssh_username, port=ssh_port)
    ss.sendline(DIG_COMMANDLINE)
    ss.prompt()
    DIG_RESULT = ss.before
    #print DIG_RESULT
    ########################### main logic #######################################
    #Step 1: If expected address is set, searching it in the DIG_RESULT
    if np["expected_address"]:
        #Step 2: Check if there is an ANSWER secton
        if "ANSWER SECTION" in DIG_RESULT:
            expaddr = np['expected_address']
            if (expaddr in DIG_RESULT):
                #Step 2: Expected address has been found, so now we can check the range...
                #First of all, we need to obtain a "QUERY TIME" from the DIG_ANSWER
                number_regex_msec = re.compile(' (\d+) msec')
                number_regex_sec  = re.compile(' (\d+) sec')
                secdata = 0
                if number_regex_sec.search(DIG_RESULT):
                    secdata = number_regex_sec.search(DIG_RESULT).group(1)
                    mycheck(secdata)
                else:
                    if number_regex_msec.search(DIG_RESULT):
                        secdata = number_regex_msec.search(DIG_RESULT).group(1)
                        secdata = int(secdata) * 0.001
                        mycheck(secdata)
                    else:
                        print "DNS WARNING - Dig returned an error status|time=0s;"+str(np['warning'])+";;"+str(np['critical'])
                        sys.exit(1)

            else:
                print "DNS WARNING - Dig returned an error status|time=0s;"+str(np['warning'])+";;"+str(np['critical'])
                sys.exit(1)
        else:
            expaddr = np['expected_address']
            if (expaddr in DIG_RESULT):
                #Step 2: Expected address has been found, so now we can check the range...
                #First of all, we need to obtain a "QUERY TIME" from the DIG_ANSWER
                number_regex_msec = re.compile(' (\d+) msec')
                number_regex_sec  = re.compile(' (\d+) sec')
                secdata = 0
                if number_regex_sec.search(DIG_RESULT):
                    secdata = number_regex_sec.search(DIG_RESULT).group(1)
                else:
                    if number_regex_msec.search(DIG_RESULT):
                        secdata = number_regex_msec.search(DIG_RESULT).group(1)
                        secdata = int(secdata) * 0.001
                    else:
                        print "DNS WARNING - Dig returned an error status|time=0s;"+str(np['warning'])+";;"+str(np['critical'])
                        sys.exit(1)
            print "DNS CRITICAL - ",secdata,"s response time (No ANSWER Section found)|time=",secdata,"s;",+str(np['warning'])+";;"+str(np['critical'])
            sys.exit(2)
    else:
        number_regex_msec = re.compile(' (\d+) msec')
        number_regex_sec  = re.compile(' (\d+) sec')
        secdata = 0
        if number_regex_sec.search(DIG_RESULT):
            secdata = number_regex_sec.search(DIG_RESULT).group(1)
            mycheck(secdata)
        else:
            if number_regex_msec.search(DIG_RESULT):
                secdata = number_regex_msec.search(DIG_RESULT).group(1)
                secdata = int(secdata) * 0.001
                mycheck(secdata)
            else:
                print "DNS WARNING - Dig returned an error status|time=0s;"+str(np['warning'])+";;"+str(np['critical'])
                sys.exit(1)
    ##############################################################################
    ss.logout()
except pxssh.ExceptionPxssh, e:
    print "UNKNOWN - ",e
    sys.exit(3)
