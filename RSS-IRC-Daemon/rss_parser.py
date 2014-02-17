import feedparser
from threading import Thread
import time
from config import feeds_urls

######################################################################

class RSS_Parser(Thread):
    def __init__(self,ircbot_object,database_object):
        Thread.__init__(self)
        self.RUNFLAG=1
        self.irc = ircbot_object
        self.db = database_object
        ###
        self.temp = self.db.getdata()
        self.fns = self.temp["feeds_names"]
        self.fcs = self.temp["feeds_channels"]
        self.fupd = self.temp["feeds_updated"]
    
    def run(self):
        while self.RUNFLAG==1:
            for eu in self.fns.keys():
                #Gathering data and link ;-)
                f_name = self.fns[eu]
                f_url  = eu
                f_channel = self.fcs[f_name]
                f_entry_dict = self.fupd[f_url]
                
                feed = feedparser.parse(f_url)
                for ent in feed.entries:
                    if(f_entry_dict.has_key(ent.updated)):
                        print "RSS Parser: Skipping old entry: "+ent.title+" , "+ent.updated
                    else:
                        f_entry_dict[ent.updated] = ent.copy()
                        print "RSS Parser: new entry parsed!!!"
                        #SEND MESSAGES to IRC Channel#
                        self.irc.msg_to_all("!-----------------------------------------------------!",f_channel)
                        self.irc.msg_to_all("Feed "+f_name+" was updated!", f_channel)
                        self.irc.msg_to_all("Entry date: "+ent.updated,f_channel)
                        self.irc.msg_to_all("Entry name: "+ent.title,f_channel)
                        self.irc.msg_to_all("Entry content: "+ent.content[0].value,f_channel)
                        self.irc.msg_to_all("!-----------------------------------------------------!",f_channel)
                        break
                
            time.sleep(5)
       
    def stop(self):
        print "RSS Parser: Stopping RSS Parser enumerator thread..."
        self.RUNFLAG=0
        print "RSS Parser: RSS Parser enumerator killed."