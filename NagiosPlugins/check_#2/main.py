#!/opt/zenoss/bin/python

import os
import sys
import re
import urllib2
import time
from xml.dom.minidom import *

def help():
    print "Usage:"
    print "main.py YOUR_URL"
    sys.exit(3)

if len(sys.argv) != 2:
    help()
else:
    url = sys.argv[1]
    try:
        if "http://" not in url:
            url="http://"+url
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        content = response.read()
        ####################################
        ######## Script main logic #########
        ####################################
        try:
	    xmldoc = parseString(content)
	    reservedPrefixes_FLAG = False
	    for each in xmldoc.childNodes:
		if (each.nodeName.lower() == "reservedPrefixes".lower()):
		    reservedPrefixes_FLAG = True
    	    if (reservedPrefixes_FLAG):
        	print "CHECK #2 OK - reserverPrefixes has been found."
        	sys.exit(0)
    	    else:
        	print "CHECK #2 CRITICAL - Wrong response received: reservedPrefixes not found."
        	sys.exit(2)
	    
	except xml.parsers.expat.ExpatError, e:
	    print "CHECK #2 CRITICAL - XML ERROR: ",e

            ####################################
    except (urllib2.HTTPError, urllib2.URLError), e:
        print "CHECK #2 CRITICAL HTTP/URL Error:- "+str(e)
        sys.exit(2)