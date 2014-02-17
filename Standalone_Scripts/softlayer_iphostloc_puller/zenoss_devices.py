#!/usr/bin/env python

'''
Algorithm:
1. Get devices with its locations from DB (which was made by softlayer_pull.py script.
2. Get devices with its locations from zenoss
3. Calculate difference in two ways the output something to console
4. Inject new devices into zenoss.
5. Result check loop
6. Move devices into right locations.
7. Do "resetIP" thing
'''

from zenjsonclient import router, ZenJsonClientError
from sets import Set
from time import sleep
import sys
import argparse
import sqlite3

########################################################################################################################

ZENOSS_PULL_INTERVAL = 10       #In seconds
ZENOSS_MAX_RETRY = 5

########################################################################################################################
def searchValueInTheDictionaryList(dict_lst, key, value_to_search, key_to_get):
    if (dict_lst):
        if (len(dict_lst)):
            for eachDict in dict_lst:
                if (key in eachDict.keys() and key_to_get in eachDict.keys()):
                    if (eachDict[key] == value_to_search):
                        return eachDict[key_to_get]
                else:
                    return None
    return None
########################################################################################################################

#Step ??: Arguments parser
parser = argparse.ArgumentParser(description='ZenOSS device injector')

parser.add_argument('-c', action="store", dest="collector", required=False)

args_result = parser.parse_args()
ZENOSS_COLLECTOR = args_result.collector

if (ZENOSS_COLLECTOR):
    print "Device collector specified: ", ZENOSS_COLLECTOR
else:
    print "No device collector specified, using zenoss default. "


#Step 1: Get devices with its locations from DB (which was made by softlayer_pull.py script.
database_connection = sqlite3.connect("storage.sqlite3db")
database_cursor = database_connection.cursor()

database_cursor.execute("SELECT hostname,dc_name from SOFTLAYER_SOURCE")
data_from_db = database_cursor.fetchall()

#1.1: Transform list of lists into list of dictionaries:
devices_db = []
for eachDataRow in data_from_db:
    dct = {"hostname" : eachDataRow[0],
           "location" : eachDataRow[1],
           }
    devices_db.append(dct)
###################################################

database_connection.commit()
database_connection.close()

#Step 2: Get devices with its locations from zenoss
#We are going to get 50 devices per request to avoid zenoss overload.
devices_zenoss = []
request_offset = 0
try_count = 0
while True:
    try:
        resp = router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=50, start=request_offset)
        dev_response = resp.result['devices']
        for eachDevDict in dev_response:
            dct = {}
            if(eachDevDict["name"]):
                dct["hostname"] = eachDevDict["name"]
                if (eachDevDict["location"]):
                    if (eachDevDict["location"]["name"]):
                        dct["location"] = eachDevDict["location"]["name"][1:]
                else:
                    dct["location"] = None
                    print "Location for device ", dct["hostname"], "is not specified."
                devices_zenoss.append(dct)
            else:
                print "Name for device is not found. Skipping."
                continue

        request_offset += 50
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

#Now we have collected devices with its locations in "devices_db" and "devices_zenoss" variables.

#Step 3: Calculate difference in two ways the output something to console
#Also we will output devices with wrong location as different list.

devices_in_db_not_in_zenoss = Set()
devices_not_in_db_in_zenoss = Set()
devices_db_set = Set()
devices_zenoss_set = Set()

for eachDevDB in devices_db:
    devices_db_set.add(eachDevDB["hostname"])

for eachDevZenoss in devices_zenoss:
    devices_zenoss_set.add(eachDevZenoss["hostname"])

devices_in_db_not_in_zenoss = devices_db_set - devices_zenoss_set
devices_not_in_db_in_zenoss = devices_zenoss_set - devices_db_set

if (len(devices_in_db_not_in_zenoss)):
    print "Devices found in the db (softlayer) and not found in zenoss:"
    for each in devices_in_db_not_in_zenoss:
        print "\t",each

if (len(devices_not_in_db_in_zenoss)):
    print "Devices found in zenoss and not found in db (softlayer):"
    for each in devices_not_in_db_in_zenoss:
        print "\t",each

devlist_with_none_location = []
for each in devices_zenoss:
    if (each["location"] == None):
        devlist_with_none_location.append(each["hostname"])
if (len(devlist_with_none_location)):
    print "Devices found in zenoss without any location:"
    for each in devlist_with_none_location:
        print "\t",each

#Now we are going to find devices, which are present in db and in zenoss both, but has wrong location in zenoss
#The first, let's calculate an intersection of two sets:
devices_both_in_db_in_zenoss = devices_db_set & devices_zenoss_set
#Let's find who of them has wrong location. Let's use db location as right data.
devlst_wrong_location = []
for each in devices_both_in_db_in_zenoss:
    #Checking each devices for location
    zenloc = searchValueInTheDictionaryList(devices_zenoss,"hostname",each,"location")
    dbloc  = searchValueInTheDictionaryList(devices_db,"hostname",each,"location")
    if (zenloc != dbloc):
        dct = {}
        dct["hostname"] = each
        dct["loc_db"] = dbloc
        dct["loc_zen"] = zenloc
        devlst_wrong_location.append(dct)

if (len(devlst_wrong_location)):
    print "Attention! Some devices in zenoss has wrong location:"
    for each in devlst_wrong_location:
        print "\t","Hostname:",each["hostname"],", zenoss location:",each["loc_zen"], ", should be:", each["loc_db"]



#Step 4: Inject new devices into zenoss.
table_to_pull = {}

if (devices_in_db_not_in_zenoss):
    if (len(devices_in_db_not_in_zenoss)):
        ################################################
        #1. Building a list of devices to inject with locations from database
        dev_list_to_inject = []
        for eachDev in devices_in_db_not_in_zenoss:
            loc = searchValueInTheDictionaryList(devices_db,"hostname",eachDev, "location")
            dct = {"hostname" : eachDev,
                   "location" : loc,
                   }
            dev_list_to_inject.append(dct)
        #2. print log
        print "Going to inject this devices into zenoss:"
        for each in dev_list_to_inject:
            print "\t",each
        #3. injecting...
        for each in dev_list_to_inject:
            run_flag = True
            while run_flag:
                try:
                    if (each["location"] != None):
                        if (ZENOSS_COLLECTOR):
                            resp = router.device.addDevice(deviceName=each["hostname"],
                                               deviceClass='/Discovered',
                                               locationPath=each["location"],
                                               collector=ZENOSS_COLLECTOR)
                        else:
                            resp = router.device.addDevice(deviceName=each["hostname"],
                                                       deviceClass='/Discovered',
                                                       locationPath=each["location"])
                    else:
                        if (ZENOSS_COLLECTOR):
                            resp = router.device.addDevice(deviceName=each["hostname"],
                                                   deviceClass='/Discovered',
                                                   collector=ZENOSS_COLLECTOR)
                        else:
                            resp = router.device.addDevice(deviceName=each["hostname"],
                                                       deviceClass='/Discovered')
                    #Parse response here
                    run_flag = False
                    print "addDevice invoked... zenoss says: ", resp.result
                    if (resp.result['success'] == True):
                        table_to_pull[each["hostname"]] = False

                except ZenJsonClientError, e:
                    print "Error adding device, zenoss says:",e
                    if (try_count >= ZENOSS_MAX_RETRY):
                        run_flag = False
                        print "Error inserting device ",each["hostname"], " ", ZENOSS_MAX_RETRY, " times. Skipping."
                    try_count += 1
                    run_flag = True
        ################################################
    else:
        print "Nothing to inject into zenoss."

#Step 5: Result check loop
#We are going to pull devices which was added with "SUCCESS". See code above.
'''
if (table_to_pull):
    if (len(table_to_pull)):
        #################################################
        pull_again = True
        while pull_again:
            #1. Get devices from zenoss
            devices_zenoss_pull = []
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
                #2. Got device list. Let's check which of them we can mark as true in our table.
            for each in table_to_pull.keys():
                if (each in devices_zenoss_pull):
                    table_to_pull[each] = True

            #3. Let's count something
            added_count = 0
            not_added_count = 0
            for each in table_to_pull.keys():
                if (table_to_pull[each]):
                    added_count += 1
                else:
                    not_added_count += 1
            print "Pulling stats:"
            print "\t Devices added: ", added_count
            print "\t Devices waiting: ", not_added_count
            print "\t Devices total: ", len(table_to_pull.keys())

            #4. Let's check if all devices were added. I know that it's stupid way, but i don't use counter above right now, so i'm going to check table again.
            pull_again = False
            for each in table_to_pull.keys():
                if (table_to_pull[each] == False):
                    pull_again = True

            if (pull_again):
                print "Sleeping ", ZENOSS_PULL_INTERVAL, "seconds..."
                sleep(ZENOSS_PULL_INTERVAL)

        print "Pulling done. Seems that all injected devices now are in zenoss."
        #################################################
    else:
        print "Seems that you haven't injected any devices so nothing to check. "


'''
'''#Step 6. Move devices into right locations.
if (len(devlst_wrong_location)):
    print "We have some devices in zenoss which have wrong location:"
    for each in devlst_wrong_location:
        print "\t","Hostname:",each["hostname"],", zenoss location:",each["loc_zen"], ", location should be:", each["loc_db"]
    location_devices_groups = {}
    ### location_devices_groups format description
    # location_devices_groups = {
    #                               "location1" : [device1, device2, device3, ... ],
    #                               "location2" : [device1, device2, device3, ... ],
    #                               ... ,
    #                               }
    locations_set = Set()
    for each in devlst_wrong_location:
        locations_set.add(each["loc_db"])
    for each in locations_set:
        location_devices_groups[each] = []
    for each in devlst_wrong_location:
        location_devices_groups[each["loc_db"]].append(each["hostname"])

    #Now let's get all devices from zenoss to obtain missing data
    devices_zenoss = []
    request_offset = 0
    try_count = 0
    while True:
        try:
            resp = router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=50, start=request_offset)
            dev_response = resp.result['devices']
            for eachDevDict in dev_response:
                devices_zenoss.append(eachDevDict)

            request_offset += 50
            print "Got", len(dev_response), "devices from zenoss."
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

    print "Collected",len(devices_zenoss), "devices from zenoss. Building internal table..."
    for each in devices_zenoss:
        for eachLoc in location_devices_groups.keys():
            if ("name" in each.keys()):
                if (each["name"] in location_devices_groups[eachLoc]):
                    if ("uid" in each.keys()):
                        location_devices_groups[eachLoc].remove(each["name"])
                        location_devices_groups[eachLoc].append(each["uid"])
                    else:
                        location_devices_groups[eachLoc].remove(each["name"])

    #print "Debug:"
    #print location_devices_groups
    #DEBUG:#print devices_zenoss[1]
    #DEBUG:print "Debug:", location_devices_groups
'''

'''
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
'''
print "DONE!"