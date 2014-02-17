#!/usr/bin/env python

import destination_inst as dst_client
import shelve

def inject_devices(data_to_inject):
    print "Going to inject devices into destination zenoss instance..."
    print "Got source data:"
    for each in data_to_inject:
        print "Device: ", each
    print "\n"
    for device_dict in data_to_inject:
        retry_again = True
        failed_count = 0
        while retry_again:
            retry_again = False
            try:
                response = dst_client.router.device.addDevice(deviceName=device_dict["name"],
                    deviceClass=device_dict["class"],
                    locationPath=device_dict["location"]
                )
                if response.result["success"] == True:
                    retry_again = False
                    print "Successful import: %s" % (device_dict["uid"])
                else:
                    retry_again = False
                    print "Sorry, can't import device; zenoss says: ", response.result

            except dst_client.ZenJsonClientError, e:
                retry_again = True
                failed_count +=1
                if (failed_count > 3):
                    print "Sorry, can't add device %s" % (device_dict["uid"])
                    retry_again = False

    pass

file_container = shelve.open("data.bin")
if (file_container.has_key("data")):
    data = file_container["data"]
    inject_devices(data)
else:
    print "Import error: there is no correct data in the shelve container..."
file_container.close()