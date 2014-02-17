#!/usr/bin/env python


from zenjsonclient import router, ZenJsonClientError
from sets import Set
from time import sleep

############ BASH BINDINGS DECLARATION ############
def bash_getDevices():
    import os
    import json
    os.system("./zenoss_getDevices.sh")
    f = open("tmpfile.txt")
    data = f.read()
    dct_lst = json.loads(data)
    return dct_lst

###################################################

#Step 0: Read input data
f = open("output.txt")
f_data = f.read()
srcdata = eval(f_data)
f.close()

#Step 1: Get the list of locations in the zenoss
resp = router.device.getLocations()
zen_locations_dict_list = resp.result["locations"]
zen_locations_list = []
for each in zen_locations_dict_list:
    if ('name' in each.keys()):
        nm = each['name']
        if (nm[0] == "/"):
            nm=nm[1:]
        zen_locations_list.append(nm)

print "Locations found in zenoss:"
for each in zen_locations_list:
    print "\t",each
print "\n"

#Step 2: Get the list of locations from source data
src_locations_list = Set()
for each in srcdata:
    if ('LOCATION' in each.keys()):
        if ('name' in each['LOCATION'].keys()):
            src_locations_list.add(each['LOCATION']['name'])

print "Locations found in the source file:"
for each in src_locations_list:
    print "\t",each
print "\n"

#Step 3: Determine which locations are missing in zenoss
zen_locations_set = Set()
for each in zen_locations_list:
    zen_locations_set.add(each)

src_locations_set = src_locations_list

locations_difference = src_locations_list - zen_locations_set
if (len(locations_difference)):
    print "These locations from source data are missing in zenoss:"
    for each in locations_difference:
        print "\t",each

#Step 4: Add missing locations to zenoss
for each_location in locations_difference:
    resp = router.device.addLocationNode(type='organizer', contextUid='/zport/dmd/Devices/Locations', id=each_location)
    if (resp.result['success'] == True):
        print "Succesfully added new location \"",each_location,"\" to zenoss."

#Step 5: Get hostnames/devices from zenoss
#resp = router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=10000000)
#dev_response = resp.result['devices']
dev_response = bash_getDevices()


#Step 6: Collect devices hostnames from response and source data
dev_response_hostnames_set = Set()
for each in dev_response:
    if ('name' in each):
        dev_response_hostnames_set.add(each['name'])

print "Hostnames found in zenoss:"
for each in dev_response_hostnames_set:
    print "\t",each
print


dev_source_hostnames_set = Set()
for each in srcdata:
    if ('HOSTNAME' in each.keys()):
        dev_source_hostnames_set.add(each['HOSTNAME'])

print "Hostnames found in source data:"
for each in dev_source_hostnames_set:
    print "\t",each
print

dev_hostnames_difference_set_missing_in_zenoss = dev_source_hostnames_set - dev_response_hostnames_set
if (len(dev_hostnames_difference_set_missing_in_zenoss)):
    print "These hostnames are missing in zenoss:"
    for each in dev_hostnames_difference_set_missing_in_zenoss:
        print "\t",each
print
dev_hostnames_difference_set_existing_in_zenoss = dev_response_hostnames_set & dev_source_hostnames_set

if (len(dev_hostnames_difference_set_existing_in_zenoss)):
    print "These hostnames are present in zenoss and in the source file both:"
    for each in dev_hostnames_difference_set_existing_in_zenoss:
        print "\t",each
print

#Step 7: Insert missing hostnames
hosts_locs_table = []
for each in dev_hostnames_difference_set_missing_in_zenoss:
    for each1 in srcdata:
        if (each == each1['HOSTNAME']):
            hosts_locs_table.append(each1)
            break
print "Internal table created."
print "Going to insert hostnames/devices into zenoss."
print

#Step 7.2: Insert device with it's location into zenoss
for each_dev in hosts_locs_table:
    locationP = each_dev['LOCATION']['name']
    resp = router.device.addDevice(deviceName=each_dev['HOSTNAME'],
                                   deviceClass='/Discovered',
                                   locationPath=locationP)
    print "Add Device, zenoss says: ", repr(resp.result)

#Step ?: Just printing
print "Now we have added new devices. Usually, zenoss puts it in his background queue,"
print "so we need to make sure that all backgorund task has been finished."
print "I'm going to pull you zenoss instance every 5 secs and check if added devices already in list."

#Step 8: Wait until all devices will be added to zenoss.
polling_finished_flag = False
pulling_list = {}
for each in srcdata:
    pulling_list[each['HOSTNAME']]=False

while (not polling_finished_flag):
    print "Pulling zenoos..."
    #resp = router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=10000000)
    #dev_list_from_zen = resp.result['devices']
    dev_list_from_zen = bash_getDevices()

    for each_device in dev_list_from_zen:
        if (each_device['name'] in pulling_list.keys()):
            pulling_list[each_device['name']]=True
    polling_finished_flag=True
    for eachD in pulling_list.keys():
        if (pulling_list[eachD] == False):
            polling_finished_flag = False
    if (not polling_finished_flag):
        print pulling_list
        print "Sleeping 5 seconds..."
        sleep(5)

print "Seems that background jobs has been done... Going to do resetIp for devices."

#Step 9: Seems that all missing devices has been added to zenoss, so now we can do resetIP for all devices,
#mentioned in source data (recently added and already existing)

#Step 9.1: Collect devices uids and constract UID<->IP table. Also filter another devices which isn't mentioned in srcdata.
uids_list = []
uid_ip_dict = {}
#resp = router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=10000000)
#for each in resp.result['devices']:
for each in bash_getDevices():
    if ('uid' in each):
        uids_list.append(each['uid'])
        nm_to_search = each['name']
        for dev_in_source in srcdata:
            if dev_in_source['HOSTNAME'] == nm_to_search:
                uid_ip_dict[each['uid']]=dev_in_source['IP']


#Step 9.2: Just doing resetIP
print "\n\n\n"
for eachDeviceToResetIP in uid_ip_dict.keys():
    uid = eachDeviceToResetIP
    new_ip = uid_ip_dict[uid]
    if (new_ip):
        resp = router.device.resetIp(uids=[uid],hashcheck=1,ip=new_ip)
        print "Resetting ip for UID %s, zenoss says: %s" % (uid, repr(resp.result))

#Step 10: Just print some interesting info
print "Device count in the source data: %d" % (len(srcdata))

flag=False
for each in uid_ip_dict.keys():
    if (uid_ip_dict[each] == ""):
        flag=True

if (flag):
    print "Interesting thing! Some devices in the source data doesn't have ip:"
    for each in uid_ip_dict.keys():
        if (uid_ip_dict[each] == ""):
            name = each.split("/")
            print "\t",name[len(name)-1]

#Step 11: DONE!!!
print "\n\n\n\n\n"
print "DONE!"
