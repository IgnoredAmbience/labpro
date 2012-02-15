#!/usr/bin/python
from LabPro import LabPro
import time
import csv

class BulkLabProDevice(LabPro.Device):
    def open(self):
        LabPro.Device.open(self)
        
    def close(self):
        LabPro.Device.close(self)
        
class Incrementor:
    def __init__(self, value):
        self.inc = int(value)
    
    def increment(self):
        val = self.inc
        self.inc += 1
        return val
        
def prompt(question, default=None):
    resp = raw_input('%s [%s] ' % (question, default or ''))
    while resp == '':
        if default is not None:
            resp = str(default)
        else:
            resp = raw_input('%s [%s] ' % (question, default or ''))
    return resp

def promptBool(question, default=None):
    ret = None
    while ret is None:
        resp = prompt(question, default)
        if resp.lower() in ('y', 'yes', '1', 't', 'true'):
            ret = True
        elif resp.lower() in ('n', 'no', '0', 'f', 'false'):
            ret = False
    return ret

def setupDevice(lp, incid, csv):
    numsensors = 0
    rv = []
    deviceid = incid.increment()
    
    description = prompt("Enter device description, eg room, location etc.")
    
    if lp.status['battery'] > 0:
        print "WARNING: Battery may be low! Currently rated at level %s" % lp.status['battery']
    lp.doCommand(0)
    lp.doCommand(6,3)                       # Turn sound off - hope for battery boost
    lp.doCommand(6,5,deviceid)     # Set ID
    rv.append(deviceid)
    
    for sensor in (1, 2, 3, 4):
        lp.doCommand(1, sensor, 1)
        sensortype = lp.getSensorStatus(sensor)
        if sensortype not in (10, 34):
            lp.doCommand(1, sensor, 0)
            rv.append(0)
        else:
            sensorname = lp.doCommand(116, sensor)
            print "Found channel %s, detected type %s as a %s" % (sensor, sensortype, sensorname)
            rv.append(sensortype)
            numsensors += 1
    
    if numsensors:
        samples = 12287 / numsensors
        sampletime = (4*24*60*60) / samples
        #sampletime = 5
        lp.doCommand(3, sampletime, samples, 0, 0, 0, 0, 0, 0, 0, 0)
        rv.append(samples)
        rv.append(sampletime)
        rv.append(description)
        rv.append(time.time())
        csv.writerow(rv)
    else:
        print "No sensors found!"
    
def downloadData(lp, logger):
    if (lp.status['systemstate'] % 16) == 3:
        print "Warning! Data is still being collected. Downloading will result in terminating the collection."
    if promptBool("Download data?", True):
        lp.doCommand(6, 0)
        lp.getDeviceStatus()    # Refresh this
        
        start = int(float(logger[7]))
        step = int(float(lp.status['sampletime']))
        end = start + (step * int(float(lp.status['numsamples']))) + 1
        # ( +1 below to go over endpoint)
        data = [range(start, end, step)]
        
        for sensor in range(4):
            if float(logger[sensor]):
                lp.doCommand(5, sensor+1, 3, 0, 0)
                data.append(lp.getData())
                
        data = zip(*data)   # Rotate the table by 90 degrees, make rows of data points from rows of data sets.
        
        datacsvfile = open('%d.csv' % lp.status['systemid'], 'wb')
        datacsv = csv.writer(datacsvfile)
        datacsvfile.write('# %s\r\n' % logger[6])
        datacsv.writerows(data)
        datacsvfile.close()
        return True
    else:
        return False

def main(argv=None) :
    loggers = {}
    try:
        loggercsvfile = open('loggers.csv', 'rb')
    except IOError:
        pass
    else:
        loggercsv = csv.reader(loggercsvfile)
        for line in loggercsv:
            loggers[int(line[0])] = line[1:]
        loggercsvfile.close()
    loggercsvfile = open('loggers.csv', 'ab')
    loggercsv = csv.writer(loggercsvfile)

    globalid = int(prompt("Enter global minimum device ID.", 100))
    incid = Incrementor(prompt("Enter minimum device ID for this instance.", 100))
    try:
        while True:
            lp = BulkLabProDevice()
            lp.open()
            lp.getDeviceStatus()
            
            systemid = int(lp.status['systemid'])
            if systemid < globalid or not downloadData(lp, loggers[systemid]):
                # System is not yet configured by us, do it now.
                setupDevice(lp, incid, loggercsv)
            
            lp.close()
            raw_input("*** Please disconnect the device before continuing! (Then hit enter) ***")
    except KeyboardInterrupt:
        loggercsvfile.close()
        
    """lp.doCommand(1, 1, 1)
    lp.doCommand(1, 2, 1)
    lp.doCommand(3,0.001,100,0,0,0,0,0,1,0)
    time.sleep((0.001*100) + 1)
    lp.writeDataPacket('g\r')
    string = lp.readDataPackets()

    print string
    print string.count(',') + 1
    lp.close()"""

if __name__ == "__main__" :
    main()
