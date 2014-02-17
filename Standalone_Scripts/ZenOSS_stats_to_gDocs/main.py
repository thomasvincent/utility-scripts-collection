import curses
import time
import api_example
###########################################################################################################
def getEventsFromZENOSS():
    z = api_example.ZenossAPIExample()
    # Get events from Zenoss
    rawEvents = z.get_events()['events']
    events = []
    #Iterate through raw data and obtain only needed data.
    for x in rawEvents:
        events.append(
            [
                x['device']['text'],
                x['component']['text'],
                x['summary'],
                x['eventClass']['text']
            ]
        )
    return rawEvents
###########################################################################################################
def parseAndInsertDataIntoGoogleSpreadSheet(source_events):
    f = open("report.html","w")
    #printing events listing
    device_list = []
    for event in source_events:
        f.write("Device: "+str(event['device']['text'])
                +"; Component: "+str(event['component']['text'])
                +"; Summary: "+str(event['summary'])
                +"; EventClass: "+str(event['eventClass']['text'])
                +"\n")
        device_list.append(event['device']['text'])

    f.write("\n\n\n\n")

    for device in device_list:
        total_events_count = len(source_events)
        current_device_event_count = 0
        for event1 in source_events:
            if (event1['device']['text'] == device):
                current_device_event_count +=1
        f.write("Device \""+device+"\" produces "+str((100.0/total_events_count)*current_device_event_count)+"% of total events\n" )



    f.close()

    pass
###########################################################################################################
def main():
    zenoss_events = getEventsFromZENOSS()
    parseAndInsertDataIntoGoogleSpreadSheet(zenoss_events)

###########################################################################################################
if __name__ == "__main__":
    main()
