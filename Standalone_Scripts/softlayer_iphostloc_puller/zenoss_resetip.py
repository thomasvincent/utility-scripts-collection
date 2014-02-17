#!/usr/bin/env python

from zenjsonclient import router, ZenJsonClientError
from sets import Set
from time import sleep
import sys
import argparse
import sqlite3

#Step 7. resetIP thing
#Collect devices from db with hostnames and ip addrs
database_connection = sqlite3.connect("storage.sqlite3db")
database_cursor = database_connection.cursor()

database_cursor.execute("SELECT hostname,ip from SOFTLAYER_SOURCE")
data_from_db = database_cursor.fetchall()

#Transform list of lists into list of dictionaries:
devices_db = []
for eachDataRow in data_from_db:
    dct = {"hostname" : eachDataRow[0],
           "ip" : eachDataRow[1],
           }
    devices_db.append(dct)
###################################################

database_connection.commit()
database_connection.close()

#Verify data and clean broken records
dcts_to_remove_from_devices_db = []
for eachDCT in devices_db:
    if (eachDCT["ip"] == "" or eachDCT["ip"] == " "):
        print 'Device, pulled from softlayer with name \"%s\" has no ip address!' % eachDCT["hostname"]
        dcts_to_remove_from_devices_db.append(eachDCT)

#Remove "broken" records (which has no ip address)
for each in dcts_to_remove_from_devices_db:
    devices_db.remove(each)

#Now we have clean data with hostnames,ip addrs.
#Let's pull zenoss for devices again. Maybe something is missing.
devices_zenoss_pull = []
devices_zenoss_uids_and_names = {}
request_offset = 0
try_count = 0
print "Pulling zenoss..."
while True:
    try:
        resp = router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=50, start=request_offset)
        dev_response = resp.result['devices']
        for eachDevDict in dev_response:
            if(eachDevDict["name"]):
                devices_zenoss_pull.append(eachDevDict["name"])
                devices_zenoss_uids_and_names[eachDevDict["name"]] = eachDevDict["uid"]
            else:
                continue

        request_offset += 50
        print "Got",len(dev_response), "devices from zenoss"
        if (len(dev_response) < 50):
            break
    except ZenJsonClientError, e:
        print e
        if (try_count >= ZENOSS_MAX_RETRY):
            print "Error getting devices from zenoss!"
            sys.exit(1)
        else:
            try_count += 1
            print "Sleeping 2 seconds before retry."
            sleep(2)

#Now we have a device names list in devices_zenoss_pull variable. Let's make a set of devices in db and calculate a difference.
devdb_set = Set()
devzen_set = Set()

for each in devices_db:
    devdb_set.add(each["hostname"])

for each in devices_zenoss_pull:
    devzen_set.add(each)

dev_diff = devdb_set - devzen_set
devices_to_resetIP = devices_db
lst_to_remove_from_dtrIP = []
if (dev_diff):
    if (len(dev_diff)):
        print "It's impossible, but we have some devices in the db(softlayer output) which are not present in the zenoss:"
        for each in dev_diff:
            print "\tMissing device: ",each
            for dtr in devices_to_resetIP:
                if (dtr["hostname"].lower() == each.lower()):
                    lst_to_remove_from_dtrIP.append(dtr)
if (lst_to_remove_from_dtrIP):
    if (len(lst_to_remove_from_dtrIP)):
        for each in lst_to_remove_from_dtrIP:
            devices_to_resetIP.remove(each)

#Now we have clean list of devices which are need resetIP thing. Let's replace device names by its uids (zenoss accept only device uid, not name/hostname)
for eachDevice in devices_to_resetIP:
    if (eachDevice["hostname"].lower() in devices_zenoss_uids_and_names.keys()):
        eachDevice["uid"] = devices_zenoss_uids_and_names[eachDevice["hostname"]]

#Now resetting ips
resetIP_success_count = 0
resetIP_failed_count = 0
failed_list = []
for each in devices_to_resetIP:
    if ("uid" in each.keys()):       #Only do resetIP if we have found a device UID in the step above.
        try_count = 0
        while True:
            try:
                resp = router.device.resetIp(uids=[each["uid"]],hashcheck=1,ip=each["ip"])
                result = resp.result
                print "resetIP() invoked for device",each["uid"],", zenoss says:", result
                if ("success" in result.keys()):
                    if (result["success"] == True):
                        resetIP_success_count += 1
                    else:
                        resetIP_failed_count += 1
                        failed_list.append(result)
                break
            except ZenJsonClientError,e:
                print e
                if (try_count >= ZENOSS_MAX_RETRY):
                    print "Error doing resetIP thing with data:",repr(each)
                else:
                    try_count += 1
                    print "Sleeping 2 seconds before retry."
                    sleep(2)

print "Reset IP stats:"
print "Total devices to reset:", len(devices_to_resetIP)
print "ResetIP success count:", resetIP_success_count
print "ResetIP failed count:", resetIP_failed_count
if (failed_list):
    if (len(failed_list)):
        print "Going to print a list of failed requests in 3 secs... "
        sleep(3)
        for each in failed_list:
            print each

print "DONE!"