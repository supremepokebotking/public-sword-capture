#!/usr/bin/env python3
import argparse
import serial
from time import sleep

#parser = argparse.ArgumentParser()
#parser.add_argument('port', default='/dev/tty.usbserial-A50285BI')
#args = parser.parse_args()

def send(msg, duration=0.15):
    print(msg)
    ser.write(f'{msg}\r\n'.encode('utf-8'));
    sleep(duration)
    ser.write(b'RELEASE\r\n');
    sleep(0.075)
#/dev/tty.usbserial-A50285BI
#ser = serial.Serial('/dev/tty.usbserial-A50285BI', 9600)
#ser = serial.Serial('/dev/tty.usbserial-AI05M0GQ', 9600)
#ser = serial.Serial('/dev/tty.usbserial-A50285BI', 9600)
#ser = serial.Serial('/dev/tty.usbserial-14640', 9600)
#ser = serial.Serial('/dev/ttyUSB0', 9600)
#ser = serial.Serial(args.port, 9600)

class Serial():

    def __init__(self, serial_port):
        self.ser = serial.Serial(serial_port, 9600)

    def send(self, msg, duration=0.1):
        print(msg)
        self.ser.write(f'{msg}\r\n'.encode('utf-8'));
        sleep(duration)
        self.ser.write(b'RELEASE\r\n');
#        sleep(0.075)
