#!/opt/zenoss/bin/python


import os
import sys
import re
import urllib2

def help():
    print "Usage:"
    print "check_http500.py --email=DESTINATION_EMAIL_ADDRESS --host=HOST --port=PORT"
    sys.exit(3)

if len(sys.argv) != 4:
    help()

else:
    args=[]
    args.append(sys.argv[1])
    args.append(sys.argv[2])
    args.append(sys.argv[3])
    email=""
    host=""
    port=80
    for ea in args:
        if ("email" in ea):
            email = ea.replace("--email=","").replace("-email=","")
            continue
        if ("host" in ea):
            host = ea.replace("--host=","").replace("-host=","")
            continue
        if ("port" in ea):
            port = ea.replace("--port=","").replace("-port=","")
            port = int(port)
            continue
    #Args parsing done.
    try:
        proto = "http://"
        if (port == 443):
            proto = "https://"
        url = proto+host+":"+str(port)+"/"
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        content = response.read()
    except (urllib2.HTTPError, urllib2.URLError), e:
        if (e.code == 500):
            #print e.code
            #print e.read()
            print 'Sending mail message to %s' % email
            ### SEND MAIL MESSAGE ###
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(e.read())

            me = "root@localhost"
            you = "not_a_box@mail.com"
            msg['Subject'] = 'Server failure at host %s' % host
            msg['From'] = me
            msg['To'] = you
            s = smtplib.SMTP('127.0.0.1')
            s.sendmail(me, [you], msg.as_string())
            s.quit()
            print 'Message sent.'
