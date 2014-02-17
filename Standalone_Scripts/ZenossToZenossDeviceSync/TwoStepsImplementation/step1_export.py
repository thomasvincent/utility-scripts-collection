#!/usr/bin/env/python

import source_inst as src_client
import shelve

#Step 1. Collect devices into list of dicts from source instance
def pull_devices_src():
    print "Going to load devices from source zenoss instance..."
    src_dev_lst = []
    '''
    dct_sample = {
        'name' : 'device_name'
        'class' : 'device_class_obtained_by_shrinking_ui'
        'location' : 'location_path_or_None'
    }
    '''
    devices_zenoss = []
    request_offset = 0
    try_count = 0
    while True:
        try:
            resp = src_client.router.device.getDevices(uid="/zport/dmd/Devices", sort="name", limit=50, start=request_offset)
            dev_response = resp.result['devices']
            for eachDevDict in dev_response:
                devices_zenoss.append(eachDevDict)
            request_offset += 50
            print "Got %s devices from source instance." % len(dev_response)
            if (len(dev_response) < 50):
                break
        except src_client.ZenJsonClientError, e:
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
        src_dev_lst.append(tmp_dct)

    return src_dev_lst

file_container = shelve.open("data.bin")
file_container["data"] = pull_devices_src()
file_container.close()
