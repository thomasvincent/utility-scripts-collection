import feedparser
from threading import *
import time
from config import feeds_urls
from sets import Set
######################################################################

class RSS_Grab(Thread):
    def __init__(self,irc_cls):
        Thread.__init__(self)
        self.irc = irc_cls
        ###
        self.registered_urls = Set()
        self.upd = {}
        ###
        self.RUNFLAG=1
    
    def run(self):
        while self.RUNFLAG==1:
            #URLs
            if(repr(self.registered_urls) != repr(feeds_urls)):
                for eee in feeds_urls:
                    self.registered_urls.add(eee)
                print "Debug::RSS: Registering new feeds in queue."
                
            #Feed update!
            for ef in feeds_urls:
                #Existing feed
                if(self.upd.has_key(ef)):
                    if(self.upd.get(ef) != repr(feedparser.parse(ef)['updated'])):
                        self.irc.msg_to_all("Feed "+ef+" updated!")
                        self.upd[ef] = repr(feedparser.parse(ef)['updated'])
                        print "RSS: Feed "+ef+" updated!"
                #New feed
                else:
                    self.upd[ef] = repr(feedparser.parse(ef)['updated'])
                    print "RSS: New key added for feed "+ef
                    
            time.sleep(3)
    
    def stop(self):
        self.RUNFLAG=0