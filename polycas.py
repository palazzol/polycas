
import argparse
import serial
import time
import sys
from pathlib import Path

SYNC = b'\xe6'
SOH  = b'\x01'

TYPE_DATA = b'\x00'
TYPE_COMMENT = b'\x01'
TYPE_END = b'\x02'
TYPE_EXEC = b'\x03'

class CassetteProgram:
    def __init__(self):
        # header consists of sync characters followed by Start of header
        self.header = SYNC * 16 + SOH
        self.bytes = b''

    def __createChecksum(self, s):
        if s == b'':
            return b''
        sum = 0
        for b in s:
            sum += b
        sum %= 0x100
        return bytes([(0x100-sum)%0x100])

    def __createSection(self, address, data, sectiontype):
        if sectiontype == TYPE_EXEC:
            execaddr = address
            address = 0
        else:
            execaddr = address
        a = self.name + \
             bytes([address % 0x100, address // 0x100]) + \
             bytes([len(data) % 0x100]) + \
             bytes([execaddr % 0x100, execaddr // 0x100]) + \
             sectiontype
        if len(data) == 0:
            b = b''
        else:
            b = data
        self.bytes += self.header + a + self.__createChecksum(a) + b + self.__createChecksum(b)
             
    def setName(self, name):
        if len(name) > 8:
            print("Error: program name field greater than 8 characters")
            sys.exit(-1)
        # pad the name field with spaces up to 8 chars
        if len(name) < 8:
            name = name + (b' ' * (8-len(name)))
        self.name = name

    def createDataMessage(self, address, data):
        self.__createSection(address, data, TYPE_DATA)

    def createCommentMessage(self, s):
        self.__createSection(0x0000, s, TYPE_COMMENT)

    def createEndMessage(self):
        self.__createSection(0x0000, b'', TYPE_END)

    def createExecMessage(self, execaddr):
        self.__createSection(execaddr, b'', TYPE_EXEC)

    def loadFromBin(self, infile, loadaddr, execaddr, name):
        print('Creating cas object...')
        self.setName(name)
        self.createCommentMessage(b'\r\nLOADING START\r\n')
        with open(infile, 'rb') as f:
            address = loadaddr
            increment = 0x100
            data = f.read(increment)
            while len(data) != 0:
                self.createDataMessage(address,data)
                address += increment
                data = f.read(increment)
            self.createCommentMessage(b'LOADING END\r\n')
            if execaddr is not None:
                self.createExecMessage(execaddr)
            else:
                self.createEndMessage()

    def load(self, infile):
        print('Loading cas file...')
        with open(infile, 'rb') as f:
            self.bytes = f.read()

    def save(self, outfile):
        print('Saving cas file...')
        with open(outfile, 'wb') as f:
            f.write(self.bytes)

    def saveAsWavs(self):
        print('Saving wav files...')

    def stream(self, port):
        print('Streaming to serial port...')
        ser = serial.Serial(port, 300, stopbits=2, timeout=1, write_timeout=1)
        #print(ser.get_settings())
        self.send(ser, self.bytes)
        print("Done")
        while 1:
            sleep(1)

    def send(self, ser, msg):
        for i in range(0,len(msg)):
            ser.write(msg[i:i+1])
            time.sleep(11/300)

def main():
    # Parse Arguments
    def auto_int(x): # function to handle ints and int literals
        return int(x,0)
    parser = argparse.ArgumentParser(description = 'polycas - Poly-88 Cassette Utility')
    parser.add_argument('-i','--infile',help='Input File',required=True)
    parser.add_argument('-o','--outfile',help='Output File',required=False)
    parser.add_argument('-n','--name',default=b' ',help='Name',required=False)
    parser.add_argument('-p','--port',help='Serial Port Name',required=False)
    parser.add_argument('-a','--addr',type=auto_int,help='Load Address',required=False)
    parser.add_argument('-e','--exec',type=auto_int,help='Exec Address',required=False)
    parser.add_argument('-w','--wav',help='Write WAV files',required=False,action="store_true")
    args = parser.parse_args()

    # Create or load cas file
    input_file_path = Path(args.infile)
    if input_file_path.suffix != '.cas':
        if args.addr is None:
            parser.print_help()
            sys.exit(-1)
        casobj = CassetteProgram()
        casobj.loadFromBin(args.infile, args.addr, args.exec, args.name)
        if args.outfile is not None:
            casobj.save(args.outfile)
    else:
        casobj = CassetteProgram()
        casobj.load(args.infile)
        
    # save to wav files
    if args.wav:
        casobj.saveAsWavs()
    # stream file to serial if desired
    if args.port:
        casobj.stream(args.port)

'''
def oldmain():
    argv = sys.argv
    if len(argv) != 4 and len(argv) != 5:
        print('Usage: polyload <filename> <startexecaddr> <comport> [recordname]')
        sys.exit(-1)
    filename = argv[1]
    startaddr = int(argv[2],0)
    comport = argv[3]
    if len(argv) == 5:
        rname = argv[4].encode('ascii')
    else:
        rname = b' '
    ser = serial.Serial(comport, 300, stopbits=2, timeout=1)
    pgm = CassetteProgram()
    pgm.setName(name=rname)
    msg = pgm.createCommentMessage(b'\r\nLOADING START\r\n')
    Write(ser,msg)
    print("LOADING START")
    f = open(filename,'rb')
    address = startaddr
    increment = 0x100
    data = f.read(increment)
    while len(data) != 0:
        msg = pgm.createDataMessage(address,data)
        Write(ser,msg)
        print(f"{pgm.name.decode()} {address:04X}")
        address += increment
        data = f.read(increment)
    msg = pgm.createCommentMessage(b'LOADING END\r\n')
    Write(ser,msg)
    print("LOADING END")
    msg = pgm.createExecMessage(startaddr)
    Write(ser,msg)
    print("Done")
    while True:
        time.sleep(1)
'''

if __name__ == '__main__':
    #import serial.tools.list_ports
    #print([comport.device for comport in serial.tools.list_ports.comports()])
    main()

"""
TBD - redo this section
SAMPLE commands:
python polyload.py tetris_poly88.bin 0x1000 COM6
python polyload.py demo.bin 0x1000 COM6
python polyload.py bezier.bin 0x1000 COM6
python polyload.py lenna.bin 0x1000 COM6
python polyload.py readwritedi.bin 0x0c6a COM6
python polyload.py readwrite.bin 0x0c6a COM6
"""
