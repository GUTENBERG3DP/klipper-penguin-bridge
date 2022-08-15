#!/usr/bin/python3
import sys
import socket
import fcntl
import struct

def get_ip_address(ifname):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip =  socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24])
        s.close()
    except Exception as e:
        return "none"
    return ip


def main():
    if len(sys.argv) > 1:
        print(get_ip_address(sys.argv[1]))
        sys.exit(0)
    else:
        print("none")
        sys.exit(0)
        


if __name__=="__main__":
    main()