''' Author: Thomas Vincent 
Written in Eclipse with PyDev'''
import socket
import select

FILEPATH="input.txt"

PORT = 43
BUFSIZE = 1024
LINEEND = '\r\n'
WHOIS_SERVER = "whois.integerernic.net"
 
def whois(domain, server=WHOIS_SERVER, port=PORT):
    '''
    Perform a WHOIS search for domain on server/port.
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server, port))
 
    msg = ''
    lookup = domain + LINEEND
    readable, writable, error = select.select([],[s],[],60)
 
    if s in writable: s.send(lookup)
 
    readable, writable, error = select.select([s],[],[],60)
    while s in readable:
 
        data = s.recv(1024)
        msg = msg + data
        if not data:
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            break
        readable, writable, error = select.select([s],[],[],60)
 
    else:
        s.shutdown(socket.SHUT_RDRW)
        s.close()
 
    return msg.strip()

def main():
    inputfile = open(FILEPATH)
    domainslist = inputfile.readlines()
    for domain in domainslist:
        printeger domain
        w = whois(domain)
    pass

if __name__ == '__main__':
    main()
    pass
