#################################################################
# This is simple configuration file for the RSS<->IRC Daemon.
#################################################################
from sets import Set
#################################################################
#IRC Enumerator Configuration
irc_network = 'irc.freenode.net'
irc_port = 6667
irc_channel = '#sparktests'
irc_nick = 'RSS Notifier'
irc_name = 'Python RSS Notifier'

feeds_urls_filename = "feedurls.txt"
feeds_urls = Set()

