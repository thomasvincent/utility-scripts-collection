from xml.dom import minidom
import os
import subprocess
from xml.dom import minidom

xml_source = subprocess.Popen(['zendump'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]
xml_parsed = minidom.parseString(xml_source)

#xml_parsed = minidom.parse("/Users/tvincent/Downloads/dmp.xml")

def findDevices(xml_object):
    devices_list = []
    if (xml_object.childNodes):
        for each in xml_object.childNodes:
            if (each.childNodes):
                lst=findDevices(each)
                for each1 in lst:
                    devices_list.append(each1)
                if ("class" in each.attributes.keys()):
                    if (each.attributes["class"].value.lower() == "device"):
                        if ("id" in each.attributes.keys()):
                            devices_list.append(each.attributes["id"].value)
                            print each.attributes["id"].value

    return devices_list

dl = findDevices(xml_parsed)
print "Device count:", len(dl)
