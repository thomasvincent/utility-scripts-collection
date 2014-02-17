#!/opt/zenoss/bin/python

import os
import sys
import re
import urllib2

def help():
    print "Usage:"
    #print "check_statusthroughweb.py --url=YOUR_URL"
    print "check_statusthroughweb.py YOUR_URL"
    sys.exit(3)

#if len(sys.argv) != 2 or ("--url=" not in sys.argv[1]):
#    help()
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
        php_flag = False
        mysql_flag = False
        memcache_flag = False
        cdn_flag = False
        content=content.lower()
        failed_count = 0
        if "php up" in content:
            php_flag = True
        else:
            failed_count = failed_count + 1

        if "mysql up" in content:
            mysql_flag = True
        else:
            failed_count = failed_count + 1

        if "memcache up" in content:
            memcache_flag = True
        else:
            failed_count = failed_count + 1

        if "cdn up" in content:
            cdn_flag = True
        else:
            failed_count = failed_count + 1

        ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', content )[0]

        if php_flag and mysql_flag and memcache_flag and cdn_flag and failed_count == 0:
            print "OK - PHP, MySQL and MemCache services are ok at server "+str(ip)
            sys.exit(0)

        if failed_count>0:
            if failed_count<4:
                #Print warning with failure services
                output = "WARNING - "
                if not php_flag:
                    output = output + "PHP service down, "
                if not mysql_flag:
                    output = output + "MySQL service down, "
                if not memcache_flag:
                    output = output + "MemCache service down, "
                if not cdn_flag:
                    output = output + "CDN service down, "

                output = output[:-2] + " at server "+str(ip)
                print output
                sys.exit(1)

            if failed_count==4:
                #Print critical failure
                print "CRITICAL - Server failure at address "+str(ip)
                sys.exit(2)

        ####################################
    except (urllib2.HTTPError, urllib2.URLError), e:
        print "CRITICAL - "+str(e)
        sys.exit(2)