#!/usr/bin/python
import sys
import usb

# Adapted from http://www.media.mit.edu/resenv/classes/MAS961/plug/PlugUSB.py

class DeviceDescriptor(object) :
    def __init__(self, vendor_id, product_id, interface_id) :
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.interface_id = interface_id

    def getDevice(self) :
        """
        Return the device corresponding to the device descriptor if it is
        available on a USB bus.  Otherwise, return None.  Note that the
        returned device has yet to be claimed or opened.
        """
        print "Searching for device..."
        while True:
            buses = usb.busses()
            for bus in buses :
                for device in bus.devices :
                    if device.idVendor == self.vendor_id :
                        if device.idProduct == self.product_id :
                            print "Found on bus: %s" % (bus.dirname)
                            return device

class Device(object) :
    
    VENDOR_ID = 0x08f7
    PRODUCT_ID = 0x0001
    INTERFACE_ID = 0
    BULK_IN_EP = 130
    BULK_OUT_EP = 2
    RETURN_SET_CMDS = (7,8,9,10,11,115,201)
    RETURN_STR_CMDS = (105,116,117)
    
    CMD_7_OUTPUT = ('softwareid',
                    'error',
                    'battery',
                    8888,
                    'sampletime',
                    'triggercondition',
                    'channelfunction',
                    'channelpost',
                    'channelfilter',
                    'numsamples',
                    'recordtime',
                    'temperature',
                    'piezoflag',
                    'systemstate',
                    'datastart',
                    'dataend',
                    'systemid')

    def __init__(self) :
        self.device_descriptor = DeviceDescriptor(self.VENDOR_ID,
                                                  self.PRODUCT_ID,
                                                  self.INTERFACE_ID)
        self.device = self.device_descriptor.getDevice()
        self.handle = None

    def open(self) :
        """Open a connection to the LabPro device, and bring it out of standby"""
        self.handle = self.device.open()
        if sys.platform == 'darwin' :
            # XXX : For some reason, Mac OS X doesn't set the
            # configuration automatically like Linux does.
            self.handle.setConfiguration(1)
        self.handle.claimInterface(self.device_descriptor.interface_id)
        self.writeDataPacket('s')

    def close(self) :
        """Close the connection to the LabPro device"""
        self.handle.releaseInterface()

    def writeDataPacket(self, data):
        """Write a single data packet to the opened device.
        
        Expects a string, which will be appended with a CR before being sent.
        """
        print "<< "+data
        self.handle.bulkWrite(Device.BULK_OUT_EP, data+'\r', 200)
            
    def readDataPacket(self, bytesToGet=64):
        """Read a single packet from the opened device. Returns as tuple of ascii codes.
        
        bytesToGet - Device's sent packet size (defaults 64)
        """
        try:
            return self.handle.bulkRead(Device.BULK_IN_EP, bytesToGet, 500)
        except usb.USBError:
            if not sys.exc_value.message == 'No error':
                raise
                
    def readDataPackets(self, bytesToGet=64):
        """Reads as many packets as possible from the device. Returns string of retrieved data."""
        string = ''
        data = self.readDataPacket(bytesToGet)
        while data:
            for bit in data:
                if bit:
                    string += chr(bit)
            data = self.readDataPacket(bytesToGet)
        print ">> "+string
        return string
        
    def parseData(self, data):
        out = []
        for item in data.split(','):
            if item:
                out.append(float(item.strip(' {}\r\n')))
        return out
    
    def doCommand(self, cmd, *args):
        """Sends a specific command, accepts an integer command followed by as many options as required.
        
        Usage: doCommand(1, 1, 2, 3, 4)
        Returns: None, or a tuple of parsed data if the command is expected to return data.
        """
        argstr = ''
        cmd = int(cmd)
        if args:
            for arg in args:
                argstr += ',%s' % arg
        self.writeDataPacket('s{%s%s}\r' % (cmd, argstr))
        retval = self.readDataPackets()
        if cmd in self.RETURN_SET_CMDS:
            # Get data and parse as set of floats
            return self.parseData(retval)
        elif cmd in self.RETURN_STR_CMDS:
            # Get data and parse as string
            return retval
            
    def getDeviceStatus(self):
        status = []
        while 8888.0 not in status:
            status = self.doCommand(7)
        self.status = dict(zip(self.CMD_7_OUTPUT, status))
        return self.status
        
    def getSensorStatus(self, sensor):
        status = self.doCommand(8, sensor, 0)
        return status[0]
        
    def getData(self):
        self.writeDataPacket('g\r')
        return self.parseData(self.readDataPackets())

def main(argv=None):
    try:
        import readline
    except:
        pass
    lp = Device()
    lp.open()
    lp.doCommand(1999,2000,80,1000,60,500,40)
    
    print "Enter commands in the format #,#,#\nQ for quit"
    s = raw_input('LabPro> ')
    while s.upper() != 'Q':
        commands = s.split(',')
        if not commands[0] in ('s', 'g', 'r'):
            print lp.doCommand(*commands)
        elif commands[0] == 'r':
            print lp.getDeviceStatus()
        else:
            lp.writeDataPacket(commands[0]+'\r')
            print lp.readDataPackets()
        s = raw_input('LabPro> ')
    lp.doCommand(1999,2000,40,1000,60,500,80)
    lp.close()

if __name__ == "__main__" :
    main()
