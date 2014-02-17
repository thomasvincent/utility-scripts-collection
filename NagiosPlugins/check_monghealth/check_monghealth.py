#!/opt/zenoss/bin/python

import os
import sys
import re
import urllib2
import json

def help():
    print "Usage:"
    print "check_statusthroughweb.py YOUR_URL MODE"
    print "MODE CAN BE:"
    print """1 - To parse JSON like {"alive":true,"mongrations_current":true,"mongration_version":20120514232231,"search_reachable":true}"""
    print """2 - To parse JSON like {"alive":true,"search_reachable":true,"site_api_reachable":true}"""
    print """3 - To parse JSON like {"alive":true,"mongrations_current":true,"mongration_version":20120501015159,"mongration_newest":20120501015159,"search_reachable":true}"""
    sys.exit(3)

#if len(sys.argv) != 2 or ("--url=" not in sys.argv[1]):
#    help()
if len(sys.argv) != 3:
    help()
else:
    url = sys.argv[1]
    #url = url[6:]
    try:
        if "http://" not in url:
            url="http://"+url
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        content = response.read()
        ####################################
        mode = int(sys.argv[2])
        json_data = json.loads(content)
        #IT WAS JUST FOR DEBUG: print json_data
        #print mode

        if (json_data["alive"] == True):
            if (mode == 1):
                okflag = True
                if (json_data["mongrations_current"] == False):
                    okflag = False
                    print "CRITICAL - Database can not be reached by the host"
                    sys.exit(2)
                if (json_data["search_reachable"] == False):
                    okflag = False
                    print "WARNING - Database slaves is not reachable"
                    sys.exit(1)
                if (okflag):
                    print "OK - ", json.dumps(json_data)
                    sys.exit(0)

            if (mode == 2):
                okflag = True
                if (json_data["search_reachable"] == False):
                    okflag = False
                    print "WARNING - Database slaves is not reachable"
                    sys.exit(1)
                if (json_data["site_api_reachable"] == False):
                    okflag = False
                    print "CRITICAL - Video API is not reachable"
                    sys.exit(2)
                if (okflag):
                    print "OK - ", json.dumps(json_data)
                    sys.exit(0)

            if (mode == 3):
                okflag = True
                if (json_data["mongrations_current"] == False):
                    okflag = False
                    print "CRITICAL - Database can not be reached by the host"
                    sys.exit(2)
                if (json_data["search_reachable"] == False):
                    okflag = False
                    print "WARNING - Database slaves is not reachable"
                    sys.exit(1)
                if (okflag):
                    print "OK - ", json.dumps(json_data)
                    sys.exit(0)

        else:
            print "CRITICAL - Engine is not alive!"
            sys.exit(2)


        ####################################
    except (urllib2.HTTPError, urllib2.URLError), e:
        print "CRITICAL - "+str(e)
        sys.exit(2)