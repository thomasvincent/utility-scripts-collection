#!/usr/bin/env python


import SoftLayer.API

api_username = 'set me'
api_key = 'set me'

client = SoftLayer.API.Client('SoftLayer_Account', None, api_username, api_key)

object_mask = {
    'hardware' : {
        'operatingSystem' : {
            'passwords' : {},
            },
        'networkComponents' : {},
        'datacenter' : {},
        'processorCount' : {},
        }
}

client.set_object_mask(object_mask)



hardware = client.getHardware()

output_list = []
for eachDev in hardware:
    ip=""
    hostname=""
    loc=""
    if ("privateIpAddress" in eachDev.keys()):
        ip=eachDev["privateIpAddress"]
    if ("hostname" in eachDev.keys()):
        hostname=eachDev["hostname"]
    if ("datacenter" in eachDev.keys()):
        loc=eachDev["datacenter"]
    print "IP: %s, HOSTNAME: %s, LOCATION: %s" % (ip,hostname,loc)
    output_list.append({
        "IP": ip,
        "HOSTNAME": hostname,
        "LOCATION": loc
    })

print "Resulting list:"
print repr(output_list)

f = open("output.txt", "w")
f.write(repr(output_list))
f.close()