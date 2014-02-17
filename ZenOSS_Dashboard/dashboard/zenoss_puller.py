import sys,os
from datetime import *
os.environ['DJANGO_SETTINGS_MODULE'] ='dashboard.settings'
from django.core.management import setup_environ
from django.db.models import *
from dashboard import settings
from main.models import *
setup_environ(settings)
from zenjsonclient import *
import threading
import base64
########################################################################################################################

import sys, os, time, atexit
from signal import SIGTERM

class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
class MyDaemon(Daemon):
    def run(self):
        while True:
            #The first step - we should pull locations.
            response = router.device.getLocations()
            for each in response.result["locations"]:
                try:
                    loc = zenoss_location.objects.get(name=each['name'])
                    loc.save()
                except ObjectDoesNotExist:
                    currentloc = zenoss_location(uid="None", name=each['name'])
                    currentloc.save()
            #Add "NONE" location
            try:
                loc = zenoss_location.objects.get(name="NONE")
                loc.save()
            except ObjectDoesNotExist:
                loc = zenoss_location(name="NONE", uid="NONE")
                loc.save()
            #Step 2: Get devices (with pagination)
            request_offset = 0
            try_count = 0
            self.break_flagg = True
            while self.break_flagg:
                try:
                    resp = router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=50, start=request_offset)
                    dev_response = resp.result['devices']
                    print "Got %s devices... " % len(dev_response)
                    for eachDevDict in dev_response:
                        try:
                            dev = zenoss_device.objects.get(uid=eachDevDict["uid"])
                            dev.collector = eachDevDict["collector"]
                            if (eachDevDict["ipAddress"]):
                                dev.ipAddress = eachDevDict["ipAddress"]
                            else:
                                dev.ipAddress = 0
                            dev.ipAddressString = str(eachDevDict["ipAddressString"])
                            dev.name = str(eachDevDict["name"])
                            if (eachDevDict["location"] != None):
                                dev.location_id = zenoss_location.objects.get(name=eachDevDict["location"]["name"]).id
                            else:
                                dev.location_id = zenoss_location.objects.get(name="NONE").id
                            dev.save()
                        except ObjectDoesNotExist:
                            dev = zenoss_device(uid=eachDevDict["uid"],
                                                    collector=str(eachDevDict["collector"]),
                                                    ipAddressString=str(eachDevDict["ipAddressString"]),
                                                    name = str(eachDevDict["name"])
                                        )
                            if (eachDevDict["ipAddress"]):
                                dev.ipAddress = eachDevDict["ipAddress"]
                            else:
                                dev.ipAddress = 0
                            if (eachDevDict["location"] != None):
                                dev.location_id = zenoss_location.objects.get(name=eachDevDict["location"]["name"]).id
                            else:
                                dev.location_id = zenoss_location.objects.get(name="NONE").id
                            dev.save()
                    request_offset += 50
                    if (len(dev_response) < 50):
                        self.break_flagg = False
                except ZenJsonClientError, e:
                    print e
                    if (try_count >= ZENOSS_MAX_RETRY):
                        print "Error getting devices from zenoss!"
                        break_flagg = False
                    else:
                        try_count += 1
                        print "Sleeping 2 seconds before retry."
                        time.sleep(2)
            #Step 3: Get devices templates
            devices_list = zenoss_device.objects.all()
            for zdevice in devices_list:
                resp = router.device.getTemplates(id=zdevice.uid)
                if resp.result:
                    for template_dict in resp.result:
                        try:
                            templ = zenoss_rrd_template.objects.get(uid=template_dict["uid"])
                            templ.path = template_dict["path"]
                            templ.text = template_dict["text"]
                            templ.save()
                            if (templ not in zdevice.templates.all()):
                                zdevice.templates.add(templ)
                                zdevice.save()
                        except ObjectDoesNotExist:
                            new_temp = zenoss_rrd_template()
                            new_temp.uid = template_dict["uid"]
                            new_temp.path = template_dict["path"]
                            new_temp.text = template_dict["text"]
                            new_temp.save()
                            zdevice.templates.add(new_temp)
                            zdevice.save()
            #Step 4: get data sources.
            templates = zenoss_rrd_template.objects.all()
            for template in templates:
                resp = router.template.getDataPoints(uid=template.uid, query="")
                if resp.result:
                    for dp in resp.result["data"]:
                        try:
                            ds = zenoss_rrd_datasource.objects.get(uid=dp["uid"])
                            ds.id_text = dp["id"]
                            ds.name = dp["name"]
                            ds.newId = dp["newId"]
                            ds.rrdType = dp["rrdtype"][:1]
                            ds.type = dp["type"]
                            ds.description = dp["description"]
                            ds.save()
                            if (ds not in template.datapoints.all()):
                                template.datapoints.add(ds)
                                template.save()

                        except ObjectDoesNotExist:
                            ds = zenoss_rrd_datasource()
                            ds.uid = dp["uid"]
                            ds.id_text = dp["id"]
                            ds.name = dp["name"]
                            ds.newId = dp["newId"]
                            ds.rrdType = dp["rrdtype"][:1]
                            ds.type = dp["type"]
                            ds.description = dp["description"]
                            ds.save()
                            template.datapoints.add(ds)
                            template.save()

            #Step 5: The most important step! Here we are going to pull performance data.
            devices_to_pull = zenoss_device.objects.all()
            for device in devices_to_pull:
                templates = device.templates.all()
                for template in templates:
                    datapoints = template.datapoints.all()
                    for dp in datapoints:
                        point = zenoss_rrd_performance_point()
                        point.device = device
                        point.template = template
                        point.datasource_details = dp
                        url_to_fetch = DEFAULT_PROTOCOL+"://"+DEFAULT_HOST+":"+DEFAULT_PORT+device.uid+"/getRRDValue?dsname="+dp.newId
                        request = urllib2.Request(url_to_fetch)
                        basic_auth_data = base64.encodestring('%s:%s' % (DEFAULT_USERNAME, DEFAULT_PASSWORD)).replace('\n', '')
                        request.add_header("Authorization", "Basic %s" % basic_auth_data)
                        result = urllib2.urlopen(request)
                        content = result.read()
                        if (content != ""):
                            point.value_str = content
                            point.value_int = int(float(content))
                            point.value_float = float(content)
                            point.save()
                        else:
                            point.value_str = ""
            #Step 6;
            #Step 7;
            print "Sleeping for 60 secounds..."
            time.sleep(60) #We are going to pull zenoss every minute.
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
'''if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-zenoss-pull.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
'''
d = MyDaemon("/tmp/daemon-zenoss-pull.pid")
d.run()
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################