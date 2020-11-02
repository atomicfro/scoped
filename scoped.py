#!/usr/bin/env python3
# Version 1.2

import serial
import io
import glob
import collections
from time import sleep
import argparse
import os.path
import threading
import atexit
import sys

# Globals
version = 1
baudrate = 0
directory = ''
serialport = ''
prefix = ''
number = 0
leading_zeros = 0
ser = 0
# buffer is the data buffer containing the PNG file as its transmitted
buffer = []
# shiftregister is a FIFO shift register that the script uses to search for
# the PNG's IEND message. 
shiftregister = collections.deque([], 8)
suffix = ".png"


def argument_parser():  ########################################################
#arg parser
    discription_text = 'TekScope serial daemon for recieving PNG files over serial'
    program = "scoped, the scope printer daemon"

    global baudrate
    global directory
    global serialport
    global prefix
    global number
    global leading_zeros
    global filenumber

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
        if os.name != 'nt':
            if os.path.exists(args.serialport):
                print("Serial port set to %s" % args.serialport)
                serialport = args.serialport
            else:
                print("Error: %s does not exist"% args.serialport)
                quit()
        else:
            print("Serial port set to %s" % args.serialport)
            serialport = args.serialport
    else:
        if os.name != 'nt':
            serialport = "/dev/ttyUSB0"
        else:
            serialport = "COM12"
            

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
################################################################################


def state0():   ################################################################
# in state zero, we clear the buffer and scan the serial port for the 
# PNG start code 0x89 every 1 second. Once recieved, the code is placed on 
# the buffer and state1 is entered
    returnvalue = 0
    buffer.clear()
    startcode = 0x89
    tester = True
    print("Waiting for transmission.")
    while tester:
        for line in ser.read():
            if line == startcode:
                print("Start code recieved.")
                tester = False
                buffer.append(line)
                returnvalue = 1   
        sleep(1)
    return returnvalue
################################################################################


def state1():   ################################################################
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
                print("Recieved EOF.")
                #go to state 2
                returnvalue = 2
    return returnvalue
################################################################################


def state2():   ################################################################
# In state 2, a current reading of the write directory is obtained.  It checks
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
    print("Writting %s..." % filename)
    #close file
    filehandle.close()
    print ("Finished writing %i bytes." % len(bytes(buffer)))
    return returnvalue
################################################################################


# state_machine(argument)   ####################################################
def state_machine(argument):
# This is the code for the statemachine. A dictionary is used to map state
# functions to return values. The returned function for the mapped state is then
# returned
    switcher = {
        0: state0,
        1: state1,
        2: state2,
    }
    func = switcher.get(argument)
    return func()
################################################################################


def quit_gracefully():  ########################################################
#  Called when ctl-C is captured for shutdown
    ser.close()
    print("Closed serial port. Good bye.")
################################################################################


def setup_serial(): ############################################################
#   Creates the serial object and sets up and tests the connection.
    # Open and configure serial port
    global ser
    ser = serial.Serial(
        port = serialport,
        baudrate = baudrate,
        parity = serial.PARITY_NONE,
        stopbits = serial.STOPBITS_ONE,
        bytesize = serial.EIGHTBITS,
        timeout = 2,
        )

    # Determine if scope is present by sending GPIB Identification query.
    ser.write(b'*IDN?\n')
    text = str(ser.readlines())
    # Get rid of formating from readline
    text = text[2:][:-5]
    if (len(text)):
        print("Succesfully connected to: %s on %s." % (text, ser.portstr))
    else:
        print("Unable to detect an instrument on %s." % ser.portstr)
################################################################################


# Main starts here #############################################################
def main():

    # parse arguments
    argument_parser()
    #setup serial device
    setup_serial()
    # allow for quiting gracefully from ctrl+c
    atexit.register(quit_gracefully)

    # Preload state machine to state0 and run the state machine
    state = 0
    sys.tracebacklimit=0
    while True:
        state = state_machine(state)
################################################################################

main()
