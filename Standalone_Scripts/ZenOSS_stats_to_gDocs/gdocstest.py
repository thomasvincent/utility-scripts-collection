#!/usr/bin/python

import time
import gdata.spreadsheet.service

email = 'youmail@gmail.com'
password = 'yourpassword'

# Find this value in the url with 'key=XXX' and copy XXX below
spreadsheet_key = '0ApMTQyOHeptsdC0zNVdZRDJINmlReUdNT3VMeFlaMlE'
worksheet_id = 'od6' #first woksheet id is always od6. 

spr_client = gdata.spreadsheet.service.SpreadsheetsService()
spr_client.email = email
spr_client.password = password
spr_client.source = 'myclient'
spr_client.ProgrammaticLogin()

for i in range(1,30):
    entry = spr_client.UpdateCell(i,1,("i="+str(i)),spreadsheet_key)
    print "Row #"+str(i)
