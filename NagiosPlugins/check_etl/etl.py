#!/opt/zenoss/bin/python
DEBUG_flag=False

import os
import sys
import re
import urllib2
import json
import time
import datetime

def help():
    print "Usage:"
    print "etl.py -url=YOUR_HOSTNAME -component=YOUR_COMPONENT_NAME -t=MAX_TIME_SINCE_LAST_UPDATE_IN_MINUTES"
    sys.exit(3)

if (len(sys.argv) == 4):
    args_str = sys.argv[1] +" "+ sys.argv[2] +" "+ sys.argv[3]
    args_str = args_str.lower()
    if ("-url=" in args_str and "-component=" in args_str and "-t=" in args_str):
        url_str = "http://" + sys.argv[1].replace("-url=","") + "/api/component/"
        component_str = sys.argv[2].replace("-component=","")
        time_str = sys.argv[3].replace("-t=", "")
        if DEBUG_flag:
            print url_str+component_str, component_str, time_str
        try:
            request = urllib2.urlopen(url_str+component_str)
            content = request.read()
            ### Here is the main part of code ###
            json_dict = json.loads(content)
            status = json_dict["status"].lower()
            if (status == "ok"):
                #Here we should check the time since last update
                time_from_json = time.strptime(json_dict["updated"], "%Y-%m-%d %H:%M:%S")
                time_now = time.localtime()
                time_from_json = datetime.datetime(*time_from_json[0:6])
                time_now = datetime.datetime(*time_now[0:6])
                time_delta = time_now - time_from_json
                if DEBUG_flag:
                    print time_from_json
                    print time_now
                    print time_delta.seconds
                    print time_delta.days
                if (time_delta.days > 0 or ((time_delta.seconds/60) > int(time_str)) ):
                    print "WARNING - Time since last update is greater than %s minutes" % str(time_str)
                    sys.exit(1)
                else:
                    print "OK - Time since last update is less than %s minutes" % str(time_str)
                    sys.exit(0)
            else:
                message = json_dict["message"]
                print 'CRITICAL - %s' % (message)
                sys.exit(2)
            #####################################
        except (urllib2.URLError, urllib2.HTTPError), e:
            print 'CRITICAL - %s' % (e)
            sys.exit(2)
    else:
        print "UNKNOWN - Wrong arguments"
        help()
        sys.exit(3)
else:
    print "UNKNOWN - Not enough arguments"
    sys.exit(3)