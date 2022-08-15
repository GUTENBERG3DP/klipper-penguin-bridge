#!/usr/bin/python3
import sys
from os.path import exists

FILE_LOCATION = "/home/pi/gcode_files/SDCARD/wifi-config.json"

def main():
    try:
        print(exists(FILE_LOCATION))
        sys.exit(0)
    except Exception as e:
        print(False)
        sys.exit(0)


if __name__=="__main__":
    main()