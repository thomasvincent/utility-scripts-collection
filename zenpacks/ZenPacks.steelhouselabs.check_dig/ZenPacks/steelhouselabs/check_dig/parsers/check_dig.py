from Products.ZenRRD.CommandParser import CommandParser
import logginglogger = logging.getLogger('.'.join(['zen', __name__]))

class check_dig(CommandParser):
    def processResults(self, cmd, result):
	for dp in cmd.points:
	    result.values.append((dp, 12345)
	    