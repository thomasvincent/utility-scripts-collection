#!/opt/zenoss/bin/python

import os
import sys
import re
import urllib2
import time
from datetime import datetime

def help():
    print "Usage:"
    print "zenoss_check4.py YOUR_URL"
    sys.exit(3)

if len(sys.argv) != 2:
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

        if (response.code == 200):
            if ("numdocs" in content.lower()):
                if ("lastModified".lower() in content.lower()):
                    if ("time since last index".lower() in content.lower()):
                        #Now obtain time since last index from lastModified line
                        content = content.split("\n")
                        lstmod = ""
                        for each in content:
                            if ("lastModified".lower() in each.lower()):
                                lstmod = each.replace("lastModified is ","")
                                break
                        tm_page = time.strptime(lstmod.replace("PDT ",""),"%a %b %d %H:%M:%S %Y")
                        tm_now = time.gmtime()
                        tm_page_dt_obj = datetime(*tm_page[0:6])
                        tm_now_dt_obj = datetime(*tm_now[0:6])
                        tm_dt_diff = tm_now_dt_obj - tm_page_dt_obj
                        days_diff = tm_dt_diff.days
                        if (days_diff < 1):
                            #Find numdocs
                            for each in content:
                                if ("numdocs".lower() in each.lower()):
                                    numdocs = each.replace("numDocs is ", "")
                            #############
                            print "CHECK #4 OK - Numdocs = %s" % numdocs
                            sys.exit(0)
                        else:
                            #Find numdocs
                            for each in content:
                                if ("numdocs".lower() in each.lower()):
                                    numdocs = each.replace("numDocs is ", "")
                                #############
                            print "CHECK #4 WARNING - time since last index bigger than one day. Numdocs = %s" % numdocs
                            sys.exit(1)
                    else:
                        print "CHECK #4 CRITITCAL - reponse doesnt contain time sinse last index line."
                        sys.exit(2)
                else:
                    print "CHECK #4 CRITICAL - response doesnt contain last modified time line."
                    sys.exit(2)
            else:
                print "CHECK #4 CRITICAL - response doesnt contain numDocs var."
                sys.exit(2)
        else:
            print "CHECK #4 CRITICAL - Got %s HTTP error." % str(response.code)
            sys.exit(2)

            ####################################
    except (urllib2.HTTPError, urllib2.URLError), e:
        print "CRITICAL - "+str(e)
        sys.exit(2)