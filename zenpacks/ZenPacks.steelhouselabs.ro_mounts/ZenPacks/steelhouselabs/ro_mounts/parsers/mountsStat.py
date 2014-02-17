from Products.ZenRRD.CommandParser import CommandParser
import logginglogger = logging.getLogger('.'.join(['zen', __name__]))

class mountsStat(CommandParser):
    def processResults(self, cmd, result):
	cmdoutput = cmd.result.output
	#for dp in cmd.points:
	#    result.values.append((dp, 12345))




