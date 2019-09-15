#!/usr/bin/env python3

import serial
import glob
import collections
from time import sleep
import argparse
import os.path

#arg parser
discription_text = 'TekScope serial daemon for recieving PNG files over serial'
program = "scoped, the scope printer daemon"
version = 1
parser = argparse.ArgumentParser(description = discription_text, prog = program)
parser.add_argument("-V", "--version", help = "show program version", action = "store_true")
parser.add_argument("-d", "--directory", help = "set save directory")
parser.add_argument("-p", "--prefix", help = "set file prefix")
parser.add_argument("-n", "--number", help= "set file number")
parser.add_argument("-l", "--leading", help="leading zeros for file number")
parser.add_argument("-s", "--serialport", help="serial port device")
parser.add_argument("-b", "--baudrate", help ="set baudrate")

args = parser.parse_args()

if args.version:
    print(program + ", version %i\n" % version)
    quit()

if args.directory:
    if os.path.exists(args.directory):
        print("Directory set to %s" % args.directory)
        directory = args.directory + "/"
    else:
        print("Error: %s does not exist" % args.directory)
        quit()
else:
    directory = "./"

if args.serialport:
    if os.path.exists(args.serialport):
        print("Serial port set to %s" % args.serialport)
        serialport = args.serialport
    else:
        print("Error: %s does not exist"% args.serialport)
        quit()
else:
    serialport = "/dev/ttyUSB0"

if args.prefix:
    print("File prefix set to %s" % args.prefix)
    prefix = args.prefix
else:
    prefix = "scope"

if args.number:
    print("File starting number set to %s" % args.number)
    filenumber = int(args.number)
else:
    filenumber = 0

if args.leading:
    print("Leading zeros set to %s" % args.leading)
    leading_zeros = int(args.leading)
else:
    leading_zeros = 3

if args.baudrate:
    print("Baudrate set to %s" % args.baudrate)
    baudrate = int(args.baudrate)
else:
    baudrate = 38400 
    
# buffer is the data buffer containing the PNG file as its transmitted
buffer = []
# shiftregister is a FIFO shift register that the script uses to search for
# the PNG's IEND message. 
shiftregister = collections.deque([], 8)

suffix = ".png"

#filelist contains the PNG files the directory
filelist = [f for f in glob.glob(directory + "/*.png")]


def state0():
# in state zero, we clear the buffer and scan the serial port for the 
# PNG start code 0x89 every 1 second. Once recieved, the code is placed on 
# the buffer and state1 is entered
    returnvalue = 0
    buffer.clear()
    startcode = 0x89
    tester = True
    while tester:
        for line in ser.read():
            if line == startcode:
                print("Start code recieved")
                tester = False
                buffer.append(line)
                returnvalue = 1   
        sleep(1)
    return returnvalue

def state1():
# in state 1, data from the serial port is appended to the buffer and shifted
# through the shift register right to left.  The shift register contains 8 bytes
# and the left most 4 bytes are scanned for IEND. Once IEND is detected, state
# 3 is entered.
    returnvalue = 1
    shiftregister.clear()
    tester = True
    while tester:
        for line in ser.read():
            buffer.append(line)
            shiftregister.append(chr(line))
            test = list(shiftregister)
            test =''.join(test)
            if test[0:4] == "IEND":
                tester = False
                print("Recieved EOF")
                #go to state 2
                returnvalue = 2
    return returnvalue

def state2():
# in state 2, a current reading of the write directory is obtained.  It checks
# do see if the filename to write already exists. If it does, the file number is
# increased and checked again until a filename is found that does not already
# exist.  The file is created and the buffer is dumped into it. The file is then
# closed. State0 is then entered.
    returnvalue = 0
    filenumber = 0
    #grab file list
    filelist = [f for f in glob.glob(directory+"*.png")]
    #does file exist
    while (directory + prefix+str(filenumber).zfill(3)+suffix in filelist):
        filenumber = filenumber + 1
    
    filename = directory + prefix + str(filenumber).zfill(3)+suffix
    #open file
    filehandle = open(filename, "wb")
    #write file
    
    filehandle.write(bytes(buffer))
    print("Writting " + filename + "...")
    #close file
    print("Closing " + filename + "...")
    filehandle.close()
    return returnvalue

def state_machine(argument):
# This is the code for the statemachine.  A dictionary is used to map state
# functions to return values.  The returned function for the mapped state is then
# returned
    switcher = {
        0: state0,
        1: state1,
        2: state2,
    }
    func = switcher.get(argument)
    return func()

# Main starts here #############################################################
# Open and configure serial port
ser = serial.Serial(
    port = serialport,
    baudrate = baudrate,
    parity = serial.PARITY_NONE,
    stopbits = serial.STOPBITS_ONE,
    bytesize = serial.EIGHTBITS,
    timeout = 0)
# Print to terminal
print("Connected to :" + ser.portstr)

# Preload state machine to state0 and run the state machine
state = 0
while True:
    state = state_machine(state)

ser.close()