import urllib2
import json
import time
import datetime

URL = 'http://shuttlebusapp.azurewebsites.net/position'
FILENAME = 'GPSLog.txt'
BUFFER_SIZE = 720

PPL_COORD = [42.30138, -71.48414]
MTN_COORD = [42.30153, -71.47647]
RES_COORD = [42.30165, -71.47266]

# PP = [42.30148
# RES LEFT = [42.30175, -71.47290]
# MTN = [42.30145

RES_RAD = 0.00025
MTN_RAD = 0.00010
PPL_RAD = 0.00010

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
        #self.track = Cbuffer(BUFFER_SIZE)
        self.lat = []
        self.lng = []
        self.time = []
        self.config = dict()
        self.parse(data)
    def parse(self, data):
        pos = data['Positions'][self.name]
        timestamp = data['LastTime']
        conf = data['Config']['buses'][self.name]
        pos.pop('bus')
        #self.track.write(pos)
        lat = pos.pop('lat')
        lng = pos.pop('lng')
        self.lat.append(lat)
        self.lng.append(lng)
        self.time.append(timestamp)
        self.config = conf

    def getTimestamp(self,timeIndex):
        currTimeSec = self.time[timeIndex]/1000
        return datetime.datetime.fromtimestamp(currTimeSec).strftime('%Y-%m-%d %H:%M')

    def analyzeTrack(self):

        PPL_STATUS = 0
        MTN_STATUS = 0
        RES_STATUS = 0

        for i in xrange(len(self.lat)):
            lat = float(self.lat[i])
            lng = float(self.lng[i])

            PPL_LAT_DIFF = abs(lat-PPL_COORD[0])
            PPL_LNG_DIFF = abs(lng-PPL_COORD[1])

            MTN_LAT_DIFF = abs(lat-MTN_COORD[0])
            MTN_LNG_DIFF = abs(lng-MTN_COORD[1])
            
            RES_LAT_DIFF = abs(lat-RES_COORD[0])
            RES_LNG_DIFF = abs(lng-RES_COORD[1])

            if (PPL_LAT_DIFF <= PPL_RAD) and (PPL_LNG_DIFF <= PPL_RAD):
                PPL_STATUS = PPL_STATUS+1
            elif (MTN_LAT_DIFF <= MTN_RAD) and (MTN_LNG_DIFF <= MTN_RAD):
                MTN_STATUS = MTN_STATUS+1
            elif (RES_LAT_DIFF <= RES_RAD) and (RES_LNG_DIFF <= RES_RAD):
                RES_STATUS = RES_STATUS+1
            else:
                # In-Between Stops

                if PPL_STATUS > 0:
                    print 'Leaving  PP  (%s)' % self.getTimestamp(i)
                    PPL_STATUS = 0
                elif MTN_STATUS > 0:
                    print 'Leaving  MTN (%s)' % self.getTimestamp(i)
                    MTN_STATUS = 0
                elif RES_STATUS > 0:
                    print 'Leaving  RES (%s)' % self.getTimestamp(i)
                    RES_STATUS = 0

            if PPL_STATUS == 1:
                print 'Arriving PP  (%s)' % self.getTimestamp(i)
            elif MTN_STATUS == 1:
                print 'Arriving MTN (%s)' % self.getTimestamp(i)
            elif RES_STATUS == 1:
                print 'Arriving RES (%s)' % self.getTimestamp(i)

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


