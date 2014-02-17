#!/usr/bin/env python


import SoftLayer.API
import sqlite3
import argparse
import csv

api_username = 'set me'
api_key = 'set me'

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

def get_hardware_list():
    client = SoftLayer.API.Client('SoftLayer_Account', None, api_username, api_key)

    client.set_object_mask(object_mask)

    request_offset = 0
    hardware_lst = []
    data_limit = 500

    while True:
        client.set_result_limit(data_limit, request_offset)
        hardware = client.getHardware()
        request_offset += data_limit
        for each in hardware:
            hardware_lst.append(each)
        if (len(hardware) < data_limit):
            break

    output_list = []
    for eachDev in hardware_lst:
        ip=""
        hostname=""
        loc=""
        if ("privateIpAddress" in eachDev.keys()):
            ip=eachDev["privateIpAddress"]
        if ("hostname" in eachDev.keys()):
            hostname=eachDev["hostname"]
        if ("datacenter" in eachDev.keys()):
            loc=eachDev["datacenter"]
        output_list.append({
            "IP": ip,
            "HOSTNAME": hostname,
            "LOCATION": loc
        })

    return output_list


def store_to_database(hardware_list):
    database_connection = sqlite3.connect("storage.sqlite3db")
    db_cursor = database_connection.cursor()
    db_cursor.execute("CREATE TABLE if not exists SOFTLAYER_SOURCE (PK INTEGER PRIMARY KEY, HOSTNAME VARCHAR, IP VARCHAR, DC_ID INTEGER, DC_NAME VARCHAR, DC_LONGNAME VARCHAR)")
    db_cursor.execute("DELETE FROM SOFTLAYER_SOURCE")
    pk=0
    for hardware in hardware_list:
        pk+=1
        query_values = []
        query_values.append(pk)
        query_values.append(hardware['HOSTNAME']+".playdom.com")
        query_values.append(hardware['IP'])
        query_values.append(hardware['LOCATION']['id'])
        query_values.append(hardware['LOCATION']['name'])
        query_values.append(hardware['LOCATION']['longName'])
        db_cursor.execute("INSERT INTO SOFTLAYER_SOURCE values(?, ?, ?, ?, ?, ?)", query_values)

    database_connection.commit()
    database_connection.close()

    print "Pulled data has been written to an sqlite database called storage.sqlite3db"

def print_to_stdout(hardware_list):
    for hardware in hardware_list:
        print "IP: %s, HOSTNAME: %s, LOCATION: %s" % (hardware['IP'], hardware['HOSTNAME'], hardware['LOCATION'])
    
    print "Resulting list:"
    print repr(hardware_list)

    print "Total devices collected: ", len(hardware_list)

def store_to_csv(filename, hardware_list):
    with open(filename, 'wb') as csvfile:
        hardware_writer = csv.writer(csvfile)
        for hardware in hardware_list:
            hardware_writer.writerow([hardware['IP'], hardware['HOSTNAME'], hardware['LOCATION']])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--database", type=int, default=1, choices=[0, 1], help="1 (default) for store data in database")
    parser.add_argument("-s", "--stdout", type=int, default=1, choices=[0, 1], help="1 (default) for print output to stdout")
    parser.add_argument("-f", "--file", help="save output to csv file")
    
    args = parser.parse_args()

    DATABASE = (args.database == 1)
    STDOUT = (args.stdout == 1)
    FILE = args.file

    hardware_list = get_hardware_list()
   
    if STDOUT:
        print_to_stdout(hardware_list)

    if DATABASE:
        store_to_database(hardware_list)

    if FILE is not None:
        store_to_csv(FILE, hardware_list)