#!/usr/bin/env python

import os
import sys
import sqlite3
from sets import Set
import time
from zenjsonclient import router, ZenJsonClientError
#######################

#Step 1: Get the list of locations in the zenoss
retry_count = 0
retry_count_max = 5
retry_flag=True

while (retry_flag):
    if (retry_count < retry_count_max):
        try:
            retry_count +=1
            resp = router.device.getLocations()
            retry_flag = False
        except ZenJsonClientError,e:
            print "ZenOSS JSON Client ERROR: ",e
            retry_flag = True
    else:
        print "Error getting loctions info from zenoss."


if (resp.result):
    if (resp.result["success"] == True):
        zen_locations_dict_list = resp.result["locations"]
    else:
        print "ZenOSS said some error instead of locations data..."
        exit(0)

zen_locations_list = []
for each in zen_locations_dict_list:
    if ('name' in each.keys()):
        nm = each['name']
        if (nm[0] == "/"):
            nm=nm[1:]
        zen_locations_list.append(nm)

if (len(zen_locations_list)):
    print "Locations found in zenoss:"
    for each in zen_locations_list:
        print "\t",each
    print "\n"
else:
    print "There are no locations in the zenoss"
    print "\n"

list_zen = zen_locations_list


#Step 2: Get locations list from the source data
database_connection = sqlite3.connect("storage.sqlite3db")
database_cursor = database_connection.cursor()

database_cursor.execute("SELECT DC_NAME from SOFTLAYER_SOURCE")
locations_from_db = database_cursor.fetchall()

list_db = []
set_db = Set()
for each in locations_from_db:
    for each1 in each:
        list_db.append(each1)

for each in list_db:
    set_db.add(each)

list_db = []

for each in set_db:
    list_db.append(each)
if (len(list_db)):
    print "Locations found in db:"
    for each in list_db:
        print "\t",each
else:
    print "There are no location in the database."

database_connection.commit()
database_connection.close()

#Step 3: now we have list_zen and list_db lists. They are contains a lists of locations found in the database and in the
#zenoss instance. Here we should calculate the difference than insert missing locations into zenoss.

set_zen = Set()
set_db = Set()

for each in list_zen:
    set_zen.add(each)

for each in list_db:
    set_db.add(each)

locations_difference = set_db - set_zen

if (len(locations_difference)):
    print "We have some locations which are not present in the zenoss:"
    for each in locations_difference:
        print "\t",each
    print "Now i'm going to inject missing locations into zenoss"
    ####### Insert part #######
    failed_to_add = []
    for each_missing_location in locations_difference:
        resp = router.device.addLocationNode(type='organizer', contextUid='/zport/dmd/Devices/Locations', id=each_missing_location)
        if (resp.result['success'] == True):
            print "Succesfully added new location \"",each_missing_location,"\" to zenoss."
        else:
            failed_to_add.append(each_missing_location)

    if (len(failed_to_add)):
        print "Failed to add this locations into zenoss:"
        for each in failed_to_add:
            print "\t",each
    else:
        print "Succesfully added all missing locations."
        print "Added locations count: ", len(locations_difference)
    ###########################
else:
    print "There are no locations which are present in db and not present in zenoss"

print "\n"

#Step 4. Calculate another locations difference.
locations_difference = set_zen - set_db
if (len(locations_difference)):
    print "We have some locations which are present in zenoos and not present in db(softlayer):"
    for each in locations_difference:
        print "\t",each
else:
    print "There are no locations which are present in zenoss and not present in db(softlayer)."