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

    tripTime = dict()
    tripTime['PPL-MTN'] = 0
    tripTime['PPL-RES'] = 0
    tripTime['MTN-PPL'] = 0
    tripTime['MTN-RES'] = 0
    tripTime['RES-MTN'] = 0
    tripTime['RES-PPL'] = 0

    def __init__(self, name, data):
        self.name = name
        #self.track = Cbuffer(BUFFER_SIZE)
        self.lat = []
        self.lng = []
        self.time = []
        self.config = dict()
        self.nextStop = dict()
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
        self._setupRoute(self.config['route'])

    def getTimestamp(self,timeIndex):
        currTimeSec = self.time[timeIndex]/1000
        return datetime.datetime.fromtimestamp(currTimeSec).strftime('%Y-%m-%d %H:%M')

    def formatTimeStamp(self,timeMSec):
        return datetime.datetime.fromtimestamp(timeMSec/1000).strftime('%H:%M')

    def logTrip(self, DEP_STATION, DEP_TIMESTAMP, ARR_STATION, ARR_TIMESTAMP):
        alpha = 0.90
        key = DEP_STATION + '-' + ARR_STATION
        durationMSec = ARR_TIMESTAMP - DEP_TIMESTAMP
        prevDurationMSec = Bus.tripTime[key]
        Bus.tripTime[key] = alpha*durationMSec + (1-alpha)*prevDurationMSec

        print '%s -> %s (%.2fm)' % (DEP_STATION, ARR_STATION, (durationMSec/1000.0)/60)

    def _setupRoute(self, route):
        if route == 'MTN - PP - LOOP':
            self.nextStop['MTN'] = 'PPL'
            self.nextStop['PPL'] = 'MTN'

        elif route == 'MTN -  RES - PP LOOP' or route == 'MNT- RES -PP- LOOP':
            self.nextStop['MTN'] = 'RES'
            self.nextStop['RES'] = 'PPL'
            self.nextStop['PPL'] = 'MTN'

        elif route == ' MTN -  PP - RES - LOOP':
            self.nextStop['MTN'] = 'PPL'
            self.nextStop['PPL'] = 'RES'
            self.nextStop['RES'] = 'MTN'

    def _computeNextTime(self, DEP_STATION, currTime):
        key = DEP_STATION + '-' + self.nextStop[DEP_STATION]
        nextTime = currTime + self.tripTime[key]
        return [self.nextStop[DEP_STATION], nextTime]

    def analyzeTrack(self):

        PPL_STATUS = 0
        MTN_STATUS = 0
        RES_STATUS = 0

        DEP_TIMESTAMP = 0
        ARR_TIMESTAMP = 0

        DEP_STATION = ''
        ARR_STATION = ''

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
                LEAVING = PPL_STATUS > 0 or MTN_STATUS > 0 or RES_STATUS > 0

                if LEAVING:
                    if PPL_STATUS:
                        DEP_STATION = 'PPL'
                        PPL_STATUS = 0
                    elif MTN_STATUS:
                        DEP_STATION = 'MTN'
                        MTN_STATUS = 0
                    elif RES_STATUS:
                        DEP_STATION = 'RES'
                        RES_STATUS = 0

                    DEP_TIMESTAMP = self.time[i]
                    
                    print 'Leaving  %s (%s)' % (DEP_STATION, self.getTimestamp(i))

                    [nextStation, nextTime] = self._computeNextTime(DEP_STATION, self.time[i])
                    print '%s | %s' % (nextStation, self.formatTimeStamp(nextTime))

                    [nextStation, nextTime] = self._computeNextTime(nextStation, nextTime)
                    print '%s | %s' % (nextStation, self.formatTimeStamp(nextTime))

                    if len(self.nextStop) == 3:
                        [nextStation, nextTime] = self._computeNextTime(nextStation, nextTime)
                        print '%s | %s' % (nextStation, self.formatTimeStamp(nextTime))


            ARRIVING = PPL_STATUS == 1 or MTN_STATUS == 1 or RES_STATUS == 1

            if ARRIVING:

                if PPL_STATUS:
                    ARR_STATION = 'PPL'
                elif MTN_STATUS:
                    ARR_STATION = 'MTN'
                elif RES_STATUS:
                    ARR_STATION = 'RES'

                ARR_TIMESTAMP = self.time[i]

                print 'Arriving %s (%s)' % (ARR_STATION, self.getTimestamp(i))

                if DEP_STATION == '':
                    ARR_STATION = ''
                    ARR_TIMESTAMP = 0
                else:
                    self.logTrip(DEP_STATION, DEP_TIMESTAMP, ARR_STATION,
                        ARR_TIMESTAMP)



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


