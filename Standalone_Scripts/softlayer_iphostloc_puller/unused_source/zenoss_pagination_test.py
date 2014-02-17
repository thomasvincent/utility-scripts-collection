#!/usr/bin/env python

import os
import json


def zenoss_pullLargeDevicesList():

    os.system("./zenoss_getDevices.sh")
    f = open("tmpfile.txt")
    data = f.read()
    dct_lst = json.loads(data)

    print "Device list lenght:", len(dct_lst)

zenoss_pullLargeDevicesList()
