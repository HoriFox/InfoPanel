#!/usr/bin/python3

import time
import serial

print("> Open serial port...")
port = serial.Serial("/dev/ttyS1", 9600, timeout=1)
print("> Send command to arduino animation...")
port.write(b'heil')

time.sleep(1)

print("> Send to arduino data request...")
port.write(b'data')

while True:
        response = port.readline()
        if response:
                print("> Message from arduino: %s" % response)