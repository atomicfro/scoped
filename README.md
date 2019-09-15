# scoped
The oscilloscope daemon.
This python script is designed to run in the background waiting for a Portable 
Network Graphics (PNG) file to be transmitted over serial.  The file is then given a
name and saved to the root directory.

scoped takes the following command line options:
  -h, --help                            Show help message and exit
  -V, --version                         Show program version
  -d DIRECTORY, --directory DIRECTORY   Set the save directory/path
  -p PREFIX, --prefix PREFIX            Set the file name prefix (default is scope)
  -n NUMBER, --number NUMBER            Set the starting file name number (default is 0)
  -l LEADING, --leading LEADING         Set leading zeros for file name (default is 2)
  -s SERIALPORT,--serialport SERIALPORT Set the listening serial port. (default /dev/ttyUSB0)
  -b BAUDRATE, --baudrate BAUDRATE      Set the transmission rate (default 38400)
  
When saving a file, scoped will first check to see if the file exists.  If it 
does, it will increment the number counter to avoid saving over existing files.

Filenames follow prefix + number + .png format.  Default is scope000.png.

This program was created specifically for the TDS-3000 series of Tektronix       
oscilloscopes with serial ports. This o-scope allows the hardcopy/print button on
the scope to be configured to transmit a PNG file over the serial port.
