###################################### IRC<->RSS BOT Main #################################################
#Dependencies: python-shelve, python-irclib, python-feedparser, python-flask
#

###############################
from config import database_filename,DB,feeds_channels,feeds_names,feeds_updated,feeds_urls
from db_layer import MyDataBaseLayer
from ircbot import IRCBot
from rss_parser import RSS_Parser
import time
from webpanel import *
import shelve
###############################
DB = DB

def main():
    global DB
    
    '''############# Initial data #################'''
    feeds_urls.add("http://test.vincent.users.com/?feed=rss2")
    feeds_names["http://test.vincent.users.com/?feed=rss2"] = "Test.vincent.Users.com Feed"
    feeds_channels["Test.vincent.Users.com Feed"] = "#tvincent"
    feeds_updated["http://test.vincent.users.com/?feed=rss2"] = {"date":'123'}
    '''############# Initial data #################'''
    
    tempdict = {}
    tempdict["feeds_urls"] = feeds_urls
    tempdict["feeds_names"] = feeds_names 
    tempdict["feeds_channels"] = feeds_channels 
    tempdict["feeds_updated"] = feeds_updated  
    DB = MyDataBaseLayer(tempdict, database_filename)
    tempdict.clear()
    DB.start()
    irc = IRCBot(DB)
    irc.start()
    time.sleep(10)
    rss = RSS_Parser(irc, DB)
    rss.start()
    
    #run_webpanel(DB)
    
    '''########################################## TEST BLOCK ###############################'''
    abc ="1"
    while (abc != "quit"):
        abc = raw_input("type quit to exit:")
    if (abc=="quit"):
        rss.stop()
        irc.stop()
        DB.stop()
    '''########################################## TEST BLOCK ###############################'''
    pass



########################
if __name__=='__main__':
    main()
    pass
