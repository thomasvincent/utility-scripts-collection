#!/usr/bin/env python
'''#!/opt/zenoss/bin/python'''
DEBUG_Flag = False

import os
import sys
import re
import urllib2
import json
import time
import datetime

########################################################################################################################

def help():
    print "Usage:"
    print "check_jobs.py -url=JSON_URL"
    sys.exit(3)

if (len(sys.argv) == 2):
    #Seems we have two arguments, ok...
    args_str = sys.argv[1] #+" "+ sys.argv[2]
    args_str = args_str.lower()
    if ("-url=" in args_str): #and "-t=" in args_str):
        #We have all we need
        proto = 'http://'               #Just default ;-)
        if ('http://' in sys.argv[1]):
            proto = 'http://'
        else:
            if ('https://' in sys.argv[1]):
                proto = 'https://'

        url_arg = sys.argv[1].replace("http://","").replace("-url=","").replace("https://","")
        #time_arg = sys.argv[2].replace("-t=","")
        clean_url = '%s%s' % (proto, url_arg)
        if (DEBUG_Flag):
            print "Got url proto: %s" % (proto)
            print "Got clean url: %s" % (url_arg)
            print "Got clean time arg: %s" % (time_arg)
            print "Constructed url: %s" % (clean_url)

        try:
            request = urllib2.urlopen(clean_url)
            content = request.read()
            if (DEBUG_Flag):
                print content

            #Here we should got a JSON dict in content... Let's try to process it...
            json_dict = json.loads(content)
            if (DEBUG_Flag):
                print repr(json_dict)
            #Firstly we are going to check root level status
            status = json_dict['status'].lower()
            if (status == 'ok'):
                #seems that status is ok... Let's check components...
                for component in json_dict['components']:
                    component_status = component['status'].lower()
                    component_message = ''
                    if (component['message']):
                        component_message = component['message'].replace('\n',"; ")
                    else:
                        component_message = ' '

                    if component_status != 'ok':
                        print "WARNING - Component %s has status %s, message: %s" % (component['name'], component_status.upper(), component_message)
                        sys.exit(1)

                print "SUCCESS - Root status is OK. All components has status OK."
                sys.exit(0)
            else:
                print "WARNING - Root status %s is %s. Message: %s" % (json_dict['title'].upper(),status.upper(), json_dict['message'].replace('\n','; '))
                sys.exit(1)

        except (urllib2.URLError, urllib2.HTTPError), e:
            print "UNKNOWN - URL/HTTP Error: %s" % (e)
            sys.exit(3)
else:
    print "UNKNOWN - Wrong arguments!"
    sys.exit(3)