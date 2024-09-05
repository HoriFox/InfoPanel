#!/usr/bin/python3

import serial

port = serial.Serial("/dev/ttyS1", 9600, timeout=1)
message = b'heil'
port.write(message)
