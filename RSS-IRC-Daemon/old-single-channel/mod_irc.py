import irclib
from threading import *
from config import *
import time
####################################################################

class irc_conn(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.RUNFLAG=1
        # Create an IRC object
        self.irc = irclib.IRC()
        self.server = self.irc.server()
        self.server.connect ( irc_network, irc_port, irc_nick, ircname = irc_name )
        self.server.join ( irc_channel )
        #Registering event handlers
        self.irc.add_global_handler ( 'privmsg', self.handlePrivMessage )
        self.irc.add_global_handler ( 'pubmsg', self.handlePubMessage )
        #Debug
        print "Debug: IRC Enumerator Initialized."
    def run(self):
        print "Debug: Connected to server."
        while (self.RUNFLAG==1):
            self.irc.process_once()
            
            
    
    def stop(self):
        self.server.close()
        self.RUNFLAG=0
        #Writing feeds urls list back to file
        try:
            fuf1 = open(feeds_urls_filename,"w",)
            for each in feeds_urls:
                print >>fuf1, each
        except (IOError):
            print "Debug: Fatal error: Can't write feeds urls to a file!!!!"
    
    def msg_to_all(self,textofmessage):
        if(self.server.connected):
            self.server.privmsg(irc_channel, textofmessage)
        else:
            print "Debug: Not connected to server!"
    
    #IRC Event Handlers
    # Private messages
    def handlePrivMessage (self, connection, event ):
        print "Debug::handlePrivMessage: "+event.source().split ( '!' ) [ 0 ] + ': ' + event.arguments() [ 0 ]
        # Respond to a "hello" message
        if event.arguments() [ 0 ].lower().find ( 'hello' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'Hello.' )
        
        ### Add new feed url from message.
        if event.arguments() [ 0 ].lower().find ( 'newfeed' ) == 0:
            connection.privmsg ( event.source().split( '!' ) [ 0 ], 'Adding feed to DB... '+event.arguments()[ 0 ].split(' ')[1])
            feeds_urls.add(event.arguments()[ 0 ].split(' ')[1])
            
        ### Feeds URLs List
        if event.arguments() [ 0 ].lower().find ( 'list' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'Registered feeds: '+repr(feeds_urls))
        
        ### Helo
        if event.arguments() [ 0 ].lower().find ( 'help' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'Hello. Available commands are: new feed <feed url>, list' )
        #### !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
        #### !!!!! DEBUG !!!!! you should never use this block of code on production server.
        if event.arguments() [ 0 ].lower().find ( 'exit' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ],'exiting...' )
            self.RUNFLAG=0
            self.stop()
        #### !!!!! 

    # Public messages
    def handlePubMessage (self, connection, event ):
        print "Debug::handlePubMessage: "+event.target() + '> ' + event.source().split ( '!' ) [ 0 ] + ': ' + event.arguments() [ 0 ]
        
        
        
###########################################################################################################################################











