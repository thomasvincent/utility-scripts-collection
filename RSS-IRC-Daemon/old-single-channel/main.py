#!/usr/bin/python

# Author: Darkstar (Vlad E. Borovtsov)
# Dependencies: python-base, Universal Feed Parser, python-irclib, ...
#######################################################################################
from mod_irc import irc_conn
from rss_mod import RSS_Grab
from config import *  
from fileinput import close
import string
from compiler.pycodegen import EXCEPT
import time
#######################################################################################

def main():
    #Prepare
    #Load urls of feed into memory
    print "Registered urls:"
    try:
        fuf = open(feeds_urls_filename,"r",)
        feeds_urls = fuf.readlines()
        print feeds_urls
        fuf.close()
    except (IOError):
        print "Debug: Error opening file with feeds urls"
    ####################################################
    print "=== RSS<->IRC Daemon ==="
    #starting irc enumerator thread
    irc = irc_conn()
    irc.start()
    rss = RSS_Grab(irc)
    rss.start()
    
    while True:
        if(irc.RUNFLAG == 0):
            rss.stop()
            break
        time.sleep(3)
    ####################################################
    pass

if __name__=='__main__':
    main()
    pass