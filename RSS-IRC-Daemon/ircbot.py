#IRC Bot class

import irclib
from threading import Thread
from config import *
import time
import feedparser
##############################################################################################################################################

class IRCBot(Thread):
    def __init__(self,dddd):
        Thread.__init__(self)
        self.db = dddd
        self.RUNFLAG=1
        self.IRC = irclib.IRC()
        self.irc_server = self.IRC.server()
        self.irc_server.connect ( irc_network, irc_port, irc_nick, ircname = irc_name )
        #Performing joins to needed channels
        self.somedata = self.db.getdata()
        self.channels = self.somedata["feeds_channels"]
        for ec in self.channels.keys():
            self.irc_server.join(self.channels[ec])
            print "IRC Bot: join to channel "+self.channels[ec]
        #Register events handlers
        self.IRC.add_global_handler ( 'privmsg',       self.handlePrivMessage )
        self.IRC.add_global_handler ( 'pubmsg',        self.handlePubMessage  )
        self.IRC.add_global_handler ( 'kill',          self.handleKillEvent )
        self.IRC.add_global_handler ( 'disconnect',    self.handleDisconnectEvent )
        #Debug
        print "IRC Bot: Init() complete."
        
    def run(self):
        print "IRC Bot: enumerator thread started."
        for ec in self.channels.keys():
            self.msg_to_all("Hi everyone!", self.channels[ec])
        while (self.RUNFLAG==1):
            if(self.irc_server.connected==False):
                self.irc_server.connect ( irc_network, irc_port, irc_nick, ircname = irc_name )
                print "IRC Bot: Disconnected from irc server... Attempting to reconnect..."
            self.IRC.process_once()
            time.sleep(1)
            print "Debug: enumerate irc"
        pass
    
    def stop(self):
        print "IRC Bot: stopping irc bot enumerator thread."
        for ec in self.channels.keys():
            self.msg_to_all("Master command received: Exit", self.channels[ec])
            self.msg_to_all("Disconnecting...", self.channels[ec])
        self.IRC.process_once()
        self.RUNFLAG=0
        pass
    
    #Public message sender
    def msg_to_all(self,textofmessage,ch):
        if(self.irc_server.connected):
            self.irc_server.privmsg(ch, textofmessage)
        else:
            print "IRC Bot Fatal Error: Not connected to server, so can't send public message!"
    
    #IRC Event Handlers
    # Private messages
    def handlePrivMessage (self, connection, event ):
        print "Debug::handlePrivMessage: "+event.source().split ( '!' ) [ 0 ] + ': ' + event.arguments() [ 0 ]
        # Respond to a "hello" message
        if event.arguments() [ 0 ].lower().find ( 'hello' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'Hello.' )
        
        ### Add new feed url from message.
        if event.arguments() [ 0 ].lower().find ( 'newfeed' ) == 0:
            connection.privmsg ( event.source().split( '!' ) [ 0 ], 'Adding feed to DB: ')
            newfeedurl = event.arguments()[ 0 ].split(' ')[1]
            newfeedchannel = event.arguments()[ 0 ].split(' ')[2]
            #Join to the new channel immediately
            self.irc_server.join(newfeedchannel)
            ###
            newfeedname = feedparser.parse(newfeedurl).channel.title
            urls=self.somedata["feeds_urls"]
            urls.add(newfeedurl)
            names=self.somedata["feeds_names"]
            names[newfeedurl]=newfeedname
            channels=self.somedata["feeds_channels"]
            channels[newfeedname]=newfeedchannel
            updddd=self.somedata["feeds_updated"]
            updddd[newfeedurl]={"1":"1"}
            
            #Working with feed data#
            
            
        ### Feeds URLs List
        if event.arguments() [ 0 ].lower().find ( 'list' ) == 0:
            feedsdict = self.somedata["feeds_names"]
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'Registered feeds: ')
            for each in feedsdict.keys():
                connection.privmsg ( event.source().split ( '!' ) [ 0 ], (feedsdict[each]+'  :::  '+each))
        
        ### Helo
        if event.arguments() [ 0 ].lower().find ( 'help' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'Hello. Available commands are: newfeed <feed url> #<channel>, list' )
        #### !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
        #### !!!!! DEBUG !!!!! you should never use this block of code on production server.
        if event.arguments() [ 0 ].lower().find ( 'exit' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'exiting...' )
            self.RUNFLAG=0
            self.stop()
        #### !!!!! 

    # Public messages
    def handlePubMessage (self, connection, event ):
        print "IRC Bot::handlePubMessage: "+event.target() + '> ' + event.source().split ( '!' ) [ 0 ] + ': ' + event.arguments() [ 0 ]

    #Internal service handlers... 
    def handleKillEvent(self, connection, event):
        print "DEBUG: IRC BOT: Ooops! It seems that irc server has gone awaw somewhere! ;-)"
        self.irc_server.disconnect("Something strange was happen!")
        self.irc_server.connect ( irc_network, irc_port, irc_nick, ircname = irc_name )
        print "IRC Bot: Reconnecting..."
        for ec in self.channels.keys():
            self.irc_server.join(self.channels[ec])
            print "IRC Bot: join to channel "+self.channels[ec]
        
    def handleDisconnectEvent(self, connection, event):
        print "DEBUG: IRC BOT: Ooops! It seems that irc server has gone awaw somewhere! ;-)"
        self.irc_server.disconnect("Something strange was happen!")
        self.irc_server.connect ( irc_network, irc_port, irc_nick, ircname = irc_name )
        print "IRC Bot: Reconnecting..."
        for ec in self.channels.keys():
            self.irc_server.join(self.channels[ec])
            print "IRC Bot: join to channel "+self.channels[ec]