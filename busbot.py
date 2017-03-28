import urllib2
import json
import time

URL = 'http://shuttlebusapp.azurewebsites.net/position'
FILENAME = 'GPSLog.txt'

def getData(URL):
    busdata = urllib2.urlopen(URL)
    return busdata.read()

def parseJSON(dataString):
    return json.loads(dataString)

def initLog(fileName):
    f = open(fileName, 'a')
    return f

def logData(f, logTimeMinutes, periodSec=5):
    numIterations = int(round((logTimeMinutes*60)/periodSec))
    for x in xrange(0,numIterations):
        f.write(getData(URL))
        f.write('\n')
        print '%d / %d' % (x+1, numIterations)
        time.sleep(periodSec)

class Cbuffer:
    def __init__(self, length):
        self.length = length
        self.buffer = list()
        self.currptr = 0;
        for i in xrange(length):
            self.buffer.append(0)
    def write(self, data):
        self.buffer[self.currptr] = data
        self.currptr = (self.currptr+1) % self.length

        
class Bus:
    def __init__(self, name, data):
        self.name = name
        self.track = Cbuffer(60)
        self.config = dict()
        self.parse(data)
    def parse(self, data):
        pos = data['Positions'][self.name]
        conf = data['Config']['buses'][self.name]
        pos.pop('bus')
        self.track.write(pos)
        self.config = conf


LOG = 0
RUN_LIVE = 0
if LOG:
    f = initLog(FILENAME)
    logData(f, 5)
    f.close()

busses = dict()

if RUN_LIVE == 0:
    f = open(FILENAME,'r')
    for line in f:
        data = parseJSON(line)
        busid = data['Positions'].keys()
        for id in busid:
            if busses.has_key(id):
                busses[id].parse(data)
            else:
                busses[id] = Bus(id, data)


