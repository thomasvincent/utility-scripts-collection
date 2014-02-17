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
    print "hadoop.py -url=SOURCE_JSON_URL -t MAX_TIME_SINCE_LAST_UPDATE_IN_MINUTES (optional)"
    sys.exit(3)

if (len(sys.argv) >= 2):
    if (len(sys.argv) == 2):
        args_str = sys.argv[1]
    else:
        args_str = sys.argv[1] +" "+ sys.argv[2]
    args_str = args_str.lower()
    if ("-url=" in args_str):
        url_str = sys.argv[1].replace("-url=","")
        if ("http://" not in url_str.lower()):
            url_str = "http://"+url_str
        time_str = False
        if ("-t" in args_str):
            time_str = sys.argv[2].replace("-t", "")
        #Main code
        try:
            request = urllib2.urlopen(url_str)
            content = request.read()
            jsondict = json.loads(content)
            if (jsondict["status"].lower() == "ok"):
                #Here we are going to check time if needed
                if (time_str != False):
                    time_from_json = time.strptime(jsondict["updated"], "%Y-%m-%d %H:%M:%S")
                    time_now = time.localtime()
                    time_from_json = datetime.datetime(*time_from_json[0:6])
                    time_now = datetime.datetime(*time_now[0:6])
                    time_delta = time_now - time_from_json
                    if (time_delta.days > 0 or ((time_delta.seconds/60) > int(time_str)) ):
                        print "WARNING - Time since last update is greater than %s minutes" % str(time_str)
                    sys.exit(1)
                subcomponents_lst = jsondict["subcomponents"]
                for component in subcomponents_lst:
                    if (component["status"].lower() == "ok"):
                        #Seems that subcomponent status is ok, so we can try to check time if needed
                        if (time_str != False):
                            time_from_json = time.strptime(component["updated"], "%Y-%m-%d %H:%M:%S")
                            time_now = time.localtime()
                            time_from_json = datetime.datetime(*time_from_json[0:6])
                            time_now = datetime.datetime(*time_now[0:6])
                            time_delta = time_now - time_from_json
                            if (time_delta.days > 0 or ((time_delta.seconds/60) > int(time_str)) ):
                                print 'WARNING - Component \"%s\" has time since last update which greater than %s minutes' % (component["name"],str(time_str))
                            sys.exit(1)
                    else:
                        print 'WARNING - component \"%s\" has status \"%s\" and message: %s' % (component["name"], component["status"],component["message"])
                        sys.exit(2)
                #Seems we are achived this area of code, so seems the everything is okay.
                #Here we need to collect memory value.
                mem_component = subcomponents_lst[len(subcomponents_lst)-1]
                if (mem_component["name"].lower() == "mem"):
                    #Output is okay
                    print "OK - mem: %s" % (mem_component["message"].replace("k",""))
                else:
                    print "CRITICAL - Source URL has wrong content"
                    sys.exit(1)
            else:
                print 'WARNING - Hadoop: %s' % jsondict["message"]
                sys.exit(2)
        except (urllib2.HTTPError, urllib2.URLError), e:
            print 'UNKNOWN - %s' % e
            sys.exit(3)
        ##########
    else:
        print "UNKNOWN - Wrong arguments"
        help()
        sys.exit(3)
else:
    print "UNKNOWN - Not enough arguments"
    sys.exit(3)
