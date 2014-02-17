#!/usr/bin/env python

import source_inst as src_client
import destination_inst as dst_client
import re
import sys
import string
from sets import Set

###################################################################################################################

#Step 1. Pull devices from the intance
def pull_devices(client_instance):
    devices_zenoss = []
    request_offset = 0
    try_count = 0
    src_dev_lst = []

    while True:
        try:
            resp = client_instance.router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=50, start=request_offset)
            dev_response = resp.result['devices']
            for eachDevDict in dev_response:
                devices_zenoss.append(eachDevDict)
            request_offset += 50
            if (len(dev_response) < 50):
                break
        except client_instance.ZenJsonClientError, e:
            print e
            if (try_count >= ZENOSS_MAX_RETRY):
                print "Error getting devices from zenoss!"
                sys.exit(1)
            else:
                try_count += 1
                print "Sleeping 2 seconds before retry."
                sleep(2)
    print "Got %s devices from source instance..." % (len(devices_zenoss))
    for eacnZenDev in devices_zenoss:
        tmp_dct={}
        tmp_dct["name"] = eacnZenDev["name"]
        tmp_dct["uid"] = eacnZenDev["uid"]
        tmp_dct["location"] = eacnZenDev["location"]
        if tmp_dct["location"] != None:
            tmp_dct["location"] = tmp_dct["location"]["name"]
        dev_class = tmp_dct["uid"].replace("/zport/dmd/Devices", "")
        dev_class = dev_class.split("/devices/")[0]
        tmp_dct["class"] = dev_class
        tmp_dct["groups"] = eacnZenDev[u'groups']
        tmp_dct["productionState"] = eacnZenDev[u'productionState']
        tmp_dct["ipaddr"] = eacnZenDev[u'ipAddressString']
        src_dev_lst.append(tmp_dct)
    return src_dev_lst


s1 = pull_devices(src_client)
s2 = pull_devices(dst_client)

print "Going to calculate difference..."

set_one = Set()
set_two = Set()

for d in s1:
    set_one.add(d['uid'])

for d in s2:
    set_two.add(d['uid'])

print "SRC SET:"
print set_one
print " "
print " "
print "DST SET:"
print set_two

print "\n\n\n"
print "SRC SET minus (-) DST SET difference:"
print (set_one - set_two)
print "\n\n\n"

print "DST SET minus (-) SRC SET difference:"
print (set_two - set_one)
print "\n\n\n"
