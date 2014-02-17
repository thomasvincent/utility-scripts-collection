#!/usr/bin/env python

import source_inst as src_client
import destination_inst as dst_client
import re
import sys
import string

#print src_client.router.device.getDevices(sort='name')     #DEBUG
#print dst_client.router.device.getDevices(sort='name')     #DEBUG

#Step 1. Collect devices into list of dicts from source instance
def pull_devices_src():
    print "Going to load devices from source zenoss instance..."
    src_dev_lst = []
    '''
    dct_sample = {
        'name' : 'device_name'
        'class' : 'device_class_obtained_by_shrinking_ui'
        'location' : 'location_path_or_None'
        'groups' : groups list or empty list
        'productionState' : production state (string only)
        'ipaddr' : ip address
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
        tmp_dct["groups"] = eacnZenDev[u'groups']
        tmp_dct["productionState"] = eacnZenDev[u'productionState']
        tmp_dct["ipaddr"] = eacnZenDev[u'ipAddressString']
        src_dev_lst.append(tmp_dct)

    return src_dev_lst

####################################################################################################################
def passthroughTree(tree,result_list):
    for each in tree:
        if 'uid' in each.keys():
            result_list.append(each['uid'])
        if 'children' in each.keys():
            if len(each['children']) > 0:
                #for eachChild in each['children']:
                passthroughTree(each['children'],result_list)
    return  result_list

def inject_devices_check_and_inject_deviceClass(source_device):
    try:
        response = dst_client.router.service.getTree(id='/zport/dmd/Devices')
        deviceClassesList = response.result
        if len(response.result):
            deviceClassesList = passthroughTree(deviceClassesList, [])
        else:
            print "Failed to get device classes from destination instance."
            sys.exit(1)
        newDCL = []
        for each in deviceClassesList:
            newDCL.append(each.replace('/zport/dmd/Devices', ''))
        if source_device['class'] in newDCL:
            print "Device class %s is already exists. " % source_device['class']
        else:
            #going to make new device class
            #lets make tree list first
            tree_list = source_device['class'].split('/')
            while '' in tree_list:
                tree_list.remove('')
            cUid = '/zport/dmd/Devices'
            for each in tree_list:
                try:
                    response = dst_client.router.service.addNode(type='organizer', contextUid=cUid, id=each)
                    print response.result
                    cUid=cUid+'/'+each
                except dst_client.ZenJsonClientError,e:
                    print e
                    return True
        return False
    except dst_client.ZenJsonClientError, e:
        print "Error getting device class tree."
        print e
        return True



def inject_devices_check_and_inject_Groups(source_device):
    groups = []
    groups_processed = []
    for each in source_device['groups']:
        try:
            groups.append(each['path'].replace('/Groups',''))
        except KeyError, e:
            print "Something went wrong, please send this to developer: "
            print "each:", each
            print "Source dev:", source_device['groups']

    for group in groups:
        lst = group.split('/')
        while '' in lst:
            lst.remove('')
        groups_processed.append(lst)
    #Here we are going to pull groups from destionation instance then import missing.
    try:
        response = dst_client.router.service.getTree(id='/zport/dmd/Groups')
        devicesGroupsList = response.result
        devicesGroupsList = passthroughTree(devicesGroupsList, [])
        newDGL = []
        for each in devicesGroupsList:
            newDGL.append(each.replace('/zport/dmd/Groups',''))
        while '' in newDGL:
            newDGL.remove('')
        newDGL2=[]
        for gr in newDGL:
            lst = gr.split('/')
            while '' in lst:
                lst.remove('')
            newDGL2.append(lst)
        for eachGr in groups_processed:
            if eachGr in newDGL2:
                print "Group %s is already exists at destination side. " % (string.join(eachGr,'/'))
            else:
                #print "Group %s is not exists at destination side. " % (string.join(eachGr,'/'))
                cUid = '/zport/dmd/Groups'
                for each in eachGr:
                    try:
                        response = dst_client.router.service.addNode(type='organizer', contextUid=cUid, id=each)
                        print response.result
                        cUid=cUid+'/'+each
                    except dst_client.ZenJsonClientError,e:
                        print e
                        return True
        #print newDGL2
        #print groups_processed
    except dst_client.ZenJsonClientError,e:
        print e
        return True
    return False

def updateIps(data_to_inject):
    #Here we should make an ip update if related flag is set!
    for device_dict in data_to_inject:
        if (device_dict["ipaddr"] != None):
            #Firstly we should wait until zenoss will add the new device. We are going to pull dev list few times.
            try:
                resp = dst_client.router.device.resetIp(uids=[device_dict["uid"]],
                    hashcheck=1,
                    params=None,
                    sort='name',
                    ip=device_dict["ipaddr"])
                print "Tried to reset ip for device ", device_dict["uid"]
                print "Zenoss says:", resp.result
            except dst_client.ZenJsonClientError,e:
                print "Error resetting ip for device:"
                print e

def inject_devices(data_to_inject, sync_or_not_production_state):
    #print data_to_inject   #just for DEBUG
    #sys.exit(0)     #just for DEBUG
    print "Going to inject devices into destination zenoss instance..."
    print "Got source data:"
    for each in data_to_inject:
        print "Device: ", each
    print "\n"
    for device_dict in data_to_inject:
        retry_again = True
        failed_count = 0
        #Before adding device we should check if related deviceClass and groups exists
        flag=True
        while (flag):
            flag=inject_devices_check_and_inject_deviceClass(device_dict)
        flag=True
        while flag:
            flag=inject_devices_check_and_inject_Groups(device_dict)
        #
        while retry_again:
            retry_again = False
            try:
                device_groups_paths = []
                for eachGr in device_dict['groups']:
                    device_groups_paths.append(eachGr['path'])
                if (sync_or_not_production_state):
                    response = dst_client.router.device.addDevice(deviceName=device_dict["name"],
                        deviceClass=device_dict["class"],
                        locationPath=device_dict["location"],
                        groupPaths=device_groups_paths,
                        productionState=device_dict['productionState']
                    )
                else:
                    response = dst_client.router.device.addDevice(deviceName=device_dict["name"],
                        deviceClass=device_dict["class"],
                        locationPath=device_dict["location"],
                        groupPaths=device_groups_paths,
                )
                if response.result["success"] == True:
                    retry_again = False
                    print "Successful import: %s" % (device_dict["uid"])

                else:
                    retry_again = False
                    print "Sorry, can't import device; zenoss says: ", response.result
                    #here we should try to update production state
                    print "Trying to update production state for device %s" % (device_dict["uid"])
                    try:
                        response = dst_client.router.device.setProductionState([device_dict["uid"]],
                                                                                prodState=device_dict['productionState'],
                                                                                hashcheck=1)
                        if response.result["success"] == True:
                            print "Production state for device %s has been set." % (device_dict["uid"])
                        else:
                            print "Failed setting production state for device %s." % (device_dict["uid"])
                            print "Zenoss says: %s" % response.result
                    except dst_client.ZenJsonClientError,e:
                        print e

            except dst_client.ZenJsonClientError, e:
                retry_again = True
                failed_count +=1
                if (failed_count > 3):
                    print "Sorry, can't add device %s" % (device_dict["uid"])
                    retry_again = False

    pass

#main loop#
SYNC_PRODUCTION=False
RESETIP=False
if ("--help" in sys.argv or "-h" in sys.argv):
    print "Synchronize quick help:"
    print "--sync_prod - sync production state (will sync if flag present)"
    print "--ipsync - resetIP thing instead of device sync"
    sys.exit(0)

if ("--sync_prod" in sys.argv):
    SYNC_PRODUCTION=True

if ("--ipsync" in sys.argv):
    RESETIP=True

if (RESETIP):
    updateIps(pull_devices_src())
else:
    inject_devices(pull_devices_src(), SYNC_PRODUCTION)

#print pull_devices_src()