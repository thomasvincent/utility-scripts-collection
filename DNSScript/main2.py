#!/usr/bin/python2
'''
Created on May 15, 2011

@author: thomasvincent
'''
#System libraries
import sys
import os
import tempfile
import string
from sets import Set
from fileinput import close
import re #Regular expressions
from getpass import getpass

#DNS Libraries
import dns.resolver
import dns.query
import dns.zone
from dns.exception import DNSException
from dns.rdataclass import *
from dns.rdatatype import *
#For GDOCS
import gdata.docs.data
import gdata.docs.client
import gdata.spreadsheet.service


#CONSTANTS

TINYDNS_CONFIG_DIR = "/service/tinydns"

####################################################

def getzone(domain):
    print "Getting NS records for", domain
    answers = dns.resolver.query(domain, 'NS')
    ns = []
    for rdata in answers:
        n = str(rdata)
        print "Found name server:", n
        ns.append(n)

    for n in ns:
        print "\nTrying a zone transfer for %s from name server %s" % (domain, n)
        try:
            zone = dns.zone.from_xfr(dns.query.xfr(n, domain))
        except DNSException, e:
            print e.__class__, e
    
    f = open("/tmp/hosts","a")
    
    for name, node in zone.nodes.items():
        rdataset = node.get_rdataset(rdclass=IN, rdtype=A)
        if not rdataset:
            continue
        for rdataset in rdataset:
            print rdataset, name.to_text().replace("@",domain,1)
            print >>f, rdataset, name.to_text().replace("@",domain,1)
    f.close()
    #Unique sort section
    file1 = open("/tmp/hosts","r");
    linesoffile = file1.readlines()
    unique = set(linesoffile)
    file1.close()
    file2 = open("/tmp/hosts","w")
    for eee in unique:
        print >>file2, eee.replace("\n","",1)
    file2.close()
    #End of section 
    return

#############################################################################################

def findinfile(addr,fn):
    if (fn==""):
        file = open("/tmp/hosts", "r")
    else:
        file = open(fn, "r")
        
    mylist = set()
    while 1:
        line = file.readline()
        if not line:
            break
        else:
            data = string.split(line, ' ')
            if(data[0]==addr):
                mylist.add(data[1])
            if(addr.replace("\n","",1)==data[1].replace("\n","",1)):
                mylist.add(data[0])    
    file.close()
    for i in mylist:
        print i.replace("\n","",1)
        
    return

##############################################################################################

def tinydns_import(dir):
    print "Importing data from TinyDNS data file..."
    print "TynyDNS config dir: ",dir
    #Load file into memory
    datafile = open((dir+"/root/data"),"r");
    ddata = datafile.readlines()
    datafile.close()
    #Data loaded into memory
    fh = open("/tmp/hosts","a")
    for rec in ddata:
        if(re.search('(^[\=|\+][a-z\.]*:([0-9]{1,3}\.){3}[0-9]{1,3}.*[0-9]*$)',rec)):
            temp = rec.replace("+","",1)
            temp = temp.replace("=","",1)
            temp1 = string.split(temp, ':')
            hostname = temp1[0]
            ipaddr = temp1[1]
            #Writing data to hosts
            print >>fh, ipaddr,hostname
    fh.close()
    #Sort file unique
    file1 = open("/tmp/hosts","r");
    linesoffile = file1.readlines()
    unique = set(linesoffile)
    file1.close()
    file2 = open("/tmp/hosts","w")
    for eee in unique:
        print >>file2, eee.replace("\n","",1)
    file2.close()
    #enf of section
    return 

##############################################################################################

def search_gdocs(key,email,password,search_pattern):
    source   = 'myspreadsheetdownloader'
    
    #Debug
    #key = "0ApMTQyOHeptsdEJIRWZYWnVQSUpIZFAzREIxdzBPZFE"
    #print key
    #print email
    #print password
    if (email==""):
        email = raw_input("Email: ")
    if (password==""):
        password = getpass("Password: ")
    if (key==""):
        key = raw_input("Document token: ")

    gd_client     = gdata.docs.client.DocsClient()
    gd_client.ssl = True
    gd_client.ClientLogin(email,password,source,)

    gs_client     = gdata.spreadsheet.service.SpreadsheetsService()
    gs_client.ssl = True
    gs_client.ClientLogin(email,password,source,)

    docs_token = gd_client.auth_token
    gd_client.auth_token = gdata.gauth.ClientLoginToken(gs_client.GetClientLoginToken())
    gd_client.auth_token = docs_token
    doc = gd_client.GetDoc('spreadsheet:%s' % key)
    gd_client.auth_token = gdata.gauth.ClientLoginToken(gs_client.GetClientLoginToken())
    #gd_client.auth_token = docs_token
    gd_client.Export(doc, '/tmp/spreadsheeet.csv')
    gd_client.auth_token = docs_token
    
    #Downloading done. Find!
    file = open("/tmp/spreadsheeet.csv", "r")
    datalist = file.readlines()
    for item in datalist:
        enum = string.split(item,",")
        #0 - IP, 1 - hostname, 3 - IP
        enum[0] = enum[0].replace("\n","",1)
        enum[1] = enum[1].replace("\n","",1)
        enum[2] = enum[2].replace("\n","",1)
        search_pattern = search_pattern.replace("\n","",1)
        if(enum[0]==search_pattern or enum[2]==search_pattern):
            print enum[1]
        if(enum[1]==search_pattern):
            print enum[0]
            print enum[2]
    file.close()
    return

##############################################################################################

def display_help():
    print "Usage:"
    print "-h                                                                         - display this message"
    print "-get <domain>                                                              - Get zone for the specified domain" 
    print "-server <servername or ip addr> <optional: hosts file name>                - Search in file"
    print "-tinydns <optional: path to tinydns config dir>                            - Grab records from tinydns db"
    print "-gdsearch <pattern> <opt: email> <opt: password> <opt: document_token>     - Search in GDocs SP"
    return 

##############################################################################################
def main():
    p_help_args     = ("-h","--h","-help","--help","-usage","--usage",)
    p_get_args      = ("-get","--get",)
    p_server_args   = ("-server","--server",)
    p_tdns_args     = ("-tinydns","--tinydns",)
    p_gdsearch_args = ("-gdsearch","--gdsearch")
    
    possible_args   = ("-h","--h","-help","--help","-usage","--usage",
                       "-get","--get",
                       "-server","--server",
                       "-tinydns","--tinydns",
                       "-gdsearch","--gdsearch",
                       )
    
    if (len(sys.argv) >=2 ): #Means, if some args.
        if (sys.argv[1] in possible_args):
            
            if(sys.argv[1] in p_help_args):
                #Display Help 
                display_help()
            
            if(sys.argv[1] in p_get_args):
                #Get zone
                if (len(sys.argv) > 2):
                    getzone(sys.argv[2])
                else:
                    print "Missing second argument!"
            
            if(sys.argv[1] in p_server_args):
                #Find in file --server key
                if (len(sys.argv) == 4):
                    findinfile(sys.argv[2],sys.argv[3])
                    sys.exit()
                if (len(sys.argv) == 3):
                    findinfile(sys.argv[2],"")
                else:
                    print "Missing second argument!"
            
            if(sys.argv[1] in p_tdns_args):
                #Find in file --server key
                if (len(sys.argv) > 2):
                    tinydns_import(sys.argv[2])
                else:
                    print "Using default directory prefix"
                    tinydns_import(TINYDNS_CONFIG_DIR)
            
            if(sys.argv[1] in p_gdsearch_args):
                #2 - email, 3 - pass, 4 - key
                if (len(sys.argv) > 2):
                    par1=""
                    par2=""
                    par3=""
                    if(len(sys.argv) == 4):
                        par1 = sys.argv[3]
                    if(len(sys.argv) == 5):
                        par1 = sys.argv[3]
                        par2 = sys.argv[4]
                    if(len(sys.argv) == 6):
                        par1 = sys.argv[3]
                        par2 = sys.argv[4]
                        par3 = sys.argv[5]
                    search_gdocs(par3, par1, par2,sys.argv[2])
                else:
                    print "You must supply search pattern at least!"
        else:
            if(len(sys.argv) == 2): #Default Action
                findinfile(sys.argv[1],"") 
    
    else:
        display_help()
    

    return

if __name__ == '__main__':
    main()
