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
np.add_arg("m", "metric", "Check thresholds against metric. Valid types:\n \
                          PROCS   - number of processes (default)", required=False)
#np.add_arg("m", "metric", "Check thresholds against metric. Valid types:\n \
#                          PROCS   - number of processes (default)\n \
#                          VSZ     - virtual memory size\n \
#                          RSS     - resident set memory size\n \
#                          CPU     - percentage CPU\n \
#                          ELAPSED - time elapsed in seconds", required=None)
np.add_arg("s", "statusflags", "Only scan for processes that have, in the output of `ps` one or\n \
more of the status flags you specify (for example R,Z,S,RS,\n \
RSZDT, plus others bused on the output of your `ps` command)", required=None)
np.add_arg("i", "ppid", "Only scan for children of the parent process ID indicated", required=None)
np.add_arg("z", "vsz", "Only scan for processes with VSZ higher than indicated", required=None)
np.add_arg("r", "rss", "Only scan for processes with RSS higher than indicated", required=None)
np.add_arg("o", "pcpu", "Only scan for processes with PCPU higher than indicated", required=None)
np.add_arg("y", "user", "Only scan fro processes with user name or ID indicated", required=None)
np.add_arg("n", "command", "Process name or command to scan", required=True)
#np.add_arg("a", "arguments-array", "Only scan for processes with args that contain STRING", required=None)
#np.add_arg("e", "ereg-argument-array", "Only scan for processes with args that contain the regex STRING", required=None)
#Plugin activation
np.activate()

#Internal functions declaration ########################################################################################
def transform_lines_into_dict(lineslist):
    source = lineslist
    result = []
    for each in source:
        if len(each) >=7:
            newdict = {}
            newdict['uid'] = each[0]
            newdict['pid'] = each[1]
            newdict['parentpid'] = each[2]
            newdict['vsz'] = each[3]
            newdict['rss'] = each[4]
            newdict['status'] = each[5]
            newdict['time'] = each[6]
            newdict['pcpu'] = each[7]
            result.append(newdict)
    return result
########################################################################################################################
def testflags(flags_array, process_flags):
    process_flags_array = []
    for each in process_flags:
        process_flags_array.append(each)

    result = False
    for each in flags_array:
        if each in process_flags_array:
            result = True
            break
    return result
########################################################################################################################
def perfdata(value_count, count_min, count_max):
    stro = "|"
    stro = stro + "count="+str(value_count)+";"
    return stro
#End of internal functions declaration #################################################################################

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


SSH_COMMAND = "ps -C \""+np['command']+"\" -o uid,pid,ppid,vsz,rss,stat,bsdtime,pcpu,comm"
#Get the PS output and process it
ss = pxssh.pxssh()
try:
    if np['user']:
        if np['user'].isdigit():
            SSH_COMMAND = SSH_COMMAND + " -U " + np['user']
        else:
            SSH_COMMAND = SSH_COMMAND + " -u " + np['user']

    if np['ssh_password']:
        ss.login(server=np['ssh_host'], username=ssh_username, password=np['ssh_password'], port=ssh_port)
    else:
        ss.login(server=np['ssh_host'], username=ssh_username, port=ssh_port)
    ss.sendline(SSH_COMMAND)
    ss.prompt()
    result_ssh = ss.before
    result_lines = result_ssh.split('\n')
    del result_lines[0]
    del result_lines[0]
    result_ssh = []
    for each in result_lines:
        result_ssh.append(re.sub(' +',' ',each).split())

    result_ssh = transform_lines_into_dict(result_ssh)
    ss.logout()
    #print result_ssh
    #Appying the first filter - status flag, if needed.
    if  np['statusflags']:
        source=result_ssh
        result = []
        flags_arr = np['statusflags'].split(',')
        for each in source:
            if testflags(flags_arr, each['status']):
                result.append(each)
        result_ssh = result

    #Applying the second filter - parent pid filter if needed
    if np['ppid']:
        source=result_ssh
        result = []
        for each in source:
            if np['ppid'] == each['parentpid']:
                result.append(each)
        result_ssh = result

    #Applying the last numberic filters
    if np['vsz']:
        source=result_ssh
        result = []
        for each in source:
            if np['vsz'] < each['vsz']:
                result.append(each)
        result_ssh = result

    if np['rss']:
        source=result_ssh
        result = []
        for each in source:
            if np['rss'] < each['rss']:
                result.append(each)
        result_ssh = result

    if np['pcpu']:
        source=result_ssh
        result = []
        for each in source:
            if np['pcpu'] < each['pcpu']:
                result.append(each)
        result_ssh = result
    #end of filters...
    ####################################################################################################################
    #    #Here we should check the procs
    flag_warning = False
    flag_critical = False
    proc_count = len(result_ssh)
    warn_limit = np['warning']
    crit_limit = np['critical']
    if np['warning']:
        min = warn_limit.split(":")[0]
        max = warn_limit.split(":")[1]
        if min != '' and max != '':
           if int(min) > int(max):
                t = min
                min = max
                max = t
           if proc_count in range(int(min),int(max)):
               print "PROCS WARNING - "+str(proc_count)+" processes"+perfdata(proc_count,0,0)
               sys.exit(1)
        else:
            if min=='':     #Check if > max
                if proc_count > int(max):
                    print "PROCS WARNING - "+str(proc_count)+" processes"+perfdata(proc_count,0,0)
                    sys.exit(1)
            if max=='':     #Check if < min
                if proc_count < int(min):
                    print "PROCS WARNING - "+str(proc_count)+" processes"+perfdata(proc_count,0,0)
                    sys.exit(1)
    else:
        flag_warning = True

    if np['critical']:
        min = crit_limit.split(":")[0]
        max = crit_limit.split(":")[1]
        if min != '' and max != '':
            if int(min) > int(max):
                t = min
                min = max
                max = t
            if proc_count in range(int(min),int(max)):
                print "PROCS CRITICAL - "+str(proc_count)+" processes"+perfdata(proc_count,0,0)
                sys.exit(2)
        else:
            if min=='':     #Check if > max
                if proc_count > int(max):
                    print "PROCS CRITICAL - "+str(proc_count)+" processes"+perfdata(proc_count,0,0)
                    sys.exit(2)
            if max=='':     #Check if < min
                if proc_count < int(min):
                    print "PROCS CRITICAL - "+str(proc_count)+" processes"+perfdata(proc_count,0,0)
                    sys.exit(2)
    else:
        flag_critical = True

    if (flag_critical or flag_warning):
        print "PROCS WARNING - "+str(proc_count)+" processes not in range"+perfdata(proc_count,0,0)
        sys.exit(1)

    #If we got there, then everything is okay, so:
    print "PROCS OK - "+str(proc_count)+" processes"+perfdata(proc_count,0,0)
    sys.exit(0)

except pxssh.ExceptionPxssh, e:
    print "UNKNOWN - ",e
    sys.exit(3)

